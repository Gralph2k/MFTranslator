@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

if not exist ".venv\Scripts\python.exe" (
    echo Виртуальное окружение не найдено. Запустите run-bot.cmd один раз.
    pause
    exit /b 1
)

echo Локальная игра в терминале.
echo   demo     - заготовленные ответы, без сети и ключей
echo   deepseek - настоящая модель
echo.
set /p PROVIDER="Провайдер [demo/deepseek]: "
if "%PROVIDER%"=="" set PROVIDER=demo

set /p SCENARIO="Сценарий [friday_evening/reunion_call]: "
if "%SCENARIO%"=="" set SCENARIO=friday_evening

".venv\Scripts\python.exe" -m bot.cli --provider %PROVIDER% --scenario %SCENARIO%
pause
