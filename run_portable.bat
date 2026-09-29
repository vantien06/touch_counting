@echo off
setlocal
set "ROOT=%~dp0"

if not exist "%ROOT%environment\python.exe" (
    if not exist "%ROOT%environment.zip" (
        echo Missing environment.zip
        pause
        exit /b 1
    )
    echo Extracting the bundled Python environment. This may take a few minutes...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%ROOT%environment.zip' -DestinationPath '%ROOT%environment' -Force"
    if errorlevel 1 (
        echo Failed to extract environment.zip
        pause
        exit /b 1
    )
)

if exist "%ROOT%environment\Scripts\conda-unpack.exe" (
    "%ROOT%environment\Scripts\conda-unpack.exe"
)

"%ROOT%environment\python.exe" "%ROOT%gui.py"
if errorlevel 1 pause