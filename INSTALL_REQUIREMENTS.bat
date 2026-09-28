@echo off
cd /d "%~dp0"
echo Installing Python packages for the current user...
python -m pip install --user -r requirements.txt
if errorlevel 1 (
    echo.
    echo Installation failed. Check that Python and pip are available.
    pause
    exit /b 1
)
echo.
echo Installation completed.
pause