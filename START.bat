@echo off
setlocal enabledelayedexpansion
title RenmaeAI Studio

:: Get the project directory (this script lives in root)
set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

:: Verify project structure
if not exist "%PROJECT_DIR%\backend\main.py" (
    echo [ERROR] Cannot find backend\main.py
    pause
    exit /b 1
)

echo.
echo   ========================================
echo     RenmaeAI Studio is starting...
echo   ========================================
echo.

:: Activate venv if available
set "VENV_ACTIVATE=%PROJECT_DIR%\.venv\Scripts\activate.bat"

:: Start Backend (completely hidden - no window)
echo   [1/2] Starting Backend Server...
if exist "%VENV_ACTIVATE%" (
    start "" /min cmd /c "cd /d "%PROJECT_DIR%\backend" && call "%VENV_ACTIVATE%" && python -m uvicorn main:app --reload --port 8000"
) else (
    start "" /min cmd /c "cd /d "%PROJECT_DIR%\backend" && python -m uvicorn main:app --reload --port 8000"
)

:: Wait for backend to initialize
timeout /t 3 /nobreak >nul

:: Start Frontend + Electron (hidden)
echo   [2/2] Starting Electron app...
start "" /min cmd /c "cd /d "%PROJECT_DIR%" && npm run dev"

:: Wait for Vite to start
timeout /t 3 /nobreak >nul

:: Open browser automatically
echo.
echo   The app window will open shortly...
echo.
echo   ========================================
echo     RenmaeAI Studio is ready!
echo   ========================================
echo.
echo   You can close this window.
echo   Backend and Frontend are running in background.
echo.
pause
