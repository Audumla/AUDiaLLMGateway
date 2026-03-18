# Spec 001: Local LLM Gateway (Mid-Level)

## Revised Topology: Full Docker Orchestration

The project has transitioned to a Docker-first deployment model to provide consistent hardware access (NVIDIA/AMD) across different Linux distributions (e.g., Tumbleweed, Ubuntu).

### Core Components

1.  **Orchestrator**: `docker-compose.yml` replaces manual bootstrap scripts.
2.  **API Gateway**: `LiteLLM` (audia-gateway container).
3.  **Swappable Backend**: `llama-swap` + `llama.cpp` (audia-llama-cpp container).
4.  **High-Perf Backend**: `vLLM` (audia-vllm container).
5.  **Watcher**: `audia-watcher` (Handles config regeneration and container restarts).
6.  **Reverse Proxy**: `nginx` (Optional, can be externalized).

### Deployment Profiles

The project provides several pre-configured Docker Compose examples in `docker/examples/`:

- **Universal**: `docker-compose.yml` (Root) - Auto-detects NVIDIA/AMD and handles both.
- **NVIDIA-Only**: `docker/examples/docker-compose.nvidia.yml` - Minimal setup for CUDA.
- **AMD-Only**: `docker/examples/docker-compose.amd.yml` - Minimal setup for ROCm.
- **External Proxy**: `docker/examples/docker-compose.external-proxy.yml` - For integration with host-level Traefik or Nginx.

### Hot Reloading Workflow

1.  User edits `./config/local/*.yaml`.
2.  `audia-watcher` detects `inotify` event.
3.  `audia-watcher` runs `generate-configs`.
4.  `audia-watcher` restarts `audia-llama-cpp` to apply new backend settings.
5.  `audia-watcher` reloads `audia-nginx`.
6.  `LiteLLM` detects the update to its generated config and refreshes its model list.

### Hardware Passthrough

The stack is configured to expose:
- `/dev/kfd` and `/dev/dri` for AMD (ROCm/Vulkan).
- `nvidia` driver capabilities for NVIDIA (CUDA).
