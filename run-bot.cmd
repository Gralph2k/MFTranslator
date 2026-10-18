@echo off
rem Batch files must stay ASCII: cmd.exe reads them in the OEM codepage and
rem mangles UTF-8 Cyrillic. Russian text is printed by Python instead.
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] No virtual environment. Creating...
    uv venv .venv --python 3.13
    uv pip install --python .venv -e ".[dev]"
    if errorlevel 1 goto :failed
)

if not exist ".env" (
    echo No .env file. Copy .env.example to .env and fill in the keys.
    goto :end
)

echo [2/3] Environment check
".venv\Scripts\python.exe" -m bot.doctor
if errorlevel 1 (
    echo.
    echo Check failed. Starting anyway; if Telegram is unreachable, turn on VPN.
    echo.
)

echo [3/3] Starting bot. Stop with Ctrl+C.
".venv\Scripts\python.exe" -m bot.telegram_bot
echo.
echo Bot stopped.
goto :end

:failed
echo Setup failed. Check the output above.

:end
pause
