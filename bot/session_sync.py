"""Собирает одну базу для просмотра: локальная история плюс живая база с VPS.

Бот работает на сервере, поэтому свежие диалоги появляются в
`/opt/mf-translator/data/bot.db`, а `sessions.cmd` по умолчанию читает локальный
`data/bot.db`. Здесь мы снимаем консистентную копию серверной базы и добавляем её
сессии в локальную копию — только для чтения, боевая база не меняется.

Запускается из `sessions.cmd` перед показом списка.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from .config import load_settings

ROOT = Path(__file__).resolve().parent.parent
SSH_TARGET = os.getenv("SESSIONS_SSH", "root@48.102.186.191")
REMOTE_PROJECT = "/opt/mf-translator"
REMOTE_DB = "data/bot.db"
DEFAULT_TTL = 120


def _backup_database(source: Path, target: Path) -> None:
    """Копия через SQLite backup: файл можно копировать даже на живой базе."""
    target.parent.mkdir(parents=True, exist_ok=True)
    target.unlink(missing_ok=True)
    src = sqlite3.connect(source)
    dst = sqlite3.connect(target)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def merge_databases(base: Path, extra: Path) -> None:
    """Добавляет в base пользователей, сессии и разборы из extra.

    Пользователи сопоставляются по telegram_id, сессии — по пользователю,
    сценарию и времени начала, поэтому повторный merge ничего не дублирует.
    """
    conn = sqlite3.connect(base)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("ATTACH DATABASE ? AS extra", (str(extra),))

        conn.execute(
            """INSERT INTO main.users (telegram_id, created_at)
               SELECT e.telegram_id, e.created_at
               FROM extra.users e
               WHERE NOT EXISTS (
                   SELECT 1 FROM main.users m WHERE m.telegram_id = e.telegram_id
               )"""
        )
        conn.execute(
            """INSERT INTO main.sessions
                   (user_id, scenario_id, state_json, history_json, user_turns,
                    finished, ended_by_persona, created_at, updated_at)
               SELECT mu.id, es.scenario_id, es.state_json, es.history_json,
                      es.user_turns, es.finished, es.ended_by_persona,
                      es.created_at, es.updated_at
               FROM extra.sessions es
               JOIN extra.users eu ON eu.id = es.user_id
               JOIN main.users mu ON mu.telegram_id = eu.telegram_id
               WHERE NOT EXISTS (
                   SELECT 1 FROM main.sessions ms
                   WHERE ms.user_id = mu.id
                     AND ms.scenario_id = es.scenario_id
                     AND ms.created_at = es.created_at
               )
               ORDER BY es.id"""
        )
        conn.execute(
            """INSERT INTO main.debriefs (session_id, payload, created_at)
               SELECT ms.id, ed.payload, ed.created_at
               FROM extra.debriefs ed
               JOIN extra.sessions es ON es.id = ed.session_id
               JOIN extra.users eu ON eu.id = es.user_id
               JOIN main.users mu ON mu.telegram_id = eu.telegram_id
               JOIN main.sessions ms
                 ON ms.user_id = mu.id
                AND ms.scenario_id = es.scenario_id
                AND ms.created_at = es.created_at
               WHERE NOT EXISTS (
                   SELECT 1 FROM main.debriefs md
                   WHERE md.session_id = ms.id
                     AND md.payload = ed.payload
                     AND md.created_at = ed.created_at
               )
               ORDER BY ed.id"""
        )
        conn.commit()
    finally:
        conn.close()


def build_view_db(local: Path, remote: Path | None, view: Path) -> Path:
    """Копия локальной базы плюс сессии с сервера (если копия доступна)."""
    _backup_database(local, view)
    if remote is not None and remote.exists():
        merge_databases(view, remote)
    return view


def fetch_remote(dest: Path, *, ttl: int = DEFAULT_TTL, target: str = SSH_TARGET) -> bool:
    """Снимает копию боевой базы на сервере и забирает её по scp.

    При любой ошибке возвращает False и оставляет прежний кэш: просмотр
    должен работать и без сети.
    """
    if dest.exists() and time.time() - dest.stat().st_mtime < ttl:
        return True

    remote_tmp = f"/tmp/mf-bot-view-{os.getpid()}.db"
    backup_code = (
        "import sqlite3; "
        "s=sqlite3.connect('data/bot.db'); "
        f"d=sqlite3.connect('{remote_tmp}'); "
        "s.backup(d); d.close()"
    )
    ssh = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", target]

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    tmp.unlink(missing_ok=True)
    try:
        made = subprocess.run(
            ssh + [f"cd {REMOTE_PROJECT} && .venv/bin/python -c \"{backup_code}\""],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if made.returncode != 0:
            return False
        got = subprocess.run(
            ["scp", "-q", f"{target}:{remote_tmp}", str(tmp)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        returncode = got.returncode
    except (OSError, subprocess.SubprocessError):
        return False
    finally:
        try:
            subprocess.run(ssh + [f"rm -f {remote_tmp}"], capture_output=True, timeout=15)
        except (OSError, subprocess.SubprocessError):
            pass

    if returncode != 0:
        return False
    tmp.replace(dest)
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sessions-sync",
        description="Обновляет базу для sessions.cmd: локальные и серверные диалоги.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / ".tmp" / "sessions-view.db",
        help="куда собрать объединённую базу",
    )
    parser.add_argument("--no-remote", action="store_true", help="не ходить на VPS")
    parser.add_argument(
        "--ttl",
        type=int,
        default=int(os.getenv("SESSIONS_REMOTE_TTL", DEFAULT_TTL)),
        help="сколько секунд считать кэш серверной базы свежим",
    )
    args = parser.parse_args(argv)

    settings = load_settings()
    if not settings.db_path.exists():
        print(f"База не найдена: {settings.db_path}", file=sys.stderr)
        return 1

    remote = ROOT / ".tmp" / "vps-bot.db"
    if not args.no_remote:
        fetch_remote(remote, ttl=args.ttl)

    build_view_db(settings.db_path, remote if remote.exists() else None, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
