"""Проверка окружения перед запуском: токен, прокси, ключ модели.

Запуск: python -m bot.doctor
"""

from __future__ import annotations

import asyncio
import sys

import httpx

from .config import Settings, load_settings
from .tls import httpx_verify, is_certificate_error


class Check:
    def __init__(self, name: str) -> None:
        self.name = name
        self.ok = False
        self.detail = ""
        self.hint = ""


async def check_telegram(settings: Settings) -> Check:
    check = Check("Telegram")
    if not settings.telegram_bot_token:
        check.detail = "нет TELEGRAM_BOT_TOKEN"
        check.hint = "Создайте бота у @BotFather и впишите токен в .env"
        return check

    proxy = settings.telegram_proxy
    try:
        async with httpx.AsyncClient(proxy=proxy, timeout=20.0, verify=httpx_verify()) as client:
            response = await client.get(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/getMe"
            )
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
        if is_certificate_error(exc):
            check.detail = "сертификат соединения не принят"
            check.hint = (
                "VPN или антивирус подменяет HTTPS. Разрешите ему проверку "
                "или отключите перехват для api.telegram.org."
            )
            return check
        check.detail = f"нет соединения с api.telegram.org ({type(exc).__name__})"
        check.hint = (
            "Похоже, Telegram блокируется в этой сети. Включите VPN "
            "или задайте TELEGRAM_PROXY (http:// или socks5://)."
        )
        return check
    except httpx.HTTPError as exc:
        check.detail = f"ошибка транспорта: {exc}"
        check.hint = "Проверьте прокси и соединение."
        return check

    if response.status_code == 401:
        check.detail = "токен не принят (401)"
        check.hint = "Перевыпустите токен у @BotFather и обновите .env."
        return check
    if response.status_code != 200:
        check.detail = f"HTTP {response.status_code}"
        check.hint = "Посмотрите тело ответа Telegram в логах."
        return check

    data = response.json()
    if not data.get("ok"):
        check.detail = f"Telegram ответил ошибкой: {data.get('description')}"
        return check

    username = (data.get("result") or {}).get("username")
    check.ok = True
    check.detail = f"бот @{username}"
    if proxy:
        check.detail += f", через прокси {proxy}"
    return check


async def check_deepseek(settings: Settings) -> Check:
    check = Check("DeepSeek")
    if not settings.has_llm:
        check.detail = "нет DEEPSEEK_API_KEY"
        check.hint = "Возьмите ключ на platform.deepseek.com и впишите в .env"
        return check

    headers = {"Authorization": f"Bearer {settings.deepseek_api_key}"}
    try:
        async with httpx.AsyncClient(timeout=25.0, verify=httpx_verify()) as client:
            response = await client.get(
                f"{settings.deepseek_base_url}/models", headers=headers
            )
    except httpx.HTTPError as exc:
        if is_certificate_error(exc):
            check.detail = "сертификат соединения не принят"
            check.hint = (
                "VPN или антивирус подменяет HTTPS. Разрешите ему проверку "
                "или отключите перехват для api.deepseek.com."
            )
            return check
        check.detail = f"нет соединения ({type(exc).__name__})"
        check.hint = "Проверьте сеть и DEEPSEEK_BASE_URL."
        return check

    if response.status_code == 401:
        check.detail = "ключ не принят (401)"
        check.hint = "Проверьте DEEPSEEK_API_KEY: возможно, он отозван или с опечаткой."
        return check
    if response.status_code == 402:
        check.detail = "на счету нет средств (402)"
        check.hint = "Пополните баланс на platform.deepseek.com."
        return check
    if response.status_code != 200:
        check.detail = f"HTTP {response.status_code}"
        check.hint = "Проверьте DEEPSEEK_BASE_URL и статус сервиса."
        return check

    check.ok = True
    check.detail = f"ключ работает, модель по умолчанию — {settings.deepseek_model}"
    return check


async def run() -> int:
    settings = load_settings()
    checks = [await check_telegram(settings), await check_deepseek(settings)]

    print("Проверка окружения\n")
    for check in checks:
        mark = "OK  " if check.ok else "ОШИБКА"
        print(f"[{mark}] {check.name}: {check.detail}")
        if check.hint:
            print(f"         → {check.hint}")

    failed = [c for c in checks if not c.ok]
    print()
    if failed:
        print(f"Не готово: {len(failed)} из {len(checks)}. Бот не запустится, пока это не исправлено.")
        return 1

    print("Всё готово: python -m bot.telegram_bot")
    return 0


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass
    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()
