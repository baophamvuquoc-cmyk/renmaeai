@echo off
setlocal enabledelayedexpansion
title RenmaeAI Studio - Setup
color 0A

echo.
echo ========================================
echo   RenmaeAI Studio - One-Click Setup
echo ========================================
echo.

:: ═══ CHECK PREREQUISITES ═══

echo [*] Checking prerequisites...
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Python is NOT installed!
    echo     Download: https://www.python.org/downloads/
    echo     Make sure to check "Add Python to PATH" during install.
    echo.
    set "HAS_ERROR=1"
) else (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do (
        echo [OK] Python %%v found
    )
)

:: Check Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Node.js is NOT installed!
    echo     Download: https://nodejs.org/ ^(LTS version recommended^)
    echo.
    set "HAS_ERROR=1"
) else (
    for /f "tokens=1" %%v in ('node --version 2^>^&1') do (
        echo [OK] Node.js %%v found
    )
)

:: Check FFmpeg (optional but recommended)
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] FFmpeg not found ^(optional - needed for video rendering^)
    echo     Download: https://ffmpeg.org/download.html
) else (
    echo [OK] FFmpeg found
)

echo.

if defined HAS_ERROR (
    echo ========================================
    echo [ERROR] Missing prerequisites! Install them first.
    echo ========================================
    pause
    exit /b 1
)

:: ═══ GET PROJECT DIRECTORY ═══
set "PROJECT_DIR=%~dp0.."
pushd "%PROJECT_DIR%"
set "PROJECT_DIR=%cd%"
popd

echo Project directory: %PROJECT_DIR%
echo.

:: ═══ STEP 1: CREATE PYTHON VENV ═══

echo [1/4] Setting up Python virtual environment...
if not exist "%PROJECT_DIR%\.venv" (
    python -m venv "%PROJECT_DIR%\.venv"
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo       Created .venv successfully
) else (
    echo       .venv already exists, skipping
)

:: ═══ STEP 2: INSTALL PYTHON DEPENDENCIES ═══

echo [2/4] Installing Python dependencies...
call "%PROJECT_DIR%\.venv\Scripts\activate.bat"
pip install -r "%PROJECT_DIR%\backend\requirements.txt" --quiet
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Python dependencies
    pause
    exit /b 1
)
echo       Python dependencies installed!
echo.

:: ═══ STEP 3: INSTALL NODE DEPENDENCIES ═══

echo [3/4] Installing Node.js dependencies...
cd /d "%PROJECT_DIR%"
call npm install --silent
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Node.js dependencies
    pause
    exit /b 1
)
echo       Node.js dependencies installed!
echo.

:: ═══ STEP 4: SETUP ENV FILE ═══

echo [4/4] Setting up environment...
if not exist "%PROJECT_DIR%\backend\.env" (
    if exist "%PROJECT_DIR%\.env.example" (
        copy "%PROJECT_DIR%\.env.example" "%PROJECT_DIR%\backend\.env" >nul
        echo       Created backend\.env from .env.example
        echo       [!] Edit backend\.env to add your API keys!
    )
) else (
    echo       backend\.env already exists, skipping
)
echo.

:: ═══ BUILD LAUNCHER EXE ═══

echo [*] Building launcher...
set "CSC=C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if exist "%CSC%" (
    if exist "%PROJECT_DIR%\scripts\RenmaeAI-Launcher.cs" (
        "%CSC%" /nologo /target:exe /out:"%PROJECT_DIR%\scripts\RenmaeAI-Launcher.exe" "%PROJECT_DIR%\scripts\RenmaeAI-Launcher.cs" >nul 2>&1
        if exist "%PROJECT_DIR%\scripts\RenmaeAI-Launcher.exe" (
            echo       Built RenmaeAI-Launcher.exe
        )
    )
)
echo.

:: ═══ DONE ═══

echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo Next steps:
echo.
echo   1. Add your API keys to backend\.env:
echo      - GEMINI_API_KEY   (https://makersuite.google.com/app/apikey)
echo      - PEXELS_API_KEY   (https://www.pexels.com/api/)
echo      - PIXABAY_API_KEY  (https://pixabay.com/api/docs/)
echo.
echo   2. Launch the app:
echo      - Double-click: scripts\RenmaeAI-Launcher.exe
echo      - Or run:       scripts\launch-renmaeai.bat
echo      - Or manually:  npm run dev:web
echo.
echo ========================================
pause
