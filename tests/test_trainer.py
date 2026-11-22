import json
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from bot import telegram_bot
from bot.engine import DialogueEngine
from bot.llm import FakeLLM
from bot.heroines import heroines
from bot.scenario import load_scenario
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

    # Новый экземпляр - как после перезапуска бота: памяти нет, база есть.
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
    session = trainer.start_session(telegram_id=5, scenario_id="reunion_call/ira")

    assert session.scenario.id == "reunion_call/ira"
    assert session.history[0]["content"] == session.scenario.opening

    # После перезапуска сценарий поднимается из базы, а не из памяти.
    restored = _trainer(store).get_session(5)
    assert restored is not None
    assert restored.scenario.id == "reunion_call/ira"


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
        self.bot = None  # _deliver_debrief передаёт target.bot в отчёт владельцу
        self.sent: list[str] = []

    async def answer(self, text: str, **kwargs) -> None:
        self.sent.append(text)


async def test_start_shows_landing_without_scenario(store, monkeypatch):
    """/start - лендинг бота: интро и меню, сценарий не запускается сам."""
    trainer = Trainer(DialogueEngine(FakeLLM([])), store, load_scenario(), with_faces=False)
    monkeypatch.setattr(telegram_bot, "_trainer_instance", trainer)

    message = FakeMessage("/start")
    await telegram_bot.cmd_start(message)

    assert trainer.get_session(1) is None
    assert any("тренажёр" in text.lower() for text in message.sent)
    assert any("Проверка анкеты" in text for text in message.sent)


async def test_restart_anti_repeats_the_last_heroine(store, monkeypatch):
    """Если прошлый разговор был с Верой, случайный выбор её исключает."""
    trainer = Trainer(DialogueEngine(FakeLLM([])), store, load_scenario(), with_faces=False)
    trainer.start_session(telegram_id=1, scenario_id="first_message/vera")
    # Закрываем разговор и «перезапускаем процесс»: ни активной сцены в базе,
    # ни копии в памяти - иначе /restart просто повторил бы ту же сцену.
    stored = store.get_active_session(store.ensure_user(1))
    store.save_session(stored.id, stored.state, stored.history, stored.user_turns, finished=True)
    trainer.sessions.pop(1, None)

    seen: dict[str, str | None] = {}

    def pick(last=None):
        seen["last"] = last
        return heroines()[1]

    monkeypatch.setattr(telegram_bot, "_trainer_instance", trainer)
    monkeypatch.setattr(telegram_bot, "random_heroine", pick)

    await telegram_bot.cmd_restart(FakeMessage("/restart"))

    assert seen["last"] == "vera"
    session = trainer.get_session(1)
    assert session is not None
    assert session.scenario.id == "first_message/eva"


async def test_restart_does_not_relaunch_a_disabled_scenario(store, monkeypatch):
    """Активную выключенную сцену /restart меняет на случайную героиню."""
    trainer = Trainer(DialogueEngine(FakeLLM([])), store, load_scenario(), with_faces=False)
    trainer.start_session(telegram_id=1, scenario_id="friday_evening/anya")

    monkeypatch.setattr(telegram_bot, "_trainer_instance", trainer)
    monkeypatch.setattr(
        telegram_bot, "random_heroine", lambda last=None: heroines()[1]
    )

    await telegram_bot.cmd_restart(FakeMessage("/restart"))

    session = trainer.get_session(1)
    assert session is not None
    assert session.scenario.id == "first_message/eva"


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


async def test_finished_scenario_is_reported_to_owner(store, monkeypatch):
    """Каждый завершённый сценарий уходит владельцу: переписка + разбор."""
    llm = FakeLLM(["Ладно.", json.dumps({"trust": 0.5}), DEBRIEF])
    trainer = Trainer(DialogueEngine(llm), store, load_scenario(), with_faces=False)
    monkeypatch.setattr(telegram_bot, "_trainer_instance", trainer)
    reports: list[str] = []
    monkeypatch.setattr(
        telegram_bot, "_notify_owner", lambda bot, tr, text: reports.append(text)
    )

    session = trainer.start_session(telegram_id=77)
    session.user_turns = session.scenario.turn_limit - 1
    await telegram_bot.on_text(FakeMessage("Я рядом.", user_id=77))

    assert len(reports) == 1
    assert f"tg 77" in reports[0]
    assert "Переписка:" in reports[0] and "Он: Я рядом." in reports[0]
    assert "Разбор:" in reports[0] and "Итог:" in reports[0]


async def test_owner_report_is_not_sent_without_debrief(store, monkeypatch):
    """Без разбора отчёта нет: провал debrief не дублирует владельцу пустоту."""
    llm = FakeLLM(["Ладно.", json.dumps({"trust": 0.5})])
    trainer = Trainer(DialogueEngine(llm), store, load_scenario(), with_faces=False)
    monkeypatch.setattr(telegram_bot, "_trainer_instance", trainer)
    reports: list[str] = []
    monkeypatch.setattr(
        telegram_bot, "_notify_owner", lambda bot, tr, text: reports.append(text)
    )

    session = trainer.start_session(telegram_id=1)
    session.user_turns = session.scenario.turn_limit - 1
    await telegram_bot.on_text(FakeMessage("Я рядом."))

    assert reports == []


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


