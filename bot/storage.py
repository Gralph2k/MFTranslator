"""SQLite: пользователи, сессии, разборы, проверки анкеты.

Храним минимум: стенограмму, состояние и - для «Проверки анкеты» - текст,
который пользователь сам прислал для разбора. Никаких догадок о реальной
жизни пользователя: только то, что он принёс сам.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .scenario import SCENARIO_ID_ALIASES

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
    ended_by_persona INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS debriefs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS profile_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    phase TEXT NOT NULL DEFAULT 'name',
    name TEXT NOT NULL DEFAULT '',
    age INTEGER,
    bio TEXT NOT NULL DEFAULT '',
    text_iterations INTEGER NOT NULL DEFAULT 0,
    photo_reviews INTEGER NOT NULL DEFAULT 0,
    last_text_score INTEGER,
    last_text_verdict TEXT NOT NULL DEFAULT '',
    last_photo_verdict TEXT NOT NULL DEFAULT '',
    last_rewrite TEXT NOT NULL DEFAULT '',
    photo_contents TEXT NOT NULL DEFAULT '[]',
    completed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id, finished);
CREATE INDEX IF NOT EXISTS idx_profile_checks_user ON profile_checks(user_id, completed);
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
    # Персонаж сам закончил разговор (красная линия): продолжение после такого
    # разговора идёт по канону, а не по реальной переписке.
    ended_by_persona: bool = False


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


@dataclass
class StoredProfileCheck:
    """Прогон «Проверки анкеты»: текст живёт в базе, фото - никогда."""

    id: int
    user_id: int
    phase: str  # name | bio | menu | photos | done | abandoned
    name: str
    age: int | None
    bio: str
    text_iterations: int
    photo_reviews: int
    last_text_score: int | None
    last_text_verdict: str
    last_photo_verdict: str
    completed: bool
    created_at: str
    updated_at: str | None
    # Что на его фото, нейтрально (JSON-список коротких описаний): выжимка
    # для героинь, чтобы им было о чём спросить. С дефолтом и в конце -
    # после полей без дефолтов.
    photo_contents: list[str] = field(default_factory=list)
    # Последняя предложенная им правка анкеты (rewrite.after из разбора):
    # на повторе текст с ней совпадать «разрешено» без критики.
    last_rewrite: str = ""

    @property
    def is_active(self) -> bool:
        return self.phase not in ("done", "abandoned")


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
        if "updated_at" not in columns:
            self._conn.execute("ALTER TABLE sessions ADD COLUMN updated_at TEXT")
            # Для старых строк время последнего хода не сохранялось: берём разбор,
            # а если его нет - момент начала, чтобы список не падал на NULL.
            self._conn.execute(
                """UPDATE sessions
                   SET updated_at = COALESCE(
                       (SELECT MAX(created_at) FROM debriefs
                        WHERE debriefs.session_id = sessions.id),
                       created_at)
                   WHERE updated_at IS NULL"""
            )
        if "ended_by_persona" not in columns:
            # Старые сессии не писали, кто закончил разговор: считаем, что игрок.
            self._conn.execute(
                "ALTER TABLE sessions ADD COLUMN ended_by_persona "
                "INTEGER NOT NULL DEFAULT 0"
            )
        # Сценарии переехали в `scenarios/<сцена>/<героиня>/`, id стал путём.
        # Переименовываем старые плоские id прямо в БД, иначе потеряются
        # продолжения (continues) и списки сессий. Идемпотентно: после
        # первого прогона старых id не остаётся.
        for old_id, new_id in SCENARIO_ID_ALIASES.items():
            self._conn.execute(
                "UPDATE sessions SET scenario_id = ? WHERE scenario_id = ?",
                (new_id, old_id),
            )
        # «Проверка анкеты»: описания содержимого фото для героинь - колонка
        # младше самой таблицы, у кого-то её ещё нет.
        pc_columns = {
            row["name"] for row in self._conn.execute("PRAGMA table_info(profile_checks)")
        }
        if pc_columns and "photo_contents" not in pc_columns:
            self._conn.execute(
                "ALTER TABLE profile_checks ADD COLUMN photo_contents TEXT "
                "NOT NULL DEFAULT '[]'"
            )
        # Своя же рекомендованная правка (rewrite): чтобы при повторном разборе
        # не критиковать текст, который бот сам и предложил.
        if pc_columns and "last_rewrite" not in pc_columns:
            self._conn.execute(
                "ALTER TABLE profile_checks ADD COLUMN last_rewrite TEXT "
                "NOT NULL DEFAULT ''"
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
        ended_by_persona: bool = False,
    ) -> None:
        with self._lock:
            self._conn.execute(
                """UPDATE sessions
                   SET state_json = ?, history_json = ?, user_turns = ?, finished = ?,
                       ended_by_persona = ?, updated_at = ?
                   WHERE id = ?""",
                (json.dumps(state, ensure_ascii=False),
                 json.dumps(history, ensure_ascii=False),
                 user_turns, int(finished), int(ended_by_persona), _now(), session_id),
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

    def last_session(self, user_id: int) -> StoredSession | None:
        """Последняя сессия пользователя любого статуса - для антиповтора героини."""
        with self._lock:
            row = self._conn.execute(
                """SELECT * FROM sessions
                   WHERE user_id = ?
                   ORDER BY id DESC LIMIT 1""",
                (user_id,),
            ).fetchone()
        return _row_to_session(row) if row is not None else None

    def last_session_for(self, user_id: int, scenario_id: str) -> StoredSession | None:
        """Последняя попытка пройти конкретный сценарий - для сценариев-продолжений."""
        with self._lock:
            row = self._conn.execute(
                """SELECT * FROM sessions
                   WHERE user_id = ? AND scenario_id = ?
                   ORDER BY id DESC LIMIT 1""",
                (user_id, scenario_id),
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
        query = _OVERVIEW_SQL + " ORDER BY s.created_at DESC, s.id DESC"
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
        """Удаление по запросу: вся история, сессии, разборы и проверки анкеты."""
        with self._lock:
            row = self._conn.execute(
                "SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)
            ).fetchone()
            if row is None:
                return
            self._conn.execute("DELETE FROM users WHERE id = ?", (row["id"],))
            self._conn.commit()

    # --- «Проверка анкеты» -------------------------------------------------

    def create_profile_check(self, user_id: int) -> int:
        """Новый прогон; прежние незакрытые помечаем покинутыми."""
        with self._lock:
            now = _now()
            self._conn.execute(
                """UPDATE profile_checks SET phase = 'abandoned', updated_at = ?
                   WHERE user_id = ? AND phase NOT IN ('done', 'abandoned')""",
                (now, user_id),
            )
            cursor = self._conn.execute(
                """INSERT INTO profile_checks (user_id, phase, created_at, updated_at)
                   VALUES (?, 'name', ?, ?)""",
                (user_id, now, now),
            )
            self._conn.commit()
            return int(cursor.lastrowid)

    def get_active_profile_check(self, user_id: int) -> StoredProfileCheck | None:
        with self._lock:
            row = self._conn.execute(
                """SELECT * FROM profile_checks
                   WHERE user_id = ? AND phase NOT IN ('done', 'abandoned')
                   ORDER BY id DESC LIMIT 1""",
                (user_id,),
            ).fetchone()
        return _row_to_profile_check(row) if row is not None else None

    def update_profile_check(self, check_id: int, **fields: Any) -> None:
        """Точечное обновление; имена колонок - из белого списка ниже.

        Списки и словари (photo_contents) сериализуются в JSON: в базе
        строка, в памяти объекта - список.
        """
        allowed = {
            "phase", "name", "age", "bio", "text_iterations", "photo_reviews",
            "last_text_score", "last_text_verdict", "last_photo_verdict",
            "last_rewrite", "photo_contents", "completed",
        }
        updates = {}
        for key, value in fields.items():
            if key not in allowed:
                continue
            if isinstance(value, (list, dict)):
                value = json.dumps(value, ensure_ascii=False)
            updates[key] = value
        if not updates:
            return
        sets = ", ".join(f"{key} = ?" for key in updates)
        params = list(updates.values()) + [_now(), check_id]
        with self._lock:
            self._conn.execute(
                f"UPDATE profile_checks SET {sets}, updated_at = ? WHERE id = ?",
                params,
            )
            self._conn.commit()

    def last_completed_profile(self, user_id: int) -> StoredProfileCheck | None:
        """Последняя доведённая до конца проверка: её героини берут в разговор."""
        with self._lock:
            row = self._conn.execute(
                """SELECT * FROM profile_checks
                   WHERE user_id = ? AND completed = 1 AND bio != ''
                   ORDER BY id DESC LIMIT 1""",
                (user_id,),
            ).fetchone()
        return _row_to_profile_check(row) if row is not None else None

    def has_completed_profile(self, user_id: int) -> bool:
        return self.last_completed_profile(user_id) is not None


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
        ended_by_persona=bool(row["ended_by_persona"]),
    )


def _row_to_profile_check(row: sqlite3.Row) -> StoredProfileCheck:
    age = row["age"]
    try:
        contents = json.loads(row["photo_contents"] or "[]")
    except (json.JSONDecodeError, TypeError):
        contents = []
    if not isinstance(contents, list):
        contents = []
    return StoredProfileCheck(
        id=int(row["id"]),
        user_id=int(row["user_id"]),
        phase=str(row["phase"]),
        name=str(row["name"]),
        age=int(age) if age is not None else None,
        bio=str(row["bio"]),
        text_iterations=int(row["text_iterations"]),
        photo_reviews=int(row["photo_reviews"]),
        last_text_score=row["last_text_score"],
        last_text_verdict=str(row["last_text_verdict"]),
        last_photo_verdict=str(row["last_photo_verdict"]),
        photo_contents=[str(item) for item in contents],
        last_rewrite=str(row["last_rewrite"] or ""),
        completed=bool(row["completed"]),
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
