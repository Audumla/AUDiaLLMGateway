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
  - [AMD / Vulkan Or ROCm](#4-amd--vulkan-or-rocm)
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

### 1. Review the default API key

Edit `.env` at the repo root (copy from `config/env.example` if it doesn't exist):

```bash
cp config/env.example .env
```

Set at minimum:

```dotenv
# API authentication key — change this before exposing the gateway on a network
LITELLM_MASTER_KEY=sk-change-me

# HuggingFace token (only needed if downloading gated models)
HUGGING_FACE_HUB_TOKEN=hf_your_token_here

# LiteLLM UI/auth database
POSTGRES_USER=audia
POSTGRES_PASSWORD=audia-dev-password
POSTGRES_DB=litellm
POSTGRES_DATA_ROOT=./config/data/postgres
DATABASE_URL=postgresql://audia:audia-dev-password@llm-db-postgres:5432/litellm

# Path to your model directory (defaults to ./models)
MODEL_ROOT=./models
MODEL_HF_ROOT=./models-hf
BACKEND_RUNTIME_ROOT=./config/data/backend-runtime

# Optional vLLM backend
AUDIA_ENABLE_VLLM=false
```

If you do not change it, the Docker install defaults LiteLLM to:

- Username: `admin`
- Password: `sk-local-dev`

That password is the LiteLLM `LITELLM_MASTER_KEY`. Change it before exposing the gateway on a network.
The default root compose also starts PostgreSQL and wires `DATABASE_URL`, so LiteLLM UI login works against a real database by default.

If you want guided first-time setup on Linux, run:

```bash
./scripts/docker-setup.sh
```

That helper:

- detects whether the host looks like NVIDIA, AMD, Vulkan-only, or CPU-only
- prompts for the main Docker settings
- writes `.env`
- creates visible host directories for `models`, `models-hf`, `BACKEND_RUNTIME_ROOT`, and PostgreSQL data

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
`config/local/models.override.yaml`. Forward slashes are required — no Windows-style
backslashes even on Windows hosts.

### 3. Start the stack

```bash
docker compose up -d
```

The root [`docker-compose.yml`](../docker-compose.yml) is image-only and safe to
copy onto a clean host with just `.env`, `config/`, and `models/`. It does not
require a git checkout or local Docker build context.

On first start the gateway container automatically seeds `config/local/` with
commented template files if they do not already exist:

| File | Purpose |
| ---- | ------- |
| `config/local/env` | Service-level env overrides (hint file — Docker reads `.env` at root) |
| `config/local/stack.override.yaml` | Port, host, and service overrides |
| `config/local/models.override.yaml` | Add or override model definitions |

Then it generates `config/generated/` from `config/project/` + `config/local/` and
starts LiteLLM. If `LITELLM_MASTER_KEY` is not already present in the container
environment, the gateway reuses the seeded value from `config/local/env` on first
run. Subsequent restarts skip the seed step — your edits are never overwritten.

To customise after first start, edit any file under `config/local/` and restart the
gateway:

```bash
docker compose restart llm-gateway
```

To force regeneration without restarting the full stack:

```bash
./scripts/AUDiaLLMGateway.sh generate
```

---

## Deployment Profiles

Choose the compose file that matches your hardware. Each profile is self-contained.
vLLM is available as an optional add-on, but the validated AMD path is the AMD
compose profile rather than the root compose file.

### 1. Universal (auto-detect)

Automatically detects NVIDIA or AMD hardware and provisions the correct runtime on
first start. Best choice for most home-lab deployments.

```bash
# llama.cpp only (auto-detect GPU)
docker compose up -d

# With vLLM added (root compose / NVIDIA-oriented path)
AUDIA_ENABLE_VLLM=true docker compose --profile vllm up -d
```

This uses the root `docker-compose.yml`. On first start, the backend container
downloads and caches the appropriate llama.cpp binary. Subsequent starts reuse the
host-mounted runtime base directory at `BACKEND_RUNTIME_ROOT` (default:
`./config/data/backend-runtime`), with one sibling directory per backend such as
`vulkan/`, `rocm/`, `cuda/`, or `cpu/`.

Full compose definition: [`docker-compose.yml`](../docker-compose.yml)

---

### 2. CPU Only

For development, testing, or systems without a GPU.

```bash
docker compose --project-directory . -f docker/examples/docker-compose.cpu.yml up -d
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
docker compose --project-directory . -f docker/examples/docker-compose.nvidia.yml up -d
```

Compose file: [`docker/examples/docker-compose.nvidia.yml`](../docker/examples/docker-compose.nvidia.yml)

```yaml
# docker/examples/docker-compose.nvidia.yml
services:
  llm-gateway:
    image: example/audia-llm-gateway-orchestrator:latest
    container_name: audia-gateway
    ports:
      - "4000:4000"
    environment:
      - LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY}
    volumes:
      - ./config:/app/config
    depends_on:
      - llm-server-llamacpp

  llm-server-llamacpp:
    image: example/audia-llm-gateway-server:latest
    container_name: audia-llama-cpp
    environment:
      - LLAMA_BACKEND=cuda
    volumes:
      - ./models:/app/models:ro
      - ./config/generated/llama-swap:/app/config:ro
      - ${BACKEND_RUNTIME_ROOT:-./config/data/backend-runtime}:/app/runtime-root
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    restart: unless-stopped

```

---

### 4. AMD / Vulkan Or ROCm

Profile for AMD GPUs where `llama.cpp` may run with both Vulkan and ROCm at the
same time. Use `LLAMA_BACKEND=auto` so the backend runtime provisions both
implementations, then route individual models with explicit
`executable_macro: llama-server-vulkan` or `executable_macro: llama-server-rocm`
in `config/local/models.override.yaml`. The validated `vLLM` path on AMD remains
the official `vllm/vllm-openai-rocm:latest` image in that same compose profile.

**Prerequisite:** ROCm 5.6+ drivers. Verify with:

```bash
rocm-smi   # or: ls /dev/kfd
```

```bash
# Provision both Vulkan and ROCm runtimes
LLAMA_BACKEND=auto docker compose --project-directory . -f docker/examples/docker-compose.amd.yml up -d
```

Compose file: [`docker/examples/docker-compose.amd.yml`](../docker/examples/docker-compose.amd.yml)

```yaml
# docker/examples/docker-compose.amd.yml
services:
  llm-gateway:
    image: example/audia-llm-gateway-orchestrator:latest
    container_name: audia-gateway
    ports:
      - "4000:4000"
    environment:
      - LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY}
    volumes:
      - ./config:/app/config
    depends_on:
      - llm-server-llamacpp

  llm-server-llamacpp:
    image: example/audia-llm-gateway-server:latest
    container_name: audia-llama-cpp
    environment:
      - LLAMA_BACKEND=${LLAMA_BACKEND:-auto}
      - VK_ICD_FILENAMES=${VK_ICD_FILENAMES:-/usr/share/vulkan/icd.d/radeon_icd.json}
    volumes:
      - ./models:/app/models:ro
      - ./config/generated/llama-swap:/app/config:ro
      - ${BACKEND_RUNTIME_ROOT:-./config/data/backend-runtime}:/app/runtime-root
    devices:
      - /dev/kfd:/dev/kfd
      - /dev/dri:/dev/dri
    group_add:
      - video
      - render
    restart: unless-stopped

```

Example mixed-backend catalog entries:

```yaml
deployments:
  llamacpp_vulkan:
    framework: llama_cpp
    transport: llama-swap
    executable_macro: llama-server-vulkan
    llama_swap_model: qwen3-5-4b-ud-q5-k-xl-vision

  llamacpp_rocm:
    framework: llama_cpp
    transport: llama-swap
    executable_macro: llama-server-rocm
    llama_swap_model: tiny-qwen25-test
```

The optional `vLLM` profile in this same AMD compose stays ROCm-only:

```bash
LLAMA_BACKEND=auto AUDIA_ENABLE_VLLM=true docker compose --project-directory . -f docker/examples/docker-compose.amd.yml --profile vllm up -d
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
docker compose --project-directory . -f docker/examples/docker-compose.external-proxy.yml up -d
```

Compose file: [`docker/examples/docker-compose.external-proxy.yml`](../docker/examples/docker-compose.external-proxy.yml)

```yaml
# docker/examples/docker-compose.external-proxy.yml
services:
  llm-gateway:
    image: example/audia-llm-gateway-orchestrator:latest
    container_name: audia-gateway
    # No port mapping — proxied via the web-proxy network
    environment:
      - LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY}
    volumes:
      - ./config:/app/config
    depends_on:
      - llm-server-llamacpp
    networks:
      - web-proxy
      - internal

  llm-server-llamacpp:
    image: example/audia-llm-gateway-server:latest
    container_name: audia-llama-cpp
    environment:
      - LLAMA_BACKEND=auto
    volumes:
      - ./models:/app/models:ro
      - ./config/generated/llama-swap:/app/config:ro
      - ${BACKEND_RUNTIME_ROOT:-./config/data/backend-runtime}:/app/runtime-root
    networks:
      - internal
    restart: unless-stopped

networks:
  web-proxy:
    external: true   # must already exist on the host
  internal:
    driver: bridge

```

Point your external proxy to `llm-gateway:4000` on the `web-proxy` network.
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
| `LITELLM_MASTER_KEY` | No | `sk-local-dev` | API key for LiteLLM Admin UI and gateway auth. Set a strong value before exposing externally. |
| `HUGGING_FACE_HUB_TOKEN` | No | — | HuggingFace token for gated model downloads. |
| `POSTGRES_USER` | No | `audia` | PostgreSQL username for the LiteLLM metadata database. |
| `POSTGRES_PASSWORD` | No | `audia-dev-password` | PostgreSQL password for the LiteLLM metadata database. |
| `POSTGRES_DB` | No | `litellm` | PostgreSQL database name for LiteLLM metadata. |
| `POSTGRES_DATA_ROOT` | No | `./config/data/postgres` | Host path for PostgreSQL data files. |
| `DATABASE_URL` | No | `postgresql://audia:audia-dev-password@llm-db-postgres:5432/litellm` | LiteLLM database connection string used by the Admin UI/auth path. |
| `DATABASE_WAIT_SECONDS` | No | `120` | Seconds the gateway entrypoint waits for the database to become reachable before starting LiteLLM. |
| `DATABASE_WAIT_INTERVAL_SECONDS` | No | `2` | Seconds between database reachability probes during gateway startup. |
| `MODEL_ROOT` | No | `./models` | Host path to model directory. Mounted read-only into the backend. |
| `MODEL_HF_ROOT` | No | `./models-hf` | Host path for Hugging Face cache and raw tensor weights used by vLLM. |
| `BACKEND_RUNTIME_ROOT` | No | `./config/data/backend-runtime` | Host path base for the provisioned `llama.cpp` runtimes. Each backend is stored in its own subdirectory such as `cpu/`, `rocm/`, `vulkan/`, or `cuda/`. |
| `AUDIA_ENABLE_VLLM` | No | `false` | Enables vLLM-backed LiteLLM routes and watcher-managed vLLM restarts. Requires `--profile vllm`. |
| `GATEWAY_PORT` | No | `4000` | Host port published for the LiteLLM gateway. |
| `NGINX_PORT` | No | `8080` | Host port published for the nginx reverse proxy. |
| `VLLM_MODEL` | No | `Qwen/Qwen2.5-0.5B-Instruct` | Model served by the vLLM backend (if used). |
| `VLLM_BACKEND` | No | `rocm` | Selects which `vllm-<backend>` block to use from `gpu_profiles` (for example `vllm-rocm`). |
| `VLLM_PORT` | No | `41090` | Host port for the vLLM backend. |
| `VLLM_GPU_MEM` | No | `1.0` | GPU memory utilization fraction for vLLM. |
| `VLLM_MAX_LEN` | No | `4096` | Maximum context length for the vLLM backend. |
| `VLLM_TENSOR_PARALLEL_SIZE` | No | `1` | Tensor parallel size passed to vLLM (`--tensor-parallel-size`). |
| `VLLM_PIPELINE_PARALLEL_SIZE` | No | `1` | Pipeline parallel size passed to vLLM (`--pipeline-parallel-size`). |
| `VLLM_VISIBLE_DEVICES` | No | — | Optional `HIP_VISIBLE_DEVICES` override when set via generated vLLM startup config. |
| `VLLM_IMAGE` | No | `example/audia-llm-gateway-vllm:latest` | Override the vLLM image. Use `vllm/vllm-openai-rocm:latest` with the AMD compose profile. |
| `VLLM_MOCK_MODE` | No | `false` | Runs the mounted mock vLLM server instead of the real `vllm` process. Intended for Docker validation only. |
| `LLAMA_BACKEND` | No | `auto` | Override llama.cpp backend detection: `auto`, `cuda`, `rocm`, `vulkan`, `cpu`. |
| `LLAMA_VERSION` | No | `latest` | llama.cpp release tag to provision (e.g. `b4632`). |
| `DOCKERHUB_USERNAME` | No | `example` | Override image registry username for self-hosted images. |

---

## Model Files

Model files live outside containers and are bind-mounted read-only.
The directory structure must match the `model_file` paths in the model catalog:

```text
# config/local/models.override.yaml snippet:
#   model_file: Qwen3.5-27B/Qwen3.5-27B-Q6_K.gguf

models/
  Qwen3.5-27B/
    Qwen3.5-27B-Q6_K.gguf
```

To add a model: place the file in `models/`, update `config/local/models.override.yaml`,
and restart the backend container:

```bash
docker compose restart llm-server-llamacpp
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
docker compose logs -f llm-gateway

# Stop and remove containers (volumes preserved)
docker compose down

# Restart a single container
docker compose restart llm-gateway
docker compose restart llm-server-llamacpp

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
- `config/data/backend-runtime/<backend>/` — cached llama.cpp binaries and backend plugins
- `config/data/postgres/` — LiteLLM metadata database
- `.env` — your environment file

On a clean remote host you only need:

- `docker-compose.yml`
- `.env`
- `config/`
- `models/`

## Building Images Locally

The Docker Hub publish pipeline now uses reusable base images so final image builds
and pushes only need to copy the repo code layered on top.

Build the base images first:

```bash
docker build -f docker/Dockerfile.gateway-base -t audia-gateway-base:local .
docker build -f docker/Dockerfile.backend-base -t audia-backend-base:local .
docker build -f docker/Dockerfile.vllm -t audia-vllm:local .
```

Then build the final images against those local base tags:

```bash
docker build -f docker/Dockerfile.gateway \
  --build-arg GATEWAY_BASE_IMAGE=audia-gateway-base:local \
  -t audia-llm-gateway .

docker build -f docker/Dockerfile.unified-backend \
  --build-arg BACKEND_BASE_IMAGE=audia-backend-base:local \
  -t audia-llm-backend .
```

For local source-driven iteration with Compose, layer the dev override on top of
the deployment compose:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

--- 

## Volumes and Persistence

| Volume / path | Contents | Managed by |
| ------------- | -------- | ---------- |
| `./config/data/backend-runtime/<backend>` (under bind-mounted base) | Provisioned llama.cpp binaries and backend plugins (~500 MB) | Installer on first start |
| `./config/data/postgres` (bind mount) | PostgreSQL data for LiteLLM UI/auth metadata | PostgreSQL container |
| `./models` (bind mount) | GGUF model files | You |
| `./models-hf` (bind mount) | Hugging Face cache and raw tensor weights for vLLM | You / vLLM |
| `./config/local/` (bind mount) | Machine-specific overrides | You |
| `./config/generated/` (bind mount) | Generated configs | Gateway container on start |

To force a full re-provision of the backend runtime (e.g. after a llama.cpp version
change):

```bash
rm -rf ./config/data/backend-runtime
docker compose up -d
```

---

## Troubleshooting

Field notes from validated installs, known-good versions, and failure modes live in
[docs/docker-field-notes.md](docker-field-notes.md).

### Gateway container exits immediately

Check the logs:

```bash
docker compose logs llm-gateway
```

Common causes: missing `LITELLM_MASTER_KEY`, malformed `config/generated/litellm/litellm.config.yaml`, or the database not yet being reachable on `DATABASE_URL`.

### Backend container exits or shows GPU errors

```bash
docker compose logs llm-server-llamacpp
```

- NVIDIA: confirm Container Toolkit is installed (`docker run --gpus all nvidia/cuda:... nvidia-smi`)
- AMD: confirm `/dev/kfd` exists and the user has `render` and `video` group membership

### apt-get hangs during image build

Docker's bridge network has unreliable DNS on some Linux hosts. Build with host networking:

```bash
docker build --network=host -f docker/Dockerfile.gateway-base -t audia-gateway-base:local .
docker build --network=host -f docker/Dockerfile.gateway \
  --build-arg GATEWAY_BASE_IMAGE=audia-gateway-base:local \
  -t audia-llm-gateway .
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
docker compose restart llm-server-llamacpp
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

### vLLM enablement

vLLM routing is intentionally gated behind `AUDIA_ENABLE_VLLM=true`. Starting the
`llm-server-vllm` profile without that flag leaves LiteLLM on the llama-swap-only
catalog so the gateway does not advertise dead vLLM aliases.

When enabled, the generator writes `config/generated/vllm/vllm.config.json`, nginx
adds `/vllm/` and `/vllm-health`, and the watcher restarts `llm-server-vllm` when the
generated vLLM config or relevant env values change. The Hugging Face cache mount
should use `MODEL_HF_ROOT`, not `MODEL_ROOT`, so raw HF weights stay separate from
GGUF files. On AMD hosts, use [`docker/examples/docker-compose.amd.yml`](../docker/examples/docker-compose.amd.yml),
set `LLAMA_BACKEND=vulkan` or `LLAMA_BACKEND=rocm` for `llama.cpp`, and use the
validated ROCm image (`vllm/vllm-openai-rocm:latest`) for the optional `vLLM`
service with `/dev/kfd`, `/dev/dri`, `ipc: host`, and `SYS_PTRACE`.

You can keep vLLM runtime options next to model definitions in
`config/local/models.override.yaml` under `model_profiles.<name>.defaults.vllm` and
`model_profiles.<name>.deployments.<deployment>.vllm`. Example:

```yaml
model_profiles:
  vllm_default:
    defaults:
      vllm:
        gpu_memory_utilization: ${VLLM_GPU_MEM}
        max_model_len: ${VLLM_MAX_LEN}
    deployments:
      vllm_primary:
        framework: vllm
        transport: direct
        backend_model_name: ${VLLM_MODEL}
        vllm:
          tensor_parallel_size: ${VLLM_TENSOR_PARALLEL_SIZE}
          pipeline_parallel_size: ${VLLM_PIPELINE_PARALLEL_SIZE}
          visible_devices: ${VLLM_VISIBLE_DEVICES}
```

You can define backend-specific split settings in a shared `gpu_profiles` preset so
the same profile name can be reused by both `llama.cpp` and `vLLM`:

```yaml
presets:
  gpu_profiles:
    gpu_equal:
      llamacpp-vulkan:
        device: [Vulkan0, Vulkan1]
        split_mode: layer
        tensor_split: [1, 1]
      vllm-rocm:
        visible_devices: "0,1"
        tensor_parallel_size: 1
        pipeline_parallel_size: 1

model_profiles:
  vllm_default:
    defaults:
      gpu_preset: gpu_equal
    deployments:
      vllm_primary:
        framework: vllm
        transport: direct
        backend_model_name: ${VLLM_MODEL}
```

Supported backend keys inside `gpu_profiles.<name>`:

- `llamacpp-vulkan`
- `llamacpp-rocm`
- `llamacpp-cuda`
- `llamacpp-cpu`
- `vllm-rocm`
- `vllm-cuda` (if you use a CUDA vLLM image)

Direct `vllm:` values on defaults/deployments/exposures still override preset values.
