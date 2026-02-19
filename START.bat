@echo off
setlocal enabledelayedexpansion

:: Get the project directory (this script lives in root)
set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

:: Verify project structure
if not exist "%PROJECT_DIR%\backend\main.py" (
    echo [ERROR] Cannot find backend\main.py
    echo Expected project at: %PROJECT_DIR%
    pause
    exit /b 1
)

if not exist "%PROJECT_DIR%\package.json" (
    echo [ERROR] Cannot find package.json
    echo Expected project at: %PROJECT_DIR%
    pause
    exit /b 1
)

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    pause
    exit /b 1
)

:: Check Node.js
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH
    pause
    exit /b 1
)

echo ========================================
echo   RenmaeAI Studio - Starting...
echo ========================================
echo.

:: Activate venv if available
set "VENV_ACTIVATE=%PROJECT_DIR%\.venv\Scripts\activate.bat"

:: Start Backend (hidden console)
echo [1/2] Starting Backend Server...
if exist "%VENV_ACTIVATE%" (
    start "" /min cmd /c "cd /d "%PROJECT_DIR%\backend" && call "%VENV_ACTIVATE%" && python -m uvicorn main:app --reload --port 8000"
) else (
    start "" /min cmd /c "cd /d "%PROJECT_DIR%\backend" && python -m uvicorn main:app --reload --port 8000"
)

:: Wait for backend to initialize
timeout /t 3 /nobreak >nul

:: Start Frontend + Electron (hidden console)
echo [2/2] Starting Frontend + Electron...
start "" /min cmd /c "cd /d "%PROJECT_DIR%" && npm run dev"

echo.
echo ========================================
echo   RenmaeAI Studio is starting!
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo ========================================
echo.
echo The Electron window will open shortly.
timeout /t 5 /nobreak >nul
exit
