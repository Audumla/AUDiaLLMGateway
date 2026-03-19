# Docker Deployment

Docker is the recommended deployment path for Linux home-lab and server environments.
It handles hardware detection and binary provisioning automatically, so you do not need
to manage llama.cpp builds or system library paths by hand.

For native (non-Docker) deployment on Windows, Linux, or macOS see [the runbook](runbook.md).

---

## Contents

- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Deployment Profiles](#deployment-profiles)
  - [Universal (auto-detect)](#1-universal-auto-detect)
  - [CPU Only](#2-cpu-only)
  - [NVIDIA / CUDA](#3-nvidia--cuda)
  - [AMD / ROCm](#4-amd--rocm)
  - [External Proxy](#5-external-proxy)
- [Port Reference](#port-reference)
- [Environment Variables](#environment-variables)
- [Model Files](#model-files)
- [Container Management](#container-management)
- [Updating](#updating)
- [Volumes and Persistence](#volumes-and-persistence)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

All profiles require:

- Docker Engine 24+ (with Compose v2 plugin — `docker compose` not `docker-compose`)
- A directory of GGUF model files

Hardware-specific extras:

| Hardware | Extra requirement |
| -------- | ----------------- |
| NVIDIA GPU | [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) |
| AMD GPU (ROCm) | ROCm 5.6+ drivers + `/dev/kfd` and `/dev/dri` available |
| CPU-only | Nothing extra |

---

## Initial Setup

### 1. Copy the environment file

```bash
cp config/env.example .env
```

Edit `.env` and set at minimum:

```dotenv
# API authentication key — change this before exposing the gateway on a network
LITELLM_MASTER_KEY=sk-change-me

# HuggingFace token (only needed if downloading gated models)
HUGGING_FACE_HUB_TOKEN=hf_your_token_here

# Path to your model directory (defaults to ./models)
MODEL_ROOT=./models
```

### 2. Place your model files

```text
models/
  Qwen3.5-27B/
    Qwen3.5-27B-Q6_K.gguf
  Ministral-3-3B/
    Ministral-3-3B-Instruct-2512-Q4_K_M.gguf
    mmproj-Ministral-3-3B-Instruct-2512-F16.gguf
```

The path structure must match the `model_file` entries in
`config/project/models.base.yaml`. Forward slashes are required — no Windows-style
backslashes even on Windows hosts.

### 3. Generate configs

The gateway container runs the config generator on startup, so no manual generation
step is needed. If you want to pre-generate and inspect:

```bash
./scripts/AUDiaLLMGateway.sh generate
```

---

## Deployment Profiles

Choose the compose file that matches your hardware. Each profile is self-contained.
vLLM is available in all profiles as an optional add-on started with `--profile vllm`.

### 1. Universal (auto-detect)

Automatically detects NVIDIA or AMD hardware and provisions the correct runtime on
first start. Best choice for most home-lab deployments.

```bash
# llama.cpp only (auto-detect GPU)
docker compose up -d

# With vLLM added (requires NVIDIA GPU)
docker compose --profile vllm up -d
```

This uses the root `docker-compose.yml`. On first start, the backend container
downloads and caches the appropriate llama.cpp binary. Subsequent starts use the
cached `backend-runtime` volume.

Full compose definition: [`docker-compose.yml`](../docker-compose.yml)

---

### 2. CPU Only

For development, testing, or systems without a GPU.

```bash
docker compose -f docker/examples/docker-compose.cpu.yml up -d
```

Compose file: [`docker/examples/docker-compose.cpu.yml`](../docker/examples/docker-compose.cpu.yml)

---

### 3. NVIDIA / CUDA

Minimal profile for systems with only NVIDIA GPUs.

**Prerequisite:** NVIDIA Container Toolkit installed and Docker runtime configured.

```bash
# Verify NVIDIA container toolkit is working
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi

# Start the NVIDIA-optimised stack
docker compose -f docker/examples/docker-compose.nvidia.yml up -d
```

Compose file: [`docker/examples/docker-compose.nvidia.yml`](../docker/examples/docker-compose.nvidia.yml)

```yaml
# docker/examples/docker-compose.nvidia.yml
services:
  gateway:
    image: example/audia-llm-gateway-orchestrator:latest
    container_name: audia-gateway
    ports:
      - "4000:4000"
    environment:
      - LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY}
    volumes:
      - ./config:/app/config
    depends_on:
      - backend-swappable

  backend-swappable:
    image: example/audia-llm-gateway-server:latest
    container_name: audia-llama-cpp
    environment:
      - LLAMA_BACKEND=cuda
    volumes:
      - ./models:/app/models:ro
      - ./config/generated/llama-swap:/app/config:ro
      - backend-runtime:/app/runtime
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    restart: unless-stopped

volumes:
  backend-runtime:
```

---

### 4. AMD / ROCm

Profile for AMD GPUs using ROCm or Vulkan passthrough.

**Prerequisite:** ROCm 5.6+ drivers. Verify with:

```bash
rocm-smi   # or: ls /dev/kfd
```

```bash
docker compose -f docker/examples/docker-compose.amd.yml up -d
```

Compose file: [`docker/examples/docker-compose.amd.yml`](../docker/examples/docker-compose.amd.yml)

```yaml
# docker/examples/docker-compose.amd.yml
services:
  gateway:
    image: example/audia-llm-gateway-orchestrator:latest
    container_name: audia-gateway
    ports:
      - "4000:4000"
    environment:
      - LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY}
    volumes:
      - ./config:/app/config
    depends_on:
      - backend-swappable

  backend-swappable:
    image: example/audia-llm-gateway-server:latest
    container_name: audia-llama-cpp
    environment:
      - LLAMA_BACKEND=rocm
    volumes:
      - ./models:/app/models:ro
      - ./config/generated/llama-swap:/app/config:ro
      - backend-runtime:/app/runtime
    devices:
      - /dev/kfd:/dev/kfd
      - /dev/dri:/dev/dri
    group_add:
      - video
      - render
    restart: unless-stopped

volumes:
  backend-runtime:
```

AMD device passthrough notes:

- `/dev/kfd` — ROCm compute interface
- `/dev/dri` — Vulkan and direct rendering
- `group_add: [video, render]` — required for permission to access those devices

---

### 5. External Proxy

Use this when you already run a reverse proxy (Traefik, nginx, Caddy) on the host.
The gateway container joins your existing proxy network instead of publishing a port.

```bash
docker compose -f docker/examples/docker-compose.external-proxy.yml up -d
```

Compose file: [`docker/examples/docker-compose.external-proxy.yml`](../docker/examples/docker-compose.external-proxy.yml)

```yaml
# docker/examples/docker-compose.external-proxy.yml
services:
  gateway:
    image: example/audia-llm-gateway-orchestrator:latest
    container_name: audia-gateway
    # No port mapping — proxied via the web-proxy network
    environment:
      - LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY}
    volumes:
      - ./config:/app/config
    depends_on:
      - backend-swappable
    networks:
      - web-proxy
      - internal

  backend-swappable:
    image: example/audia-llm-gateway-server:latest
    container_name: audia-llama-cpp
    environment:
      - LLAMA_BACKEND=auto
    volumes:
      - ./models:/app/models:ro
      - ./config/generated/llama-swap:/app/config:ro
      - backend-runtime:/app/runtime
    networks:
      - internal
    restart: unless-stopped

networks:
  web-proxy:
    external: true   # must already exist on the host
  internal:
    driver: bridge

volumes:
  backend-runtime:
```

Point your external proxy to `audia-gateway:4000` on the `web-proxy` network.
Add a label for Traefik, or an upstream block in nginx as appropriate.

---

## Port Reference

| Service | Internal port | Default published port | Config location |
| ------- | ------------ | ---------------------- | --------------- |
| LiteLLM API gateway | 4000 | 4000 | `network.litellm.port` in `stack.base.yaml` |
| llama-swap backend | 41080 | not published | `network.llama_swap.port` |
| vLLM backend | 8000 | 41090 | `VLLM_PORT` in `.env` |
| nginx reverse proxy | 8080 | 8080 | `network.nginx.port` |

Ports are configured centrally in `config/project/stack.base.yaml` under `network`.
Override machine-specific values in `config/local/stack.override.yaml`:

```yaml
network:
  litellm:
    port: 5000   # change published port
```

---

## Environment Variables

All variables read from `.env` at compose start time.

| Variable | Required | Default | Description |
| -------- | -------- | ------- | ----------- |
| `LITELLM_MASTER_KEY` | Yes | — | API key for LiteLLM. Set a strong value before exposing externally. |
| `HUGGING_FACE_HUB_TOKEN` | No | — | HuggingFace token for gated model downloads. |
| `MODEL_ROOT` | No | `./models` | Host path to model directory. Mounted read-only into the backend. |
| `VLLM_MODEL` | No | `Qwen/Qwen2.5-0.5B-Instruct` | Model served by the vLLM backend (if used). |
| `VLLM_PORT` | No | `41090` | Host port for the vLLM backend. |
| `VLLM_GPU_MEM` | No | `0.85` | GPU memory utilization fraction for vLLM. |
| `LLAMA_BACKEND` | No | `auto` | Override llama.cpp backend detection: `auto`, `cuda`, `rocm`, `vulkan`, `cpu`. |
| `LLAMA_VERSION` | No | `latest` | llama.cpp release tag to provision (e.g. `b4632`). |
| `DOCKERHUB_USERNAME` | No | `example` | Override image registry username for self-hosted images. |

---

## Model Files

Model files live outside containers and are bind-mounted read-only.
The directory structure must match the `model_file` paths in the model catalog:

```text
# config/project/models.base.yaml snippet:
#   model_file: Qwen3.5-27B/Qwen3.5-27B-Q6_K.gguf

models/
  Qwen3.5-27B/
    Qwen3.5-27B-Q6_K.gguf
```

To add a model: place the file in `models/`, update `config/local/models.override.yaml`,
and restart the backend container:

```bash
docker compose restart backend-swappable
```

The gateway container will re-generate configs on next start.

---

## Container Management

Standard Docker Compose commands work with all profiles.

```bash
# Start (detached)
docker compose up -d

# View logs (all containers)
docker compose logs -f

# View logs for a specific container
docker compose logs -f audia-gateway

# Stop and remove containers (volumes preserved)
docker compose down

# Restart a single container
docker compose restart audia-gateway
docker compose restart backend-swappable

# Check container status
docker compose ps
```

Using the unified management script (wraps Compose):

```bash
./scripts/AUDiaLLMGateway.sh start
./scripts/AUDiaLLMGateway.sh stop
./scripts/AUDiaLLMGateway.sh check health
./scripts/AUDiaLLMGateway.sh check status
```

---

## Updating

Pull the latest images and restart:

```bash
docker compose pull
docker compose up -d
```

Or via the management script:

```bash
./scripts/AUDiaLLMGateway.sh update
```

The update preserves:

- `config/local/` — your local overrides
- `models/` — your model files
- `backend-runtime` volume — cached llama.cpp binaries
- `.env` — your environment file

---

## Volumes and Persistence

| Volume / path | Contents | Managed by |
| ------------- | -------- | ---------- |
| `backend-runtime` (Docker volume) | Provisioned llama.cpp binaries (~500 MB) | Installer on first start |
| `./models` (bind mount) | GGUF model files | You |
| `./config/local/` (bind mount) | Machine-specific overrides | You |
| `./config/generated/` (bind mount) | Generated configs | Gateway container on start |

To force a full re-provision of the backend runtime (e.g. after a llama.cpp version
change):

```bash
docker volume rm example_backend-runtime
docker compose up -d
```

---

## Troubleshooting

### Gateway container exits immediately

Check the logs:

```bash
docker compose logs audia-gateway
```

Common causes: missing `LITELLM_MASTER_KEY`, malformed `config/generated/litellm/litellm.config.yaml`.

### Backend container exits or shows GPU errors

```bash
docker compose logs backend-swappable
```

- NVIDIA: confirm Container Toolkit is installed (`docker run --gpus all nvidia/cuda:... nvidia-smi`)
- AMD: confirm `/dev/kfd` exists and the user has `render` and `video` group membership

### apt-get hangs during image build

Docker's bridge network has unreliable DNS on some Linux hosts. Build with host networking:

```bash
docker build --network=host -f docker/Dockerfile.gateway -t audia-llm-gateway .
```

### Models not found by llama-swap

Verify forward slashes in the model path. The generated llama-swap config must use
Linux paths. Check:

```bash
cat config/generated/llama-swap/llama-swap.generated.yaml | grep -i model-path
```

If you see backslashes, re-run generate:

```bash
./scripts/AUDiaLLMGateway.sh generate
docker compose restart backend-swappable
```

### Port already in use

Edit `config/local/stack.override.yaml` to change ports, then regenerate and restart:

```bash
./scripts/AUDiaLLMGateway.sh generate
docker compose up -d
```

### Auth errors (401) when calling the API

Ensure your client includes the API key:

```bash
curl http://localhost:4000/v1/models \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}"
```

The `LITELLM_MASTER_KEY` in `.env` must match what your client sends.
