@echo off
REM AUDia LLM Gateway - Auto-Start Setup Script
REM This script sets up Windows Task Scheduler for automatic startup
REM Requires Administrator privileges

echo.
echo ========================================
echo AUDia LLM Gateway - Auto-Start Setup
echo ========================================
echo.

REM Check if running as Administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: This script requires Administrator privileges!
    echo.
    echo To run as Administrator:
    echo   1. Right-click cmd.exe or PowerShell
    echo   2. Select "Run as Administrator"
    echo   3. Navigate to: h:\development\projects\AUDia\AUDiaLLMGateway\scripts
    echo   4. Run: setup-autostart.bat
    echo.
    pause
    exit /b 1
)

echo Administrator privileges confirmed.
echo.
echo This setup will:
echo   1. Create Windows Task Scheduler entry
echo   2. Configure auto-start at logon
echo   3. Enable highest privileges for Docker access
echo   4. Set retry policy for failures
echo.

REM Get script directory
for %%I in ("%~dp0.") do set SCRIPT_DIR=%%~fI
set PS_SCRIPT=%SCRIPT_DIR%\register-startup-task.ps1

echo Running PowerShell registration script...
echo Location: %PS_SCRIPT%
echo.

REM Run PowerShell with ExecutionPolicy bypass to allow script execution
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%"

if errorlevel 1 (
    echo.
    echo ERROR: Setup failed!
    echo.
    pause
    exit /b 1
)

echo.
echo Setup completed successfully!
echo.
pause
exit /b 0
