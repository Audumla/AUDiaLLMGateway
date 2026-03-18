# Docker Deployment Guide

This project is optimized for Docker-first deployment using `docker-compose`.

## Core Images

- **Gateway**: `audia-llm-gateway` (LiteLLM + Config Generator)
- **Backend**: `audia-llm-gateway-backend` (Universal Provisioner for llama.cpp)

## Configuration

1.  **Environment**: Copy `config/env.example` to `.env` and configure your keys.
2.  **Models**: Ensure your models are stored in the `./models` directory (or update `MODEL_ROOT` in `.env`).

## Deployment Profiles

Choose the `docker-compose` file that matches your hardware:

### 1. Universal (Recommended)
Automatically detects NVIDIA/AMD hardware and provisions the correct runtimes on the first run.
```bash
docker-compose up -d
```

### 2. NVIDIA (CUDA)
Minimal configuration for NVIDIA-only systems.
```bash
docker-compose -f docker/examples/docker-compose.nvidia.yml up -d
```

### 3. AMD (ROCm)
Optimized for AMD systems using direct device mapping.
```bash
docker-compose -f docker/examples/docker-compose.amd.yml up -d
```

### 4. External Proxy
If you already run a reverse proxy (like Traefik or Nginx) on your host.
```bash
docker-compose -f docker/examples/docker-compose.external-proxy.yml up -d
```

## Management

Use the unified management script for common actions:

- **Start**: `./scripts/AUDiaLLMGateway.sh start`
- **Update**: `./scripts/AUDiaLLMGateway.sh update` (Pulls images and refreshes runtimes)
- **Status**: `./scripts/AUDiaLLMGateway.sh check status`
- **Health**: `./scripts/AUDiaLLMGateway.sh check health`

## Volume Management

The system uses a persistent volume called `backend-runtime` to store GPU libraries (~2GB). If you want to force a clean download of the `llama.cpp` binaries:
```bash
docker volume rm audiallmgateway_backend-runtime
docker-compose up -d
```
