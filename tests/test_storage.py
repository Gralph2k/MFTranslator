import uuid
from pathlib import Path

import pytest

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
