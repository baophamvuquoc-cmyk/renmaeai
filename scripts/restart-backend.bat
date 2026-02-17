@echo off
echo ========================================
echo   Restarting Backend Server
echo ========================================
echo.

REM Kill any process running on port 8000
echo [1/3] Stopping backend server on port 8000...
FOR /F "tokens=5" %%P IN ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') DO (
    echo Killing process %%P
    taskkill /PID %%P /F >nul 2>&1
)
FOR /F "tokens=5" %%P IN ('netstat -ano ^| findstr :8000 ^| findstr ESTABLISHED') DO (
    taskkill /PID %%P /F >nul 2>&1
)

timeout /t 2 /nobreak >nul

REM Clear Python cache
echo [2/3] Clearing Python cache...
cd backend
for /d /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
cd ..

REM Start backend using venv Python
echo [3/3] Starting backend server...
start "Backend Server" cmd /k "cd backend && ..\\.venv\\Scripts\\python.exe main.py"

timeout /t 5 /nobreak >nul

echo.
echo ========================================
echo   Backend restarted successfully!
echo ========================================
echo.
echo Testing connection...
curl -s http://localhost:8000/health 2>nul
echo.
pause
