@echo off
cd /d "%~dp0"
python gui.py
if errorlevel 1 (
    echo.
    echo The application could not start.
    pause
)