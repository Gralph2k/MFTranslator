"""Настройки из окружения и .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    """Всё, что нужно для запуска, в одном месте."""

    telegram_bot_token: str | None
    telegram_proxy: str | None
    deepseek_api_key: str | None
    deepseek_base_url: str
    deepseek_model: str
    db_path: Path
    safety_resources: str | None
    faces_dir: Path

    @property
    def has_llm(self) -> bool:
        return bool(self.deepseek_api_key)

    @property
    def has_telegram(self) -> bool:
        return bool(self.telegram_bot_token)


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def load_settings(env_file: Path | None = None) -> Settings:
    """Читает .env (если есть) и переменные окружения.

    Пустые значения считаются отсутствующими: в .env.example ключи оставлены
    пустыми специально, чтобы запуск без них давал понятную ошибку, а не 401.
    """
    load_dotenv(env_file or ROOT / ".env")

    db_path = Path(os.getenv("DB_PATH", "./data/bot.db"))
    if not db_path.is_absolute():
        db_path = ROOT / db_path

    faces_dir = Path(os.getenv("FACES_DIR", "./images"))
    if not faces_dir.is_absolute():
        faces_dir = ROOT / faces_dir

    return Settings(
        telegram_bot_token=_clean(os.getenv("TELEGRAM_BOT_TOKEN")),
        telegram_proxy=_clean(os.getenv("TELEGRAM_PROXY")),
        deepseek_api_key=_clean(os.getenv("DEEPSEEK_API_KEY")),
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        db_path=db_path,
        safety_resources=_clean(os.getenv("SAFETY_RESOURCES")),
        faces_dir=faces_dir,
    )
