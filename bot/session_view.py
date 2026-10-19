"""Просмотр диалогов: список сессий и стенограмма одной сессии.

Запускается через `sessions.cmd` (или `python -m bot.session_view`).
Данные только читаются: ничего не меняем и не отправляем в сеть.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from .config import load_settings
from .scenario import Scenario, ScenarioError, load_scenario
from .storage import SessionOverview, StoredSession, Storage

MSK = timezone(timedelta(hours=3))
SCORE_RE = re.compile(r"Итог:\s*(\d+)\s*из\s*(\d+)")
RULE = "-" * 40
LAST_SESSIONS = 20


def _as_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return None
    return moment.replace(tzinfo=timezone.utc) if moment.tzinfo is None else moment


def format_start(value: str, full: bool = False) -> str:
    moment = _as_datetime(value)
    if moment is None:
        return "—"
    pattern = "%d.%m.%Y %H:%M" if full else "%d.%m.%y %H:%M"
    return moment.astimezone(MSK).strftime(pattern)


def duration_minutes(created_at: str, updated_at: str | None) -> int | None:
    start, end = _as_datetime(created_at), _as_datetime(updated_at)
    if start is None or end is None:
        return None
    return max(0, int((end - start).total_seconds() // 60))


def format_minutes(minutes: int | None) -> str:
    if minutes is None:
        return "—"
    if minutes < 1:
        return "<1 мин"
    hours, rest = divmod(minutes, 60)
    if hours:
        return f"{hours} ч {rest:02d} мин"
    return f"{minutes} мин"


def parse_score(payload: str | None) -> tuple[int, int] | None:
    """Оценка лежит в готовом тексте разбора: «Итог: 8 из 12»."""
    if not payload:
        return None
    match = SCORE_RE.search(payload)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


def format_score(payload: str | None) -> str:
    score = parse_score(payload)
    return f"{score[0]}/{score[1]}" if score is not None else "—"


def _status(row: SessionOverview) -> str:
    return "активна" if not row.finished else "завершена"


def format_table(rows: list[SessionOverview], total: int | None = None) -> str:
    if not rows:
        return "Сессий пока нет: бот ещё не сохранил ни одного диалога."

    headers = ["ID", "user", "telegram", "сценарий", "начало", "длит.", "оценка", "статус"]
    body = [
        [
            str(row.id),
            str(row.user_id),
            str(row.telegram_id),
            row.scenario,
            format_start(row.created_at),
            format_minutes(duration_minutes(row.created_at, row.updated_at)),
            format_score(row.debrief),
            _status(row),
        ]
        for row in rows
    ]
    widths = [
        max(len(headers[index]), *(len(line[index]) for line in body))
        for index in range(len(headers))
    ]

    def render(values: list[str]) -> str:
        return "  ".join(value.ljust(widths[i]) for i, value in enumerate(values)).rstrip()

    lines = [render(headers), render(["-" * width for width in widths])]
    lines.extend(render(line) for line in body)
    if total is not None and total > len(rows):
        summary = f"Показаны последние {len(rows)} из {total}."
    else:
        summary = f"Всего сессий: {len(rows)}."
    lines.extend(["", f"{summary} Номер сессии — ниже, Enter — выход."])
    return "\n".join(lines)


def format_session(
    overview: SessionOverview,
    stored: StoredSession,
    scenario: Scenario | None,
) -> str:
    title = f" «{scenario.title}»" if scenario is not None else ""
    lines = [
        f"Сессия {overview.id} · {overview.scenario}{title}",
        f"Пользователь: user_id {overview.user_id}, telegram {overview.telegram_id}",
        f"Начало: {format_start(overview.created_at, full=True)} (МСК)",
        f"Длительность: {format_minutes(duration_minutes(overview.created_at, overview.updated_at))}",
    ]

    turns = f"Ходов: {overview.user_turns}"
    if scenario is not None:
        turns += f" из {scenario.turn_limit}"
    lines.append(turns)
    lines.append(f"Статус: {_status(overview)}")

    score = parse_score(overview.debrief)
    if score is not None:
        lines.append(f"Оценка: {score[0]} из {score[1]}")

    persona = scenario.persona.name if scenario is not None else "Персонаж"
    lines.extend(["", "Стенограмма", RULE])
    if not stored.history:
        lines.append("Диалог пуст: пользователь не написал ни одной реплики.")
    else:
        for message in stored.history:
            author = "Пользователь" if message.get("role") == "user" else persona
            lines.append(f"{author}: {message.get('content', '')}")

    lines.extend(["", "Разбор", RULE])
    if overview.debrief:
        lines.append(overview.debrief)
    else:
        lines.append("Разбора нет: диалог не завершён или оценка не сохранилась.")

    return "\n".join(lines)


def _scenario_or_none(scenario_id: str) -> Scenario | None:
    try:
        return load_scenario(scenario_id)
    except ScenarioError:
        return None


def run_interactive(
    storage: Storage,
    read: Callable[[str], str] = input,
    write: Callable[[str], None] = print,
) -> None:
    """Последние 20 сессий, затем ожидание номера. Пустая строка — выход."""

    def show_list() -> None:
        rows = storage.list_overview(limit=LAST_SESSIONS)
        write(format_table(rows, total=storage.count_sessions()))

    show_list()

    while True:
        write("")
        try:
            answer = read("Номер сессии (Enter — выход): ").strip()
        except (EOFError, KeyboardInterrupt):
            write("")
            return
        if not answer or answer.lower() in {"q", "quit", "exit", "выход"}:
            write("")
            return
        if not answer.isdigit():
            write("Нужен номер сессии — число из таблицы.")
            continue

        session_id = int(answer)
        overview = storage.get_overview(session_id)
        stored = storage.get_session(session_id)
        if overview is None or stored is None:
            write(f"Сессия {session_id} не найдена.")
            continue

        write("")
        write(format_session(overview, stored, _scenario_or_none(overview.scenario)))
        # Список снова перед глазами: номер следующей сессии не надо вспоминать.
        write("")
        show_list()


def _utf8_console() -> None:
    # Консоль Windows по умолчанию не в UTF-8 — иначе русский текст превращается в кашу.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass


def main(argv: list[str] | None = None) -> int:
    _utf8_console()
    parser = argparse.ArgumentParser(
        prog="sessions.cmd",
        description="Последние 20 диалогов; номер сессии — стенограмма и разбор.",
    )
    parser.add_argument(
        "session_id",
        nargs="?",
        type=int,
        help="номер сессии; без него — последние 20 и ожидание номера",
    )
    args = parser.parse_args(argv)

    settings = load_settings()
    if not settings.db_path.exists():
        print(f"База не найдена: {settings.db_path}")
        return 1

    storage = Storage(settings.db_path)
    try:
        if args.session_id is None:
            run_interactive(storage)
            return 0

        overview = storage.get_overview(args.session_id)
        stored = storage.get_session(args.session_id)
        if overview is None or stored is None:
            print(f"Сессия {args.session_id} не найдена.")
            return 1
        print(format_session(overview, stored, _scenario_or_none(overview.scenario)))
        return 0
    finally:
        storage.close()


if __name__ == "__main__":
    raise SystemExit(main())
