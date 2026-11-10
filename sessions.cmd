@echo off
rem List the last 20 dialogues and wait for a session number: sessions.cmd
rem Show one directly: sessions.cmd [session_id]
rem Combines local data/bot.db with a fresh copy of the live VPS database.
rem ASCII only: cmd reads this file in the console codepage.
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

if not exist ".venv\Scripts\python.exe" (
    echo No virtual environment. Run run-bot.cmd once.
    pause
    goto :end
)

set "VIEW_DB=.tmp\sessions-view.db"
".venv\Scripts\python.exe" -m bot.session_sync
if errorlevel 1 (
    echo Could not build the combined view; showing the local database.
    ".venv\Scripts\python.exe" -m bot.session_view %*
) else (
    ".venv\Scripts\python.exe" -m bot.session_view --db "%VIEW_DB%" %*
)

:end
if not "%~1"=="" goto :eof
if errorlevel 1 pause
