@echo off
echo Building RenmaeAI-Launcher.exe...
echo.

set "CSC=C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"

if not exist "%CSC%" (
    echo [ERROR] C# compiler not found at: %CSC%
    echo Please install .NET Framework 4.0 or higher.
    pause
    exit /b 1
)

"%CSC%" /target:exe /out:"%~dp0RenmaeAI-Launcher.exe" "%~dp0RenmaeAI-Launcher.cs"

if %errorlevel%==0 (
    echo.
    echo [SUCCESS] Built RenmaeAI-Launcher.exe
    echo Location: %~dp0RenmaeAI-Launcher.exe
) else (
    echo.
    echo [ERROR] Build failed!
)
pause
