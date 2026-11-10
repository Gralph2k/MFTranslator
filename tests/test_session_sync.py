import uuid
from pathlib import Path

import pytest

from bot.session_sync import build_view_db, merge_databases
from bot.storage import Storage

TMP_ROOT = Path(__file__).resolve().parent.parent / ".tmp"


@pytest.fixture
def folder():
    path = TMP_ROOT / f"sync-{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _seed(path: Path, telegram_id: int, scenario: str, debrief: str | None = None):
    store = Storage(path)
    try:
        user_id = store.ensure_user(telegram_id)
        session_id = store.create_session(
            user_id,
            scenario,
            {"trust": 0.5},
            [
                {"role": "assistant", "content": "Привет."},
                {"role": "user", "content": "Привет, как ты?"},
            ],
        )
        store.save_session(session_id, {"trust": 0.6}, [], user_turns=1, finished=True)
        if debrief is not None:
            store.save_debrief(session_id, debrief)
        return user_id, session_id
    finally:
        store.close()


def test_view_combines_local_and_live_sessions(folder):
    local = folder / "local.db"
    remote = folder / "remote.db"
    view = folder / "view.db"

    _seed(local, 111, "friday_evening", "Итог: 8 из 12")
    _seed(remote, 111, "first_call", "Итог: 5 из 12")

    build_view_db(local, remote, view)

    store = Storage(view)
    try:
        rows = {row.scenario: row for row in store.list_overview()}
        assert store.count_sessions() == 2
        assert set(rows) == {"friday_evening", "first_call"}
        assert "8 из 12" in (rows["friday_evening"].debrief or "")
        assert "5 из 12" in (rows["first_call"].debrief or "")
        # Новые сессии с VPS идут после локальных: список не перетасовывается.
        assert rows["first_call"].id > rows["friday_evening"].id
    finally:
        store.close()


def test_merge_is_idempotent(folder):
    local = folder / "local.db"
    remote = folder / "remote.db"
    view = folder / "view.db"

    _seed(local, 111, "friday_evening")
    _seed(remote, 111, "first_call")

    build_view_db(local, remote, view)
    merge_databases(view, remote)
    merge_databases(view, remote)

    store = Storage(view)
    try:
        assert store.count_sessions() == 2
    finally:
        store.close()


def test_remote_users_are_matched_by_telegram_id(folder):
    local = folder / "local.db"
    remote = folder / "remote.db"
    view = folder / "view.db"

    store = Storage(local)
    try:
        store.ensure_user(999)  # другой пользователь, чтобы id 111 не совпал
        local_user = store.ensure_user(111)
    finally:
        store.close()
    _seed(remote, 111, "first_call")

    build_view_db(local, remote, view)

    store = Storage(view)
    try:
        assert store.ensure_user(111) == local_user
        sessions = [row for row in store.list_overview() if row.scenario == "first_call"]
        assert len(sessions) == 1
        assert sessions[0].user_id == local_user
    finally:
        store.close()


def test_view_without_remote_is_a_copy_of_local(folder):
    local = folder / "local.db"
    view = folder / "view.db"
    _seed(local, 111, "friday_evening", "Итог: 8 из 12")

    build_view_db(local, None, view)

    store = Storage(view)
    try:
        assert store.count_sessions() == 1
        assert store.list_overview()[0].scenario == "friday_evening"
    finally:
        store.close()
