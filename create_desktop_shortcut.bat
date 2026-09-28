@echo off
setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$project = [IO.Path]::GetFullPath('%~dp0'); $batch = Join-Path $project 'run_touch_counting.bat'; $icon = Join-Path $project 'logo\app.ico'; $desktop = [Environment]::GetFolderPath('Desktop'); $shortcutPath = Join-Path $desktop 'Touch Counting.lnk'; $shell = New-Object -ComObject WScript.Shell; $shortcut = $shell.CreateShortcut($shortcutPath); $shortcut.TargetPath = $batch; $shortcut.WorkingDirectory = $project; $shortcut.IconLocation = $icon; $shortcut.Description = 'Start Touch Counting'; $shortcut.Save(); Write-Host ('Created: ' + $shortcutPath)"

pause
endlocal
