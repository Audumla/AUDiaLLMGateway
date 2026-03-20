# AUDiaLLMGateway

Local-first LLM gateway for a home lab. Runs entirely on your own hardware — no
cloud dependencies, no usage fees.

## What it does

Provides an OpenAI-compatible API endpoint backed by local models:

- `llama.cpp` as the inference runtime (versioned, managed component)
- `llama-swap` as the local model router — load/unload models on demand
- `vLLM` as an optional persistent high-throughput backend
- `LiteLLM` as the OpenAI-compatible API gateway
- `nginx` as an optional single front-door reverse proxy
- Config generated from a shared model catalog — define a model once, target multiple backends

---

## Quick Start

**Choose your deployment path:**

| Path | Best for |
| ---- | -------- |
| [Docker](docs/docker.md) | Linux home lab or server — recommended |
| [Native install](docs/runbook.md) | Windows, macOS, or Linux without Docker |

### Docker (Linux — recommended)

```bash
cp config/env.example .env
# optional: edit .env to replace the default LITELLM key before exposing the gateway
docker compose up -d
```

For guided Docker setup on Linux, use:

```bash
./scripts/docker-setup.sh
```

The provisioned `llama.cpp` runtime is persisted on the host under
`./config/data/backend-runtime/<backend>` by default so you can inspect, back up,
or repair the downloaded binaries and backend plugins directly.

The root [`docker-compose.yml`](docker-compose.yml) is deployment-oriented and
pulls published images only, so a remote host can stay a clean Docker Compose
install without a git checkout.

Compose service names follow the deployment naming convention:
`llm-gateway`, `llm-server-llamacpp`, `llm-server-vllm`, and
`llm-config-watcher`. The Docker `container_name` values remain the shorter
`audia-*` names.

On first Docker start, LiteLLM Admin UI login defaults to username `admin` and password `sk-local-dev` unless you override `LITELLM_MASTER_KEY`.

To add the optional `vLLM` backend, set `AUDIA_ENABLE_VLLM=true` in `.env` and start the profile.
For NVIDIA hosts, the root compose profile is the direct path:

```bash
docker compose --profile vllm up -d
```

For AMD hosts, use the AMD compose profile from [docs/docker.md](docs/docker.md)
rather than the root compose.

See [docs/docker.md](docs/docker.md) for all deployment profiles (Universal, NVIDIA, AMD, External Proxy).

For local source-based Docker development, use:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

### Native install

**Windows:**

```powershell
.\bootstrap\AUDiaLLMGateway-install-release.ps1 -Owner Audumla -Repo AUDiaLLMGateway -InstallDir "$HOME\AUDiaLLMGateway"
```

**Linux / macOS:**

```bash
./bootstrap/AUDiaLLMGateway-install-release.sh
```

See [docs/runbook.md](docs/runbook.md) for the full native install and operations guide.

---

## Documentation

| Document | Contents |
| -------- | -------- |
| [docs/docker.md](docs/docker.md) | Docker deployment — all profiles, setup, management |
| [docs/docker-field-notes.md](docs/docker-field-notes.md) | Docker install field notes — validated versions, first-install issues, recovery notes |
| [docs/runbook.md](docs/runbook.md) | Native install, update, start/stop, config validation |
| [docs/architecture.md](docs/architecture.md) | System design — runtime, config, and installer topology |
| [docs/reverse-proxy.md](docs/reverse-proxy.md) | nginx routes, config generation, upstream layout |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Common issues and fixes |

---

## How it works

### Runtime shape

```text
Client / tool
  └─> nginx (optional, port 8080)
        └─> LiteLLM (port 4000)
              ├─> llama-swap (port 41080)
              │     └─> llama-server processes (llama.cpp)
              └─> vLLM (optional, port 8000)
```

Clients speak the OpenAI API. LiteLLM translates model alias names to backend routes.
llama-swap loads and unloads llama.cpp model processes as requests arrive.

### Config layering

The system uses three config layers that merge at generation time:

| Layer | Location | Managed by |
| ----- | -------- | ---------- |
| Project base | `config/project/` | Release updates |
| Local overrides | `config/local/` | You — never overwritten |
| Generated | `config/generated/` | Config generator — safe to overwrite |

Project base files:

- `config/project/stack.base.yaml` — services, network, components
- `config/project/models.base.yaml` — shared catalog scaffold and empty defaults
- `config/project/llama-swap.base.yaml` — llama-swap substrate
- `config/project/mcp.base.yaml` — MCP scaffold

Local override files:

- `config/local/stack.override.yaml`
- `config/local/models.override.yaml`
- `config/local/llama-swap.override.yaml`
- `config/local/mcp.override.yaml`

