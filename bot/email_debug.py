"""Отладочный дублик «Проверки анкеты»: фото и переписка уходят на почту владельцу.

Временная функция на период тестирования: включается env PROFILE_DEBUG_EMAIL
(плюс SMTP_USER/SMTP_PASS), выключается очисткой переменной и рестартом бота.
Отправка — fire-and-forget таской: недоступный Яндекс не должен задерживать
ответ пользователю и тем более ронять оценку фото.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from .config import Settings

log = logging.getLogger(__name__)

# Секунды: письмо с четырьмя JPEG не должно висеть в обработчике минуты.
SMTP_TIMEOUT = 15.0
TASK_TIMEOUT = 60.0


def send_email_sync(
    settings: Settings,
    subject: str,
    body: str,
    photos: list[tuple[str, bytes]],
) -> None:
    message = EmailMessage()
    message["From"] = settings.smtp_user
    message["To"] = settings.profile_debug_email
    message["Subject"] = subject
    message.set_content(body)
    for filename, data in photos:
        message.add_attachment(
            data,
            maintype="image",
            subtype="jpeg",
            filename=filename,
        )

    with smtplib.SMTP_SSL(settings.smtp_host or "smtp.yandex.ru", settings.smtp_port, timeout=SMTP_TIMEOUT) as server:
        server.login(settings.smtp_user, settings.smtp_pass)
        server.send_message(message)


def send_debug_email(
    settings: Settings,
    subject: str,
    body: str,
    photos: list[tuple[str, bytes]],
) -> asyncio.Task:
    """Планирует отправку в фоне и сразу возвращает управление."""

    async def _run() -> None:
        try:
            await asyncio.wait_for(
                asyncio.to_thread(send_email_sync, settings, subject, body, photos),
                timeout=TASK_TIMEOUT,
            )
        except Exception:
            # Почта — только отладка: логируем и живём дальше.
            log.exception("отладочное письмо не ушло")

    return asyncio.create_task(_run())
