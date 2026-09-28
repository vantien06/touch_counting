@echo off
setlocal
cd /d "%~dp0"

echo Activating Conda environment: touchCounting
call conda activate touchCounting
if errorlevel 1 (
    echo.
    echo Could not activate the Conda environment touchCounting.
    pause
    exit /b 1
)

echo Starting Touch Counting GUI...
python gui.py

if errorlevel 1 (
    echo.
    echo Touch Counting stopped with an error.
    pause
)
endlocal
