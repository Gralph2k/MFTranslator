"""Запуск бота: остановить предыдущий экземпляр и только потом стартовать новый.

run-bot.cmd вызывает `python -m bot.launcher stop`. Если старый бот остался
висеть после закрытия окна или падения, Telegram получает два getUpdates
с одним токеном, и оба процесса начинают мешать друг другу. Поэтому перед
запуском ищем процессы `python -m bot.telegram_bot` и завершаем их.

Диалоги в базе здесь не трогаются: закрывается процесс, а не сессия пользователя.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PID_FILE = ROOT / "data" / "bot.pid"
BOT_MARKER = "bot.telegram_bot"
# Диапазоны Telegram. Нужны как запасной способ, если WMI недоступен:
# процесс бота всегда держит соединение с одним из этих адресов.
TELEGRAM_PREFIXES = ("149.154.", "91.108.", "91.105.")
STOP_TIMEOUT = 5.0


def read_pid(path: Path | None = None) -> int | None:
    """Читает PID из файла. Битый или пустой файл — это просто «нет PID»."""
    path = PID_FILE if path is None else path
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    try:
        pid = int(text)
    except ValueError:
        return None
    return pid if pid > 0 else None


def write_pid(pid: int | None = None, path: Path | None = None) -> None:
    path = PID_FILE if path is None else path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(pid if pid is not None else os.getpid()), encoding="utf-8")


def clear_pid(path: Path | None = None) -> None:
    path = PID_FILE if path is None else path
    try:
        path.unlink()
    except OSError:
        pass


def is_alive(pid: int) -> bool:
    """Проверяет процесс без psutil: на Windows через OpenProcess + exit code."""
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.GetExitCodeProcess.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel32.GetExitCodeProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

        process_query_limited_information = 0x1000
        handle = kernel32.OpenProcess(
            process_query_limited_information, False, pid
        )
        if not handle:
            return False
        try:
            code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _powershell() -> str | None:
    return shutil.which("powershell") or shutil.which("pwsh")


def list_python_processes() -> list[dict[str, Any]] | None:
    """Возвращает ProcessId и CommandLine python-процессов.

    None значит «не смогли посмотреть»: WMI может быть недоступен в песочнице
    или на урезанной Windows. В этом случае нельзя безопасно гадать по PID.
    """
    shell = _powershell()
    if shell is None:
        return None

    script = (
        "Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%'\" | "
        "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            [shell, "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return None
    return [item for item in data if isinstance(item, dict)]


def pick_bot_pids(
    processes: list[dict[str, Any]], current_pid: int | None = None
) -> list[int]:
    """Оставляет только процессы, запущенные как `python -m bot.telegram_bot`."""
    current = os.getpid() if current_pid is None else current_pid
    pids: set[int] = set()
    for item in processes:
        try:
            pid = int(item.get("ProcessId"))
        except (TypeError, ValueError):
            continue
        command_line = str(item.get("CommandLine") or "")
        if pid != current and BOT_MARKER in command_line:
            pids.add(pid)
    return sorted(pids)


def find_bot_pids() -> tuple[list[int], str]:
    """Ищет запущенные боты. Второй элемент — чем искали, для сообщения."""
    processes = list_python_processes()
    if processes is not None:
        return pick_bot_pids(processes), "WMI"

    # WMI недоступен (песочница, урезанная Windows). Тогда два запасных пути:
    # PID-файл самого бота и процесс Python с живым соединением к Telegram.
    pid = read_pid()
    if pid is not None and is_alive(pid) and _looks_like_python(pid):
        return [pid], "PID-файл"

    telegram = _telegram_pids()
    if telegram:
        return telegram, "соединение с Telegram"
    return [], "WMI недоступен"


def _telegram_pids() -> list[int]:
    """PID python-процессов, которые прямо сейчас соединены с Telegram."""
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return []

    pids: set[int] = set()
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0].upper() != "TCP":
            continue
        remote = parts[2]
        if not remote.endswith(":443"):
            continue
        host = remote.rsplit(":", 1)[0]
        if not host.startswith(TELEGRAM_PREFIXES):
            continue
        try:
            pid = int(parts[-1])
        except ValueError:
            continue
        if pid > 0 and _looks_like_python(pid):
            pids.add(pid)
    return sorted(pids)


def _looks_like_python(pid: int) -> bool:
    """Проверяет, что PID — Python, а не, скажем, Telegram Desktop."""
    path = _process_path(pid)
    if path:
        return Path(path).name.lower().startswith("python")

    # Запасной путь: OpenProcess мог быть запрещён (другой пользователь/права).
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return "python" in result.stdout.lower()


def _process_path(pid: int) -> str | None:
    """Путь к exe через WinAPI: работает без WMI и без tasklist."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    handle = kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
    if not handle:
        return None
    try:
        buffer = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(len(buffer))
        if not kernel32.QueryFullProcessImageNameW(
            handle, 0, buffer, ctypes.byref(size)
        ):
            return None
        return buffer.value
    finally:
        kernel32.CloseHandle(handle)


def _terminate(pid: int) -> None:
    if os.name == "nt":
        # taskkill умеет дерево процессов: .venv-лаунчер и базовый Python — разные PID.
        try:
            result = subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )
            if result.returncode == 0:
                return
        except (OSError, subprocess.SubprocessError):
            pass

        # Запасной путь, если taskkill запрещён (например, песочницей).
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        kernel32.TerminateProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

        handle = kernel32.OpenProcess(0x0001, False, pid)  # PROCESS_TERMINATE
        if handle:
            try:
                kernel32.TerminateProcess(handle, 1)
            finally:
                kernel32.CloseHandle(handle)
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass


def stop_previous() -> int:
    """Закрывает все найденные экземпляры бота. 0 — можно запускать нового."""
    pids, source = find_bot_pids()
    if not pids:
        clear_pid()
        if source == "WMI недоступен":
            print(
                "Не удалось проверить процессы (WMI недоступен). "
                "Если старый бот ещё открыт, закрой его вручную."
            )
        else:
            print("Предыдущий бот не найден — запускаю нового.")
        return 0

    print(f"Останавливаю предыдущего бота: PID {', '.join(map(str, pids))} ({source}).")
    for pid in pids:
        if is_alive(pid):
            _terminate(pid)

    deadline = time.monotonic() + STOP_TIMEOUT
    while time.monotonic() < deadline and any(is_alive(pid) for pid in pids):
        time.sleep(0.2)

    left = [pid for pid in pids if is_alive(pid)]
    if left:
        print(
            f"Не удалось остановить PID {', '.join(map(str, left))}. "
            "Закрой окно бота вручную и повтори запуск."
        )
        return 1

    clear_pid()
    print("Предыдущий бот остановлен.")
    return 0


def status() -> int:
    """Печатает, запущен ли бот. Полезно, когда непонятно, кто держит токен."""
    pids, source = find_bot_pids()
    pid_file = read_pid()
    if pids:
        print(f"Бот запущен: PID {', '.join(map(str, pids))} ({source}).")
    else:
        print("Бот не запущен.")
    if pid_file is not None:
        print(f"PID-файл: {pid_file}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    command = args[0] if args else "status"
    if command == "stop":
        return stop_previous()
    if command == "status":
        return status()
    print("Использование: python -m bot.launcher [stop|status]")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
