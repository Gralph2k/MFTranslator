@echo off
rem ASCII only: see run-bot.cmd for why.
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

if not exist ".venv\Scripts\python.exe" (
    echo No virtual environment. Run run-bot.cmd once.
    goto :end
)

echo Local game in terminal: demo - canned replies, no network; deepseek - real model.
set "PROVIDER=demo"
set /p "PROVIDER=Provider [demo/deepseek]: "
if "%PROVIDER%"=="" set "PROVIDER=demo"

set "SCENARIO=first_message"
set /p "SCENARIO=Scenario [first_message/first_call/first_date/eva_message]: "
if "%SCENARIO%"=="" set "SCENARIO=first_message"

".venv\Scripts\python.exe" -m bot.cli --provider %PROVIDER% --scenario %SCENARIO%

:end
pause
