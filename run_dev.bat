@echo off
setlocal
title MyAssetHub - Development Mode

echo [Launcher] Starting MyAssetHub (Dev Mode)...

if not exist ".venv" (
    echo [Error] .venv not found.
    pause
    exit /b 1
)

set MYASSETHUB_DEV=1

echo [Launcher] Running main.py with --dev...
".venv\Scripts\python.exe" "MyAssetHub_Root\app\main.py" --dev

if %ERRORLEVEL% neq 0 (
    echo [Launcher] App exited with error code: %ERRORLEVEL%
    pause
)

endlocal
