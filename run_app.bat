@echo off
setlocal
title MyAssetHub

echo [Launcher] Starting MyAssetHub...

if not exist ".venv" (
    echo [Error] .venv not found.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" "MyAssetHub_Root\app\main.py"

if %ERRORLEVEL% neq 0 (
    echo [Launcher] App exited with error code: %ERRORLEVEL%
    pause
)

endlocal
