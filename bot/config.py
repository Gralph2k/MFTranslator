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
    # Проверка анкеты: vision-модель (OpenRouter) и отладочная почта.
    vision_api_key: str | None
    vision_base_url: str
    vision_model: str
    smtp_host: str | None
    smtp_port: int
    smtp_user: str | None
    smtp_pass: str | None
    # Пусто - дублик фото на почту выключен. Время тестирования; вырубить = очистить и рестарт.
    profile_debug_email: str | None
    # Дублик в Telegram-чат владельца: работает там, где SMTP закрыт хостером.
    profile_debug_chat_id: int | None

    @property
    def has_llm(self) -> bool:
        return bool(self.deepseek_api_key)

    @property
    def has_telegram(self) -> bool:
        return bool(self.telegram_bot_token)

    @property
    def has_vision(self) -> bool:
        return bool(self.vision_api_key)

    @property
    def debug_email_enabled(self) -> bool:
        """Почтовый дублик включён, только если есть и адрес, и пароль."""
        return bool(self.profile_debug_email and self.smtp_user and self.smtp_pass)

    @property
    def debug_chat_enabled(self) -> bool:
        """Telegram-дублик включён:_chat_id задан (может быть только у владельца)."""
        return self.profile_debug_chat_id is not None


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _int_or_none(value: str | None) -> int | None:
    try:
        return int(value) if value else None
    except ValueError:
        return None


def load_settings(env_file: Path | None = None) -> Settings:
    """Читает .env (если есть) и переменные окружения.

    Пустые значения считаются отсутствующими: в .env.example ключи оставлены
    пустыми специально, чтобы запуск без них давал понятную ошибку, а не 401.
    """
    load_dotenv(env_file or ROOT / ".env")

    db_path = Path(os.getenv("DB_PATH", "./data/bot.db"))
    if not db_path.is_absolute():
        db_path = ROOT / db_path

    return Settings(
        telegram_bot_token=_clean(os.getenv("TELEGRAM_BOT_TOKEN")),
        telegram_proxy=_clean(os.getenv("TELEGRAM_PROXY")),
        deepseek_api_key=_clean(os.getenv("DEEPSEEK_API_KEY")),
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        db_path=db_path,
        safety_resources=_clean(os.getenv("SAFETY_RESOURCES")),
        vision_api_key=_clean(os.getenv("VISION_API_KEY")),
        vision_base_url=os.getenv("VISION_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/"),
        vision_model=os.getenv("VISION_MODEL", "google/gemini-2.5-flash-lite"),
        smtp_host=_clean(os.getenv("SMTP_HOST")),
        smtp_port=_int_or_none(os.getenv("SMTP_PORT")) or 465,
        smtp_user=_clean(os.getenv("SMTP_USER")),
        smtp_pass=_clean(os.getenv("SMTP_PASS")),
        profile_debug_email=_clean(os.getenv("PROFILE_DEBUG_EMAIL")),
        profile_debug_chat_id=_int_or_none(os.getenv("PROFILE_DEBUG_CHAT_ID")),
    )