Generated outputs:

- `config/generated/llama-swap/llama-swap.generated.yaml`
- `config/generated/litellm/litellm.config.yaml`
- `config/generated/vllm/vllm.config.json`
- `config/generated/nginx/nginx.conf`
- `config/generated/mcp/litellm.mcp.client.json`

### Shared model catalog

Install-local model definitions live in `config/local/models.override.yaml` — no
duplicating parameters into per-backend files. The shared project base now provides
the scaffold and merge targets used by the local catalog. The catalog holds:

- model profiles (artifacts, deployments per backend)
- context presets (`32k`, `64k`, `96k`, `256k`)
- GPU placement presets
- runtime behavior presets
- exposed LiteLLM gateway aliases
- load groups (coding, reasoning, vision)

The config generator translates the catalog into backend-specific config at
generation time. Machine-specific additions go in `config/local/models.override.yaml`.

### Central network config

All service hosts and ports are configured once in `config/project/stack.base.yaml`
under `network`. The generator propagates those values into LiteLLM, llama-swap,
nginx, and MCP client configs automatically.

Override a port in `config/local/stack.override.yaml`:

```yaml
network:
  litellm:
    port: 5000
```

---

## Unified management command

After install, everything is managed through a single command:

**Linux / macOS:**

```bash
./scripts/AUDiaLLMGateway.sh help
./scripts/AUDiaLLMGateway.sh install
./scripts/AUDiaLLMGateway.sh update
./scripts/AUDiaLLMGateway.sh start
./scripts/AUDiaLLMGateway.sh stop
./scripts/AUDiaLLMGateway.sh check
./scripts/AUDiaLLMGateway.sh check health
./scripts/AUDiaLLMGateway.sh generate
./scripts/AUDiaLLMGateway.sh validate
./scripts/AUDiaLLMGateway.sh test
```

**Windows (PowerShell):**

```powershell
.\scripts\AUDiaLLMGateway.ps1 help
```

**Windows (Command Prompt):**

```bat
.\scripts\AUDiaLLMGateway.cmd help
```

---

## llama.cpp component

`llama.cpp` is a managed component — the installer downloads the right build for
your hardware and records the path in `state/install-state.json`.

Platform defaults:

| Platform | Default profile |
| -------- | --------------- |
| Windows | `windows-vulkan` |
| Linux | `linux-cpu` |
| macOS | `macos-metal` |

Available profiles:

- Windows: `windows-vulkan`, `windows-hip`, `windows-cpu`
- Linux: `linux-vulkan`, `linux-rocm`, `linux-cuda`, `linux-cpu`
- macOS: `macos-metal`, `macos-cpu`

Override the profile in `config/local/stack.override.yaml`:

```yaml
component_settings:
  llama_cpp:
    selected_profile: linux-rocm
```

For Windows AMD/HIP builds that need sidecar DLLs:

```yaml
component_settings:
  llama_cpp:
    selected_profile: windows-hip
    profiles:
      windows-hip:
        sidecar_files:
          - R:\tools\llama-bin-amd\libssl-3-x64.dll
          - R:\tools\llama-bin-amd\libcrypto-3-x64.dll
```

---

## Published LiteLLM aliases

The default model catalog exposes:

- `local/qwen27_fast` → `qwen3.5-27b-(96k-Q6)`
- `local/qwen122_smart` → `qwen3.5-122b`
- `local/qwen4b_vision` → `qwen3-5-4b-ud-q5-k-xl-vision`

Change aliases in `config/project/stack.base.yaml` or override in
`config/local/stack.override.yaml`.

---

## Optional components

| Component | Required | Notes |
| --------- | -------- | ----- |
| `python_runtime` | Yes | Python 3.10+ |
| `gateway_python_deps` | Yes | LiteLLM and dependencies |
| `llama_cpp` | Yes | Inference runtime |
| `llama_swap` | Yes | Model router |
| `nginx` | No | Reverse proxy front-door |

---

## Reverse proxy

Optional nginx is configured via code generation. See [docs/reverse-proxy.md](docs/reverse-proxy.md).
Route layout: `/v1/` → LiteLLM, `/llamaswap/` → llama-swap, `/vllm/` → vLLM when enabled, `/health` → status.

---

## MCP

MCP remains scaffolded but not production-complete. Config is isolated so LiteLLM
MCP changes can be absorbed without touching the core gateway config.

---

## Updating

**Native install:**

```bash
./scripts/AUDiaLLMGateway.sh update
```

**Docker:**

```bash
docker compose pull && docker compose up -d
```

The update replaces project-managed files from the release archive and preserves
`config/local/`, `state/`, `models/`, and `.env`.
