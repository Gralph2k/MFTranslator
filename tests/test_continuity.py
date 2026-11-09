"""Сценарии-продолжения: персонаж помнит последнюю попытку переписки.

Правило: берём последнюю доигранную попытку предшественника; если её нет,
она оборвалась или персонаж ушёл по красной линии — идём по канону.
"""

import uuid
from pathlib import Path

import pytest

from bot.engine import DialogueEngine
from bot.llm import FakeLLM
from bot.scenario import load_scenario
from bot.storage import Storage
from bot.telegram_bot import Trainer

TMP_ROOT = Path(__file__).resolve().parent.parent / ".tmp"

CHAT = [
    {"role": "assistant", "content": "Сальса. Судя по всему, ты придумал шутку."},
    {"role": "user", "content": "Давай созвонимся в четверг."},
    {"role": "assistant", "content": "Ладно, в четверг. Только не в девять."},
]


@pytest.fixture
def store():
    folder = TMP_ROOT / f"continuity-{uuid.uuid4().hex[:8]}"
    folder.mkdir(parents=True, exist_ok=True)
    storage = Storage(folder / "test.db")
    yield storage
    storage.close()


def _trainer(store) -> Trainer:
    return Trainer(DialogueEngine(FakeLLM([])), store, load_scenario(), with_faces=False)


def _saved_chat(store, user, *, ended_by_persona=False, debrief=True, user_turns=2):
    session_id = store.create_session(user, "first_message", {}, CHAT)
    store.save_session(
        session_id,
        {},
        CHAT,
        user_turns=user_turns,
        finished=True,
        ended_by_persona=ended_by_persona,
    )
    if debrief:
        store.save_debrief(session_id, "Разбор: «Первое сообщение»\nИтог: 8 из 12")
    return session_id


def test_storage_keeps_the_last_attempt(store):
    user = store.ensure_user(42)
    first = store.create_session(user, "first_message", {}, [])
    store.save_session(first, {}, [], user_turns=0, finished=True)
    second = store.create_session(user, "first_message", {}, CHAT)
    store.save_session(second, {}, CHAT, user_turns=2, finished=True)

    loaded = store.last_session_for(user, "first_message")
    assert loaded is not None
    assert loaded.id == second
    assert store.last_session_for(user, "first_call") is None


def test_ended_by_persona_survives_storage(store):
    user = store.ensure_user(7)
    session_id = store.create_session(user, "first_message", {}, CHAT)
    store.save_session(
        session_id, {}, CHAT, user_turns=2, finished=True, ended_by_persona=True
    )

    assert store.get_session(session_id).ended_by_persona is True


def test_canon_is_used_without_previous_chat(store):
    session = _trainer(store).start_session(telegram_id=1, scenario_id="first_call")

    assert session.scenario.id == "first_call"
    assert session.previous == list(session.scenario.canon_history)


def test_real_chat_replaces_canon_when_completed(store):
    user = store.ensure_user(2)
    _saved_chat(store, user)

    session = _trainer(store).start_session(telegram_id=2, scenario_id="first_call")

    assert session.previous == CHAT


def test_real_chat_is_ignored_after_red_line(store):
    user = store.ensure_user(3)
    _saved_chat(store, user, ended_by_persona=True)

    session = _trainer(store).start_session(telegram_id=3, scenario_id="first_call")

    assert session.previous == list(session.scenario.canon_history)


def test_unfinished_chat_falls_back_to_canon(store):
    user = store.ensure_user(4)
    _saved_chat(store, user, debrief=False)

    session = _trainer(store).start_session(telegram_id=4, scenario_id="first_call")

    assert session.previous == list(session.scenario.canon_history)


def test_previous_chat_is_kept_on_restart(store):
    user = store.ensure_user(5)
    _saved_chat(store, user)

    first = _trainer(store)
    started = first.start_session(telegram_id=5, scenario_id="first_call")
    first.persist(telegram_id=5, session=started)

    restored = _trainer(store).get_session(5)
    assert restored is not None
    assert restored.scenario.id == "first_call"
    assert restored.previous == CHAT


def test_trainer_remembers_only_last_twelve_messages(store):
    user = store.ensure_user(6)
    long_chat = [
        {"role": "user" if index % 2 else "assistant", "content": f"реплика {index}"}
        for index in range(20)
    ]
    session_id = store.create_session(user, "first_message", {}, long_chat)
    store.save_session(session_id, {}, long_chat, user_turns=10, finished=True)
    store.save_debrief(session_id, "Итог: 8 из 12")

    session = _trainer(store).start_session(telegram_id=6, scenario_id="first_call")

    assert len(session.previous) == 12
    assert session.previous[-1]["content"] == "реплика 19"
