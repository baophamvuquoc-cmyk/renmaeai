@echo off
title Auto Media Architecture - Launcher
color 0A

:menu
cls
echo ========================================
echo   AUTO MEDIA ARCHITECTURE
echo ========================================
echo.
echo Chon che do chay:
echo.
echo [1] Development Mode (Requires npm install)
echo     - Chay app voi hot-reload
echo     - 2 terminal windows (Backend + Frontend)
echo.
echo [2] Development Silent (RECOMMENDED)
echo     - Chay app development khong hien terminal
echo     - Chi hien 1 cua so app duy nhat
echo.
echo [3] Build Production App
echo     - Dong goi thanh file .exe
echo     - Toi uu nhat de phan phoi
echo.
echo [4] Run Production Build
echo     - Chay app da build (neu da build truoc do)
echo.
echo [0] Exit
echo.
echo ========================================
set /p choice="Nhap lua chon (0-4): "

if "%choice%"=="1" goto dev_normal
if "%choice%"=="2" goto dev_silent
if "%choice%"=="3" goto build_prod
if "%choice%"=="4" goto run_prod
if "%choice%"=="0" goto end
goto menu

:dev_normal
cls
echo Starting Development Mode...
start "Backend Server" cmd /k "cd /d %~dp0..\backend && python main.py"
timeout /t 3 /nobreak >nul
start "Frontend App" cmd /k "cd /d %~dp0.. && npm run dev"
echo.
echo Both servers are starting...
pause
goto menu

:dev_silent
cls
echo Starting Development Silent Mode...
if exist "%~dp0start-hidden.vbs" (
    start "" "%~dp0start-hidden.vbs"
    echo App is starting silently...
    timeout /t 3 /nobreak >nul
    exit
) else (
    echo ERROR: start-hidden.vbs not found!
    pause
    goto menu
)

:build_prod
cls
echo ========================================
echo   BUILDING PRODUCTION APP
echo ========================================
echo.
echo This will take several minutes...
echo.
pause
call "%~dp0build-production.bat"
echo.
echo Build complete! Check the release folder.
pause
goto menu

:run_prod
cls
echo Starting Production App...
if exist "%~dp0..\release\win-unpacked\Auto Media Architecture.exe" (
    start "" "%~dp0..\release\win-unpacked\Auto Media Architecture.exe"
    echo App started!
    timeout /t 2 /nobreak >nul
    exit
) else (
    echo ERROR: Production build not found!
    echo Please build the app first (Option 3)
    pause
    goto menu
)

:end
cls
echo Goodbye!
timeout /t 1 /nobreak >nul
exit
