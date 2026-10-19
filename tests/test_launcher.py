"""Остановка предыдущего экземпляра бота: PID-файл и выбор процессов."""

import uuid
from pathlib import Path

import pytest

from bot import launcher

# %TEMP% закрыт песочницей, поэтому временные файлы — внутри проекта.
TMP_ROOT = Path(__file__).resolve().parent.parent / ".tmp"


@pytest.fixture
def pid_path() -> Path:
    folder = TMP_ROOT / f"launcher-{uuid.uuid4().hex[:8]}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "bot.pid"


def test_pid_file_roundtrip(pid_path, monkeypatch):
    monkeypatch.setattr(launcher, "PID_FILE", pid_path)

    launcher.write_pid(12345)
    assert launcher.read_pid() == 12345

    launcher.clear_pid()
    assert launcher.read_pid() is None


def test_pid_file_with_garbage_is_ignored(pid_path):
    pid_path.write_text("не число", encoding="utf-8")

    assert launcher.read_pid(pid_path) is None


@pytest.mark.parametrize(
    "processes, current, expected",
    [
        (
            [
                {"ProcessId": 10, "CommandLine": "python.exe -m bot.telegram_bot"},
                {"ProcessId": 11, "CommandLine": "python.exe -m bot.cli --provider demo"},
                {"ProcessId": 12, "CommandLine": None},
            ],
            99,
            [10],
        ),
        (
            [
                {"ProcessId": 10, "CommandLine": "python.exe -m bot.telegram_bot"},
                {"ProcessId": 13, "CommandLine": "python.exe -m bot.telegram_bot"},
            ],
            13,
            [10],
        ),
        ([], 1, []),
    ],
)
def test_pick_bot_pids_skips_other_python(processes, current, expected):
    assert launcher.pick_bot_pids(processes, current_pid=current) == expected


def test_stop_previous_is_quiet_when_nobody_runs(pid_path, monkeypatch):
    monkeypatch.setattr(launcher, "PID_FILE", pid_path)
    monkeypatch.setattr(launcher, "find_bot_pids", lambda: ([], "WMI"))

    assert launcher.stop_previous() == 0


def test_stop_previous_warns_but_does_not_block_without_wmi(pid_path, monkeypatch):
    monkeypatch.setattr(launcher, "PID_FILE", pid_path)
    monkeypatch.setattr(launcher, "find_bot_pids", lambda: ([], "WMI недоступен"))

    # Если проверить процессы нельзя, не запираем запуск: предупреждаем
    # и даём стартовать, иначе пользователь навсегда застрянет на этой проверке.
    assert launcher.stop_previous() == 0
