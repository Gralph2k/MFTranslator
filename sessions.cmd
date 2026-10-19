@echo off
rem List the last 20 dialogues and wait for a session number: sessions.cmd
rem Show one directly: sessions.cmd [session_id]
rem ASCII only: cmd reads this file in the console codepage.
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

if not exist ".venv\Scripts\python.exe" (
    echo No virtual environment. Run run-bot.cmd once.
    pause
    goto :end
)

".venv\Scripts\python.exe" -m bot.session_view %*

:end
if not "%~1"=="" goto :eof
if errorlevel 1 pause
