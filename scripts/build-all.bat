@echo off
echo ========================================
echo Building Complete Application
echo ========================================
echo.

:: Step 1: Build Python backend exe
echo [1/4] Building Python backend...
cd backend
call build-backend.bat
if errorlevel 1 (
    echo Backend build failed!
    exit /b 1
)
cd ..
echo.

:: Step 2: Build React frontend
echo [2/4] Building React frontend...
call npm run build
if errorlevel 1 (
    echo Frontend build failed!
    exit /b 1
)
echo.

:: Step 3: Package Electron app
echo [3/4] Packaging Electron app...
call npm run electron:build
if errorlevel 1 (
    echo Electron packaging failed!
    exit /b 1
)
echo.

:: Step 4: Done
echo [4/4] Build complete!
echo.
echo ========================================
echo SUCCESS!
echo ========================================
echo.
echo Installer location: release\
dir release\*.exe
echo.
echo You can now run the installer to test the app.
echo.

pause
