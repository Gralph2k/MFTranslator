import json
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from bot import telegram_bot
from bot.engine import DialogueEngine
from bot.llm import FakeLLM
from bot.scenario import available_scenarios, load_scenario
from bot.storage import Storage
from bot.telegram_bot import Trainer

TMP_ROOT = Path(__file__).resolve().parent.parent / ".tmp"


@pytest.fixture
def store():
    folder = TMP_ROOT / f"trainer-{uuid.uuid4().hex[:8]}"
    folder.mkdir(parents=True, exist_ok=True)
    storage = Storage(folder / "test.db")
    yield storage
    storage.close()


def _trainer(storage) -> Trainer:
    return Trainer(DialogueEngine(FakeLLM([])), storage, load_scenario(), with_faces=False)


def test_session_id_is_stored_on_the_session(store):
    trainer = _trainer(store)
    session = trainer.start_session(telegram_id=1)

    assert session.session_id is not None
    trainer.persist(telegram_id=1, session=session)


def test_session_survives_process_restart(store):
    first = _trainer(store)
    session = first.start_session(telegram_id=7)
    session.history.append({"role": "user", "content": "Привет"})
    first.persist(telegram_id=7, session=session)

    # Новый экземпляр — как после перезапуска бота: памяти нет, база есть.
    second = _trainer(store)
    loaded = second.get_session(7)

    assert loaded is not None
    assert loaded.session_id == session.session_id
    assert loaded.history[-1] == {"role": "user", "content": "Привет"}


def test_restart_closes_previous_session(store):
    trainer = _trainer(store)
    trainer.start_session(telegram_id=3)
    trainer.start_session(telegram_id=3)

    user_id = store.ensure_user(3)
    active = store.get_active_session(user_id)
    assert active is not None
    assert active.user_turns == 0

    sessions = store.list_sessions(user_id)
    assert [session.finished for session in sessions] == [True, False]


def test_scenario_can_be_chosen(store):
    trainer = _trainer(store)
    session = trainer.start_session(telegram_id=5, scenario_id="reunion_call")

    assert session.scenario.id == "reunion_call"
    assert session.history[0]["content"] == session.scenario.opening

    # После перезапуска сценарий поднимается из базы, а не из памяти.
    restored = _trainer(store).get_session(5)
    assert restored is not None
    assert restored.scenario.id == "reunion_call"


def test_unknown_scenario_is_rejected(store):
    trainer = _trainer(store)
    with pytest.raises(Exception):
        trainer.start_session(telegram_id=6, scenario_id="нет_такого")


DEBRIEF = json.dumps(
    {
        "scores": {
            "noticing": 2,
            "questions": 1,
            "validation": 1,
            "no_rescuing": 2,
            "self_expression": 1,
            "care_offer": 1,
        },
        "summary": "Ты заметил и не стал давить.",
        "strengths": ["Ты назвал её состояние вслух."],
        "growth": ["Меньше вопросов подряд."],
        "moments": [],
        "rewrite": {"original": "Успокойся", "better": "Я рядом."},
        "next_time": "Назвать чувство и замолчать.",
    },
    ensure_ascii=False,
)


class FakeMessage:
    """Минимальный Message: хендлеру нужны text, from_user.id и answer()."""

    def __init__(self, text: str, user_id: int = 1) -> None:
        self.text = text
        self.from_user = SimpleNamespace(id=user_id)
        self.sent: list[str] = []

    async def answer(self, text: str, **kwargs) -> None:
        self.sent.append(text)


async def test_start_picks_a_random_scenario(store, monkeypatch):
    """`/start` без выбора берёт случайный сценарий и предлагает поменять."""
    trainer = Trainer(DialogueEngine(FakeLLM([])), store, load_scenario(), with_faces=False)
    monkeypatch.setattr(telegram_bot, "_trainer_instance", trainer)
    monkeypatch.setattr(telegram_bot.random, "choice", lambda items: "first_date")

    message = FakeMessage("/start")
    await telegram_bot.cmd_start(message)

    session = trainer.get_session(1)
    assert session is not None
    assert session.scenario.id == "first_date"
    assert session.scenario.id in available_scenarios()
    assert any("случайно" in text for text in message.sent)


async def test_debrief_arrives_as_soon_as_turns_run_out(store, monkeypatch):
    llm = FakeLLM(["Ладно.", json.dumps({"trust": 0.5}), DEBRIEF])
    trainer = Trainer(DialogueEngine(llm), store, load_scenario(), with_faces=False)
    monkeypatch.setattr(telegram_bot, "_trainer_instance", trainer)

    session = trainer.start_session(telegram_id=1)
    session.user_turns = session.scenario.turn_limit - 1
    message = FakeMessage("Я рядом.")

    await telegram_bot.on_text(message)

    assert session.finished is True
    assert any("Разбор" in text for text in message.sent)
    assert store.last_debrief(store.ensure_user(1)) is not None


async def test_finish_does_not_repeat_an_automatic_debrief(store, monkeypatch):
    llm = FakeLLM(["Ладно.", json.dumps({"trust": 0.5}), DEBRIEF])
    trainer = Trainer(DialogueEngine(llm), store, load_scenario(), with_faces=False)
    monkeypatch.setattr(telegram_bot, "_trainer_instance", trainer)

    session = trainer.start_session(telegram_id=1)
    session.user_turns = session.scenario.turn_limit - 1
    await telegram_bot.on_text(FakeMessage("Я рядом."))

    message = FakeMessage("/finish")
    await telegram_bot.cmd_finish(message)

    assert any("уже" in text.lower() for text in message.sent)
    # Второй разбор не записан и лишний запрос к модели не ушёл.
    assert len(llm.calls) == 3
