"""SQLite: пользователи, сессии, разборы.

Храним минимум: стенограмму и состояние. Никаких профилей «жены» и прочих
догадок о реальной жизни пользователя — это не нужно продукту и опасно.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scenario_id TEXT NOT NULL,
    state_json TEXT NOT NULL,
    history_json TEXT NOT NULL,
    user_turns INTEGER NOT NULL DEFAULT 0,
    finished INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS debriefs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id, finished);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class StoredSession:
    id: int
    user_id: int
    scenario: str
    state: dict[str, Any]
    history: list[dict[str, str]]
    user_turns: int
    finished: bool
    created_at: str
    updated_at: str | None


@dataclass
class SessionOverview:
    """Строка списка сессий: без стенограммы, зато с пользователем и оценкой."""

    id: int
    user_id: int
    telegram_id: int
    scenario: str
    created_at: str
    updated_at: str | None
    user_turns: int
    finished: bool
    debrief: str | None


class Storage:
    """Тонкая обёртка над SQLite. Для MVP одного файла достаточно."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._migrate()
            self._conn.commit()

    def _migrate(self) -> None:
        """Доводит старую базу до текущей схемы, не теряя диалоги."""
        columns = {
            row["name"] for row in self._conn.execute("PRAGMA table_info(sessions)")
        }
        if "updated_at" in columns:
            return
        self._conn.execute("ALTER TABLE sessions ADD COLUMN updated_at TEXT")
        # Для старых строк время последнего хода не сохранялось: берём разбор,
        # а если его нет — момент начала, чтобы список не падал на NULL.
        self._conn.execute(
            """UPDATE sessions
               SET updated_at = COALESCE(
                   (SELECT MAX(created_at) FROM debriefs
                    WHERE debriefs.session_id = sessions.id),
                   created_at)
               WHERE updated_at IS NULL"""
        )

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def ensure_user(self, telegram_id: int) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)
            ).fetchone()
            if row is not None:
                return int(row["id"])
            cursor = self._conn.execute(
                "INSERT INTO users (telegram_id, created_at) VALUES (?, ?)",
                (telegram_id, _now()),
            )
            self._conn.commit()
            return int(cursor.lastrowid)

    def create_session(
        self,
        user_id: int,
        scenario_id: str,
        state: dict[str, Any],
        history: list[dict[str, str]],
    ) -> int:
        with self._lock:
            now = _now()
            cursor = self._conn.execute(
                """INSERT INTO sessions
                   (user_id, scenario_id, state_json, history_json, user_turns, finished,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, 0, 0, ?, ?)""",
                (user_id, scenario_id, json.dumps(state, ensure_ascii=False),
                 json.dumps(history, ensure_ascii=False), now, now),
            )
            self._conn.commit()
            return int(cursor.lastrowid)

    def save_session(
        self,
        session_id: int,
        state: dict[str, Any],
        history: list[dict[str, str]],
        user_turns: int,
        finished: bool,
    ) -> None:
        with self._lock:
            self._conn.execute(
                """UPDATE sessions
                   SET state_json = ?, history_json = ?, user_turns = ?, finished = ?,
                       updated_at = ?
                   WHERE id = ?""",
                (json.dumps(state, ensure_ascii=False),
                 json.dumps(history, ensure_ascii=False),
                 user_turns, int(finished), _now(), session_id),
            )
            self._conn.commit()

    def get_active_session(self, user_id: int) -> StoredSession | None:
        with self._lock:
            row = self._conn.execute(
                """SELECT * FROM sessions
                   WHERE user_id = ? AND finished = 0
                   ORDER BY id DESC LIMIT 1""",
                (user_id,),
            ).fetchone()
        return _row_to_session(row) if row is not None else None

    def get_session(self, session_id: int) -> StoredSession | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
        return _row_to_session(row) if row is not None else None

    def list_sessions(self, user_id: int) -> list[StoredSession]:
        """Все сессии пользователя по порядку: нужно для проверок и выгрузки."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM sessions WHERE user_id = ? ORDER BY id", (user_id,)
            ).fetchall()
        return [_row_to_session(row) for row in rows]

    def list_overview(self, limit: int | None = None) -> list[SessionOverview]:
        """Все сессии для просмотра: новые сверху, с последним разбором."""
        query = _OVERVIEW_SQL + " ORDER BY s.id DESC"
        params: tuple[int, ...] = ()
        if limit is not None:
            query += " LIMIT ?"
            params = (limit,)
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return [_row_to_overview(row) for row in rows]

    def count_sessions(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) AS total FROM sessions").fetchone()
        return int(row["total"])

    def get_overview(self, session_id: int) -> SessionOverview | None:
        with self._lock:
            row = self._conn.execute(
                _OVERVIEW_SQL + " WHERE s.id = ?", (session_id,)
            ).fetchone()
        return _row_to_overview(row) if row is not None else None

    def save_debrief(self, session_id: int, payload: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO debriefs (session_id, payload, created_at) VALUES (?, ?, ?)",
                (session_id, payload, _now()),
            )
            self._conn.commit()

    def last_debrief(self, user_id: int) -> str | None:
        with self._lock:
            row = self._conn.execute(
                """SELECT d.payload FROM debriefs d
                   JOIN sessions s ON s.id = d.session_id
                   WHERE s.user_id = ?
                   ORDER BY d.id DESC LIMIT 1""",
                (user_id,),
            ).fetchone()
        return str(row["payload"]) if row is not None else None

    def delete_user(self, telegram_id: int) -> None:
        """Удаление по запросу: вся история, сессии и разборы."""
        with self._lock:
            row = self._conn.execute(
                "SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)
            ).fetchone()
            if row is None:
                return
            self._conn.execute("DELETE FROM users WHERE id = ?", (row["id"],))
            self._conn.commit()


def _row_to_session(row: sqlite3.Row) -> StoredSession:
    return StoredSession(
        id=int(row["id"]),
        user_id=int(row["user_id"]),
        scenario=str(row["scenario_id"]),
        state=json.loads(row["state_json"]),
        history=json.loads(row["history_json"]),
        user_turns=int(row["user_turns"]),
        finished=bool(row["finished"]),
        created_at=str(row["created_at"]),
        updated_at=row["updated_at"],
    )


_OVERVIEW_SQL = """
SELECT s.id, s.user_id, u.telegram_id, s.scenario_id, s.created_at, s.updated_at,
       s.user_turns, s.finished,
       (SELECT d.payload FROM debriefs d
        WHERE d.session_id = s.id ORDER BY d.id DESC LIMIT 1) AS debrief
FROM sessions s JOIN users u ON u.id = s.user_id
"""


def _row_to_overview(row: sqlite3.Row) -> SessionOverview:
    return SessionOverview(
        id=int(row["id"]),
        user_id=int(row["user_id"]),
        telegram_id=int(row["telegram_id"]),
        scenario=str(row["scenario_id"]),
        created_at=str(row["created_at"]),
        updated_at=row["updated_at"],
        user_turns=int(row["user_turns"]),
        finished=bool(row["finished"]),
        debrief=str(row["debrief"]) if row["debrief"] is not None else None,
    )
