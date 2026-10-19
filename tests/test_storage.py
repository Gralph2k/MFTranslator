import sqlite3
import uuid
from pathlib import Path

import pytest

from bot import storage as storage_module
from bot.storage import Storage

# %TEMP% в этой среде закрыт песочницей, поэтому база живёт в .tmp внутри проекта.
TMP_ROOT = Path(__file__).resolve().parent.parent / ".tmp"


@pytest.fixture
def storage():
    folder = TMP_ROOT / f"storage-{uuid.uuid4().hex[:8]}"
    folder.mkdir(parents=True, exist_ok=True)
    store = Storage(folder / "test.db")
    yield store
    store.close()


def test_user_is_created_once(storage):
    first = storage.ensure_user(42)
    second = storage.ensure_user(42)
    assert first == second


def test_session_roundtrip(storage):
    user = storage.ensure_user(42)
    history = [{"role": "assistant", "content": "Всё нормально."}]
    session_id = storage.create_session(user, "friday_evening", {"trust": 0.5}, history)

    loaded = storage.get_active_session(user)
    assert loaded is not None
    assert loaded.id == session_id
    assert loaded.state == {"trust": 0.5}
    assert loaded.history == history
    assert loaded.finished is False


def test_finished_session_is_not_active(storage):
    user = storage.ensure_user(42)
    session_id = storage.create_session(user, "friday_evening", {}, [])
    storage.save_session(session_id, {}, [], user_turns=3, finished=True)

    assert storage.get_active_session(user) is None
    assert storage.get_session(session_id).user_turns == 3


def test_debrief_is_saved_and_returned(storage):
    user = storage.ensure_user(7)
    session_id = storage.create_session(user, "friday_evening", {}, [])
    storage.save_debrief(session_id, "Итог: 8 из 12")

    assert storage.last_debrief(user) == "Итог: 8 из 12"


def test_delete_user_removes_everything(storage):
    user = storage.ensure_user(7)
    session_id = storage.create_session(user, "friday_evening", {}, [])
    storage.save_debrief(session_id, "разбор")
    storage.delete_user(7)

    assert storage.get_session(session_id) is None
    assert storage.last_debrief(user) is None
    assert storage.ensure_user(7) != user


def test_session_remembers_start_and_last_activity(storage, monkeypatch):
    times = iter(
        [
            "2026-10-18T10:00:00+00:00",  # пользователь
            "2026-10-18T10:00:00+00:00",  # начало сессии
            "2026-10-18T10:07:00+00:00",  # последний ход
        ]
    )
    monkeypatch.setattr(storage_module, "_now", lambda: next(times))

    user = storage.ensure_user(42)
    session_id = storage.create_session(user, "friday_evening", {}, [])
    storage.save_session(session_id, {}, [], user_turns=4, finished=False)

    loaded = storage.get_session(session_id)
    assert loaded.created_at == "2026-10-18T10:00:00+00:00"
    assert loaded.updated_at == "2026-10-18T10:07:00+00:00"


def test_overview_joins_user_and_latest_debrief(storage):
    user = storage.ensure_user(42)
    session_id = storage.create_session(user, "friday_evening", {}, [])
    storage.save_session(session_id, {}, [], user_turns=3, finished=True)
    storage.save_debrief(session_id, "Итог: 8 из 12")
    storage.save_debrief(session_id, "Итог: 10 из 12")

    rows = storage.list_overview()

    assert len(rows) == 1
    row = rows[0]
    assert row.id == session_id
    assert row.user_id == user
    assert row.telegram_id == 42
    assert row.scenario == "friday_evening"
    assert row.user_turns == 3
    assert row.finished is True
    assert row.debrief == "Итог: 10 из 12"


def test_overview_can_be_limited_to_latest(storage):
    user = storage.ensure_user(1)
    for _ in range(3):
        storage.create_session(user, "friday_evening", {}, [])

    rows = storage.list_overview(limit=2)

    assert len(rows) == 2
    assert rows[0].id > rows[1].id
    assert storage.count_sessions() == 3


OLD_SCHEMA = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scenario_id TEXT NOT NULL,
    state_json TEXT NOT NULL,
    history_json TEXT NOT NULL,
    user_turns INTEGER NOT NULL DEFAULT 0,
    finished INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE debriefs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def test_old_database_gets_updated_at_from_debrief_or_start():
    folder = TMP_ROOT / f"old-{uuid.uuid4().hex[:8]}"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "old.db"

    conn = sqlite3.connect(path)
    conn.executescript(OLD_SCHEMA)
    conn.execute(
        "INSERT INTO users (telegram_id, created_at) VALUES (42, '2026-10-18T10:00:00+00:00')"
    )
    conn.execute(
        """INSERT INTO sessions
           (user_id, scenario_id, state_json, history_json, user_turns, finished, created_at)
           VALUES (1, 'friday_evening', '{}', '[]', 1, 1, '2026-10-18T10:00:00+00:00')"""
    )
    conn.execute(
        """INSERT INTO debriefs (session_id, payload, created_at)
           VALUES (1, 'Итог: 8 из 12', '2026-10-18T10:09:00+00:00')"""
    )
    conn.commit()
    conn.close()

    store = Storage(path)
    try:
        loaded = store.get_session(1)
        assert loaded.created_at == "2026-10-18T10:00:00+00:00"
        # Без отдельной колонки длительность не восстановить: берём время разбора.
        assert loaded.updated_at == "2026-10-18T10:09:00+00:00"
    finally:
        store.close()