async def test_debrief_is_not_delivered_twice(store, monkeypatch):
    """Прямой повторный вызов разбора - no-op: ни запроса, ни дубля текста."""
    llm = FakeLLM([DEBRIEF])
    trainer = Trainer(DialogueEngine(llm), store, load_scenario(), with_faces=False)
    monkeypatch.setattr(telegram_bot, "_trainer_instance", trainer)

    session = trainer.start_session(telegram_id=1)
    session.user_turns = 3
    await telegram_bot.cmd_finish(FakeMessage("/finish"))
    second = FakeMessage("x")
    await telegram_bot._deliver_debrief(second, trainer, 1, session)

    assert len(llm.calls) == 1
    assert second.sent == []


async def test_crisis_message_closes_session_in_database(store, monkeypatch):
    """После кризисного сообщения сессия закрыта и в памяти, и в базе.

    Иначе следующий текст продолжил бы сцену сразу после сообщения о помощи.
    """
    trainer = Trainer(DialogueEngine(FakeLLM([])), store, load_scenario(), with_faces=False)
    monkeypatch.setattr(telegram_bot, "_trainer_instance", trainer)
    session = trainer.start_session(telegram_id=1)

    message = FakeMessage("Я больше не хочу жить")
    await telegram_bot.on_text(message)

    assert session.finished is True
    assert store.get_active_session(store.ensure_user(1)) is None
    assert any("112" in text for text in message.sent)


async def test_rapid_messages_of_one_user_are_serialized(store, monkeypatch):
    """Два быстрых сообщения обрабатываются по порядку, а не вперемешку.

    aiogram запускает апдейты конкурентно (handle_as_tasks=True): без замка
    на пользователя второй ход вклинивается до ответа на первый.
    """
    import asyncio

    class SlowLLM:
        """Первый ответ задерживается: без замка второй закончится раньше."""

        def __init__(self) -> None:
            self.calls = 0

        async def complete(self, messages, *, json_mode=False, temperature=0.8):
            self.calls += 1
            if self.calls == 1:
                await asyncio.sleep(0.05)
            if json_mode:
                return json.dumps({"mood": "спокойно"})
            return "Ладно."

        async def aclose(self) -> None:
            return None

    llm = SlowLLM()
    trainer = Trainer(DialogueEngine(llm), store, load_scenario(), with_faces=False)
    monkeypatch.setattr(telegram_bot, "_trainer_instance", trainer)
    session = trainer.start_session(telegram_id=1)

    await asyncio.gather(
        telegram_bot.on_text(FakeMessage("Первое")),
        telegram_bot.on_text(FakeMessage("Второе")),
    )

    roles = [m["role"] for m in session.history]
    # Строгое чередование после opening: ответы не перемешались.
    assert roles == ["assistant", "user", "assistant", "user", "assistant"]
    assert session.user_turns == 2


async def test_crisis_bio_stops_profile_flow(store, monkeypatch):
    """Кризисная фраза в тексте анкеты останавливает флоу, а не идёт в разбор."""
    trainer = Trainer(DialogueEngine(FakeLLM([])), store, load_scenario(), with_faces=False)
    monkeypatch.setattr(telegram_bot, "_trainer_instance", trainer)
    flow = trainer.start_profile_flow(1)
    trainer.save_flow(flow, name="Саша", age=32, phase="bio")

    message = FakeMessage("Живу один, всё надоело, хочу умереть")
    await telegram_bot.on_profile_text(message)

    assert trainer.get_profile_flow(1) is None
    assert any("112" in text for text in message.sent)


class FakeMediaMessage:
    """Медиа-сообщение: фото/голосовое есть, текста нет."""

    def __init__(self, user_id: int = 1) -> None:
        self.from_user = SimpleNamespace(id=user_id)
        self.bot = None
        self.sent: list[str] = []
        self.photo = [SimpleNamespace(file_id="f1")]
        self.media_group_id = None
        self.voice = SimpleNamespace(duration=1)
        self.sticker = None

    async def answer(self, text: str, **kwargs) -> None:
        self.sent.append(text)


async def test_media_in_dialogue_gets_text_answer(store, monkeypatch):
    """Фото/голосовое при живой сцене не молчат: сцена живёт текстом."""
    trainer = Trainer(DialogueEngine(FakeLLM([])), store, load_scenario(), with_faces=False)
    monkeypatch.setattr(telegram_bot, "_trainer_instance", trainer)
    trainer.start_session(telegram_id=1, scenario_id="first_message/vera")

    photo = FakeMediaMessage()
    await telegram_bot.on_photo(photo)
    assert any("переписка живёт текстом" in text for text in photo.sent)

    voice = FakeMediaMessage()
    await telegram_bot.on_other_media(voice)
    assert any("переписка живёт текстом" in text for text in voice.sent)


async def test_media_without_session_stays_silent(store, monkeypatch):
    """Без сцены и без флоу анкеты медиа по-прежнему игнорируется."""
    trainer = Trainer(DialogueEngine(FakeLLM([])), store, load_scenario(), with_faces=False)
    monkeypatch.setattr(telegram_bot, "_trainer_instance", trainer)

    message = FakeMediaMessage()
    await telegram_bot.on_other_media(message)
    assert message.sent == []
