@echo off
echo ========================================
echo   RenmaeAI Studio (Dev Mode)
echo ========================================
echo.

REM Check if backend is already running on port 8000
netstat -ano | findstr :8000 >nul
if %errorlevel%==0 (
    echo [Backend] Already running on port 8000
) else (
    echo [1/2] Starting Backend Server...
    start "Backend Server" /min cmd /k "cd /d %~dp0backend && call %~dp0..\.venv\Scripts\activate.bat && python main.py"
    timeout /t 4 /nobreak >nul
)

REM Check if frontend is already running on port 5173
netstat -ano | findstr :5173 >nul
if %errorlevel%==0 (
    echo [Frontend] Already running on port 5173
) else (
    echo [2/2] Starting Frontend + Electron...
    start "Frontend App" cmd /k "cd /d %~dp0 && npm run dev"
    timeout /t 3 /nobreak >nul
)

echo.
echo ========================================
echo   App starting...
echo   - Backend: http://localhost:8000
echo   - Frontend: http://localhost:5173
echo ========================================
echo.
echo The Electron window will open automatically.
echo Close this window when done.
pause
