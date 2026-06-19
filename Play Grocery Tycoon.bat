@echo off
REM Double-click this on Windows to play. First run sets itself up automatically.
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py main.py
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    python main.py
  ) else (
    echo Python 3 is required. Install it from https://www.python.org/downloads/
    echo During install, tick "Add Python to PATH".
    pause
  )
)
