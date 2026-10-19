import uuid
from pathlib import Path

import pytest

from bot.scenario import load_scenario
from bot.session_view import (
    duration_minutes,
    format_minutes,
    format_score,
    format_session,
    format_table,
    run_interactive,
)
from bot.storage import SessionOverview, Storage, StoredSession

TMP_ROOT = Path(__file__).resolve().parent.parent / ".tmp"


@pytest.fixture
def store():
    folder = TMP_ROOT / f"view-{uuid.uuid4().hex[:8]}"
    folder.mkdir(parents=True, exist_ok=True)
    storage = Storage(folder / "test.db")
    yield storage
    storage.close()


def _overview(**overrides) -> SessionOverview:
    values = {
        "id": 1,
        "user_id": 1,
        "telegram_id": 123456789,
        "scenario": "friday_evening",
        "created_at": "2026-10-18T15:07:00+00:00",
        "updated_at": "2026-10-18T15:19:00+00:00",
        "user_turns": 10,
        "finished": True,
        "debrief": "Разбор: «Пятничный вечер»\nИтог: 8 из 12",
    }
    values.update(overrides)
    return SessionOverview(**values)


def _stored() -> StoredSession:
    return StoredSession(
        id=1,
        user_id=1,
        scenario="friday_evening",
        state={},
        history=[
            {"role": "assistant", "content": "Привет. Я дома."},
            {"role": "user", "content": "Как ты?"},
        ],
        user_turns=1,
        finished=True,
        created_at="2026-10-18T15:07:00+00:00",
        updated_at="2026-10-18T15:19:00+00:00",
    )


def test_minutes_are_human_readable():
    assert format_minutes(0) == "<1 мин"
    assert format_minutes(12) == "12 мин"
    assert format_minutes(60) == "1 ч 00 мин"
    assert format_minutes(135) == "2 ч 15 мин"
    assert format_minutes(None) == "—"


def test_duration_runs_from_start_to_last_activity():
    assert (
        duration_minutes("2026-10-18T15:07:00+00:00", "2026-10-18T15:19:30+00:00") == 12
    )
    assert duration_minutes("2026-10-18T15:07:00+00:00", None) is None


def test_score_is_read_from_the_debrief_header():
    assert format_score("Разбор\nИтог: 8 из 12\n") == "8/12"
    assert format_score(None) == "—"
    assert format_score("тут нет итога") == "—"


def test_table_shows_requested_columns():
    text = format_table([_overview()])

    assert "123456789" in text
    assert "friday_evening" in text
    assert "18.10.26 18:07" in text
    assert "12 мин" in text
    assert "8/12" in text
    assert "номер сессии" in text.lower()


def test_empty_list_is_explained():
    assert "пока нет" in format_table([]).lower()


def test_active_session_has_no_score_yet():
    text = format_table([_overview(finished=False, debrief=None)])

    assert "активна" in text
    assert "—" in text


def test_session_details_include_transcript_and_debrief():
    text = format_session(_overview(), _stored(), load_scenario("friday_evening"))

    assert "Аня: Привет. Я дома." in text
    assert "Пользователь: Как ты?" in text
    assert "Оценка: 8 из 12" in text
    assert "Итог: 8 из 12" in text


def test_session_details_survive_a_missing_scenario_file():
    text = format_session(_overview(), _stored(), None)

    assert "Привет. Я дома." in text
    assert "Оценка: 8 из 12" in text


def test_table_says_how_many_sessions_are_shown():
    text = format_table([_overview()], total=57)

    assert "1 из 57" in text


def test_interactive_lists_then_waits_for_a_session_number(store):
    user = store.ensure_user(42)
    session_id = store.create_session(
        user, "friday_evening", {}, [{"role": "user", "content": "Привет"}]
    )
    store.save_debrief(session_id, "Итог: 8 из 12")

    prompts: list[str] = []
    answers = iter([str(session_id), ""])

    def read(prompt: str) -> str:
        prompts.append(prompt)
        return next(answers)

    output: list[str] = []
    run_interactive(store, read=read, write=output.append)

    text = "\n".join(output)
    assert "Номер сессии" in prompts[0]
    assert "friday_evening" in text
    assert "Итог: 8 из 12" in text
    # После карточки список показывается заново, и снова ждём ввод.
    assert text.count("Всего сессий:") == 2
    assert len(prompts) == 2


def test_interactive_reports_unknown_session(store):
    store.ensure_user(1)
    answers = iter(["999", ""])

    output: list[str] = []
    run_interactive(store, read=lambda prompt: next(answers), write=output.append)

    assert "не найдена" in "\n".join(output)


def test_interactive_shows_only_the_last_twenty(store):
    user = store.ensure_user(1)
    for _ in range(25):
        store.create_session(user, "friday_evening", {}, [])

    def read(prompt: str) -> str:
        raise EOFError

    output: list[str] = []
    run_interactive(store, read=read, write=output.append)

    assert "Показаны последние 20 из 25" in "\n".join(output)


def test_interactive_exits_on_eof(store):
    def read(prompt: str) -> str:
        raise EOFError

    output: list[str] = []
    run_interactive(store, read=read, write=output.append)

    assert "пока нет" in "\n".join(output).lower()
