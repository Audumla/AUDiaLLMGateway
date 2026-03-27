# Docker Auto-Start Configuration

This document explains how to configure Docker and AUDia LLM Gateway to automatically start on Windows system reboot.

## Prerequisites

- Windows 11 Pro or Enterprise (Docker Desktop requires WSL 2)
- Docker Desktop installed
- Administrator access

## Configuration Steps

### 1. Enable Docker Desktop to Start on Boot

**Option A: Docker Desktop Settings (Recommended)**

1. Open **Docker Desktop**
2. Click **Settings** (gear icon)
3. Go to **General**
4. Check: **"Start Docker Desktop when you log in"**
5. Click **Apply & Restart**

**Option B: Windows Services (Alternative)**

1. Press `Win+R` and type `services.msc`
2. Find **"Docker Desktop Service"**
3. Right-click → **Properties**
4. Set **Startup type** to **Automatic**
5. Click **OK**

### 2. Create Startup Batch Script

Create a file: `C:\startup-audia-gateway.bat`

```batch
@echo off
REM AUDia LLM Gateway Auto-Start Script
REM This script starts Docker and the compose stack after Windows boots

setlocal enabledelayedexpansion

REM Project directory
set PROJECT_DIR=h:\development\projects\AUDia\AUDiaLLMGateway

REM Wait for Docker daemon to be ready (max 60 seconds)
echo Waiting for Docker daemon...
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
    echo Docker not running. Please check Docker Desktop.
    pause
    exit /b 1
)

echo Docker is ready. Starting AUDia LLM Gateway...
cd /d "%PROJECT_DIR%"

REM Start compose services
docker compose up -d

if errorlevel 1 (
    echo Failed to start Docker Compose. Check logs:
    docker compose logs --tail 50
    pause
    exit /b 1
)

echo AUDia LLM Gateway services started successfully!
echo.
echo Status:
timeout /t 3 /nobreak
docker compose ps

exit /b 0
```

### 3. Add to Windows Task Scheduler

1. Press `Win+R` and type `taskschd.msc`
2. Right-click **Task Scheduler Library** → **Create Task**

**General Tab:**
- Name: `AUDia LLM Gateway Startup`
- Check: **"Run with highest privileges"**
- Choose: **"Run whether user is logged in or not"** (optional)

**Triggers Tab:**
- Click **New**
- Begin the task: **"At log on"**
- Click **OK**

**Actions Tab:**
- Click **New**
- Action: **"Start a program"**
- Program/script: `C:\startup-audia-gateway.bat`
- Click **OK**

**Conditions Tab:**
- Uncheck: **"Start the task only if the computer is on AC power"** (optional)

**Settings Tab:**
- Check: **"Allow task to be run on demand"**
- Check: **"If the task fails, restart every: 1 minute"**
- Set retry count: **3**

Click **OK** and provide admin password when prompted.

### 4. Verify Configuration

Test the startup script manually:

```bash
# Run the batch file
C:\startup-audia-gateway.bat

# Check compose status
cd h:\development\projects\AUDia\AUDiaLLMGateway
docker compose ps
```

Expected output:
```
CONTAINER ID   IMAGE                                          STATUS              PORTS
...            example/audia-llm-gateway-orchestrator:latest  Up (healthy)        0.0.0.0:4000->4000/tcp
...            nginx:alpine                                   Up                  0.0.0.0:8080->8080/tcp
...            example/audia-llm-gateway-server:latest        Up
...            postgres:16-alpine                             Up (healthy)
```

### 5. Test Boot Scenario

To test without rebooting:

```bash
# Stop all services
docker compose down

# Wait a moment
timeout /t 5

# Manually run startup script
C:\startup-audia-gateway.bat

# Verify all services restarted
docker compose ps
docker compose logs --tail 20
```

## Troubleshooting

### Services don't restart automatically
- Check Task Scheduler: `taskschd.msc` → verify the task exists and is enabled
- Check Docker startup: Ensure Docker Desktop is in System Tray after boot
- Review logs: `docker compose logs --tail 100`

### Boot warnings about backend versions
- These are non-blocking warnings from the config loader
- The server will still start and function correctly
- To suppress: See `config/local/backend-support.override.yaml`

### Git clone failures during boot
- These occur during optional backend builds (now disabled)
- If you re-enable ROCm/Lemonade variants, ensure container has internet access
- Test connectivity: `docker compose exec llm-server-llamacpp curl https://github.com`

### Port conflicts
- If ports 8080, 4000 are in use, update `.env`:
  ```
  NGINX_PORT=8081
  GATEWAY_PORT=4001
  ```

## Environment Variables

Key variables in `.env`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `LLAMA_BACKEND` | `vulkan` | GPU backend (auto, cuda, rocm, vulkan, cpu) |
| `LLAMA_VERSION` | `latest` | llama.cpp version |
| `NGINX_PORT` | `8080` | Reverse proxy port |
| `GATEWAY_PORT` | `4000` | API gateway port |
| `MODEL_ROOT` | `./models` | Where models are stored |

## Monitoring

Check service health after boot:

```bash
# All services
docker compose ps

# Gateway liveliness
curl http://localhost:4000/health/liveliness

# llama-swap models
curl http://localhost:41080/models

# Chat completion test
curl -X POST http://localhost:41080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.5-27b-(96k-Q6)",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 20
  }'
```

## Performance Notes

- First boot after adding auto-start: Takes 60-90 seconds for all services
- Subsequent boots: 30-60 seconds (depends on model preloading)
- llama.cpp backend downloads/prepares on first run: additional 5-10 minutes
