@echo off
echo ========================================
echo Building Backend Executable
echo ========================================

:: Activate virtual environment if exists
if exist ..\.venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call ..\.venv\Scripts\activate.bat
) else (
    echo Warning: Virtual environment not found, using global Python
)

:: Install PyInstaller if not already installed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

:: Clean previous build
if exist dist (
    echo Cleaning previous build...
    rmdir /s /q dist
)
if exist build (
    rmdir /s /q build
)

:: Build the executable
echo Building backend.exe...
pyinstaller backend.spec

:: Check if build was successful
if exist dist\backend.exe (
    echo.
    echo ========================================
    echo Build successful!
    echo Executable: backend\dist\backend.exe
    echo ========================================
) else (
    echo.
    echo ========================================
    echo Build FAILED!
    echo ========================================
    exit /b 1
)

pause
