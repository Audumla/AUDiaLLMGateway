@echo off
REM AUDia LLM Gateway Auto-Start Script
REM This script starts Docker and the compose stack after Windows boots
REM Location: h:\development\projects\AUDia\AUDiaLLMGateway\scripts\startup-audia-gateway.bat

setlocal enabledelayedexpansion

REM Project directory (absolute path)
set PROJECT_DIR=h:\development\projects\AUDia\AUDiaLLMGateway

REM Log file for debugging
set LOG_FILE=%PROJECT_DIR%\logs\startup.log
if not exist "%PROJECT_DIR%\logs" mkdir "%PROJECT_DIR%\logs"

echo [%date% %time%] AUDia Gateway startup script started >> "%LOG_FILE%"

REM Wait for Docker daemon to be ready (max 60 seconds)
echo Waiting for Docker daemon...
echo [%date% %time%] Waiting for Docker daemon to start... >> "%LOG_FILE%"

timeout /t 5 /nobreak

set /a count=0
:docker_wait
tasklist /FI "IMAGENAME eq docker.exe" 2>nul | find /I /N "docker.exe">nul
if errorlevel 1 (
    if !count! lss 12 (
        set /a count+=1
        timeout /t 5 /nobreak
        goto docker_wait
    )
    echo Docker not running after 60 seconds. Please check Docker Desktop.
    echo [%date% %time%] ERROR: Docker daemon did not start within timeout >> "%LOG_FILE%"
    pause
    exit /b 1
)

echo Docker is ready. Starting AUDia LLM Gateway...
echo [%date% %time%] Docker daemon detected, starting compose services... >> "%LOG_FILE%"

cd /d "%PROJECT_DIR%"
if errorlevel 1 (
    echo Failed to change to project directory: %PROJECT_DIR%
    echo [%date% %time%] ERROR: Could not cd to %PROJECT_DIR% >> "%LOG_FILE%"
    pause
    exit /b 1
)

REM Start compose services
echo Starting Docker Compose services...
docker compose up -d >> "%LOG_FILE%" 2>&1

if errorlevel 1 (
    echo Failed to start Docker Compose. Check logs:
    echo [%date% %time%] ERROR: Docker compose up -d failed >> "%LOG_FILE%"
    docker compose logs --tail 50 >> "%LOG_FILE%" 2>&1
    pause
    exit /b 1
)

echo AUDia LLM Gateway services started successfully!
echo [%date% %time%] Services started successfully >> "%LOG_FILE%"
echo.
echo Status:
timeout /t 3 /nobreak
docker compose ps >> "%LOG_FILE%" 2>&1
docker compose ps

echo [%date% %time%] Startup script completed successfully >> "%LOG_FILE%"
exit /b 0
