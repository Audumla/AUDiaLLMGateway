# Spec 001: Local LLM Gateway (Mid-Level Architecture)

## Status

Implemented (v0.6.x)

## Purpose

Describe the mid-level architecture of AUDiaLLMGateway — the component topology,
deployment models, config system, and the scope of what has been built.

---

## Runtime Topology

```text
Client / tool
  └─> nginx (optional, port 8080)
        └─> LiteLLM API gateway (port 4000)
              ├─> llama-swap model router (port 41080)
              │     └─> llama-server processes (llama.cpp)
              └─> vLLM backend (optional, port 8000)
```

All service ports are configured centrally under `network` in
`config/project/stack.base.yaml` and propagated to all generated configs by the
config generator. See `docs/architecture.md` for the full config and installer
topology.

---

## Deployment Models

Two deployment paths are supported. They share the same config system and model
catalog.

### Path A: Docker (Linux — recommended for servers)

`docker-compose.yml` orchestrates the stack. Hardware detection and binary
provisioning happen inside the backend container on first start.

On first gateway container start, `docker/gateway-entrypoint.sh` auto-seeds
`config/local/` with commented template files (`stack.override.yaml`,
`models.override.yaml`, `env`) if they are absent, then runs `generate-configs`
before starting LiteLLM. Subsequent restarts skip the seed step.

Deployment profiles in `docker/examples/`:

| Profile | File | Use case |
| ------- | ---- | -------- |
| Universal | `docker-compose.yml` (root) | Auto-detects NVIDIA/AMD |
| NVIDIA only | `docker/examples/docker-compose.nvidia.yml` | CUDA systems |
| AMD only | `docker/examples/docker-compose.amd.yml` | ROCm/Vulkan systems |
| External proxy | `docker/examples/docker-compose.external-proxy.yml` | Behind Traefik/nginx |

See [docs/docker.md](../docs/docker.md) for setup instructions, environment
variables, port reference, and troubleshooting.

### Path B: Native install (Windows, macOS, Linux)

Bootstrap scripts install from a GitHub release archive. The installer manages
`llama.cpp`, `llama-swap`, `nginx`, and Python dependencies as versioned
components. Install state is recorded in `state/install-state.json`.

Platform-specific bootstrap scripts live in `bootstrap/`. After install, all
operations go through `scripts/AUDiaLLMGateway.sh` (Linux/macOS) or
`scripts/AUDiaLLMGateway.ps1` (Windows).

See [docs/runbook.md](../docs/runbook.md) for the full native operations guide.

---

## Core Components

| Component | Technology | Role |
| --------- | ---------- | ---- |
| API gateway | LiteLLM | OpenAI-compatible endpoint, model alias routing |
| Model router | llama-swap | Load/unload llama-server processes on demand |
| Inference runtime | llama.cpp (`llama-server`) | GPU/CPU inference |
| Reverse proxy | nginx (optional) | Single front-door, auth forwarding |
| Config generator | Python (`config_loader.py`) | Merges catalog → backend-specific configs |
| Installer | Python (`release_installer.py`) | Downloads, unpacks, manages components |

---

## Config System

Three layers merge at generation time:

| Layer | Path | Notes |
| ----- | ---- | ----- |
| Project base | `config/project/` | Shipped in releases; updated by installer |
| Local overrides | `config/local/` | Machine-owned; never overwritten by updates |
| Generated | `config/generated/` | Derived outputs; safe to regenerate |

The shared model catalog (`config/project/models.base.yaml`) is the single source
of truth for model definitions. The generator translates it to `llama-swap` and
`LiteLLM` configs at generation time. See
[spec-002](spec-002-model-catalog-and-config-lifecycle.md) for the full catalog
schema and generation lifecycle.

---

## Hardware Passthrough (Docker)

The Docker profiles expose hardware through device mappings:

**AMD (ROCm/Vulkan):**

```yaml
devices:
  - /dev/kfd:/dev/kfd
  - /dev/dri:/dev/dri
group_add:
  - video
  - render
```

**NVIDIA (CUDA):**

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

---

## What is not yet implemented

| Feature | Status | Spec |
| ------- | ------ | ---- |
| Config watcher (auto-reload on file change) | Stub only (`src/launcher/watcher.py`) | spec-002 |
| Selective component reload | Not implemented | spec-002 |
| vLLM backend integration | Implemented in Docker with generated config, watcher restarts, and nginx `/vllm/` proxy | spec-251 |
| Interactive component selection at install | Not implemented | spec-002 |

The hot-reload workflow described in early drafts of this spec (inotify detection →
auto-regenerate → selective restart) is not yet implemented. The current workflow
is: edit config → run `generate` → restart affected services.
