import uuid
from pathlib import Path

import pytest

from bot.engine import DialogueEngine
from bot.llm import FakeLLM
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
    return Trainer(DialogueEngine(FakeLLM([])), storage, load_scenario())


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
