@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Виртуальное окружение не найдено. Создаю...
    uv venv .venv --python 3.13
    uv pip install --python .venv -e ".[dev]"
)

if not exist ".env" (
    echo Нет файла .env. Скопируйте .env.example в .env и впишите ключи.
    pause
    exit /b 1
)

echo [2/3] Проверка окружения
".venv\Scripts\python.exe" -m bot.doctor
if errorlevel 1 (
    echo.
    echo Проверка не прошла. Бот всё равно попробует запуститься,
    echo но если Telegram недоступен — включите VPN.
    echo.
)

echo [3/3] Запуск бота. Остановить — Ctrl+C.
".venv\Scripts\python.exe" -m bot.telegram_bot
echo.
echo Бот остановлен.
pause
