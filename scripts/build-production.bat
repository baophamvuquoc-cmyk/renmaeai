@echo off
echo ========================================
echo   Build Production App
echo ========================================
echo.
echo Step 1: Building Backend...
echo.
cd backend
call build-backend.bat
cd ..
echo.
echo Step 2: Building Frontend...
echo.
call npm run build
echo.
echo Step 3: Building Electron App...
echo.
call npm run electron:build
echo.
echo ========================================
echo   Build Complete!
echo ========================================
echo.
echo Your app is ready at: release/Auto Media Architecture Setup.exe
echo.
pause
