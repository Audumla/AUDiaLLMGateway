# Architecture

## Deployment paths

Two paths lead to the same runtime stack. Choose based on your environment.

**Docker (Linux — recommended):**

```text
docker compose up -d
  └─> llm-gateway service       (LiteLLM + config generator)
  └─> llm-server-llamacpp       (llama-swap + llama.cpp, auto-provisioned)
  └─> nginx service             (optional reverse proxy)
```

**Native install (Windows / macOS / Linux):**

```text
bootstrap script
  └─> release_installer.py
        └─> downloads llama.cpp, llama-swap, nginx from GitHub releases
        └─> installs Python deps into .venv
        └─> seeds config/local/ files
        └─> writes state/install-state.json
```

After native install, `AUDiaLLMGateway.sh` / `.ps1` manages start/stop.

---

## Runtime topology

```text
Client or tool
  └─> nginx (optional, port 8080)
        └─> LiteLLM (port 4000)
              └─> llama-swap (port 41080)
                    └─> llama-server processes (llama.cpp)
```

Optional MCP path (scaffolded, not production-complete):

```text
Client or tool
  └─> LiteLLM MCP endpoint
        └─> configured MCP servers
```

---

## Config topology

Three layers merge at generation time. The config generator reads project base and
local overrides, then writes the generated layer.

**Project layer** (`config/project/`):

- shipped in GitHub releases
- updated by the release installer on each update
- safe to replace — do not edit directly

**Local layer** (`config/local/`):

- machine-owned; managed by you
- never overwritten by a release update
- holds paths, local model additions, port overrides, optional component choices
- **Docker**: seeded automatically on first gateway container start if files are absent
- **Native**: seeded by `postinstall.sh` on package install

**Generated layer** (`config/generated/`):

- derived from project + local config
- safe to regenerate at any time with `generate`
- grouped by component: `llama-swap/`, `litellm/`, `nginx/`, `mcp/`

---

## Installer topology (native path)

```text
Bootstrap script
  └─> download GitHub release archive
  └─> unpack bundle
  └─> sync managed files (project layer)
  └─> preserve local files (local layer)
  └─> install required and selected components
        └─> python_runtime
        └─> gateway_python_deps (.venv)
        └─> llama_cpp (versioned binary, platform profile)
        └─> llama_swap (GitHub release binary)
        └─> nginx (optional)
  └─> validate layered config
  └─> write install state (state/install-state.json)
```

---

## State tracking

`state/install-state.json` is the installer-facing source for:

- installed version
- selected components and their install results
- install locations and resolved executable paths
- installed llama.cpp version, backend, and profile metadata
- config validation warnings
- last successful update time

---

## Script action routing

`AUDiaLLMGateway.sh` (and `.ps1`) routes actions to either the Python layer or
Docker Compose depending on the command — Docker is never required for native
operations.

| Action group | Commands | Requires Docker? |
| ------------ | -------- | ---------------- |
| Native install | `install stack` · `install components` · `install firewall` | No |
| Config ops | `generate` · `validate` | No |
| Native runtime | `start` · `stop` · `status` | No |
| Docker ops | `docker start/stop/restart/update/status/health/logs` | Yes (lazy) |
| Legacy aliases | `check status/health/logs` · `update` | Yes (lazy) |

`docker_cmd()` is resolved lazily — it is only called when a Docker action is
invoked. Native commands (`install`, `generate`, `validate`, `start`, `stop`,
`status`) work in any environment without Docker present.

---

## Executable resolution

`load_stack_config()` resolves executable paths at config-load time using a
three-tier priority chain:

1. **YAML config** — an absolute path in `stack.override.yaml` wins outright.
2. **install-state.json** — `component_results.<name>.path` written by the
   component installer. This is the primary mechanism for tools installed outside
   the venv (e.g. nginx via apt, llama-swap via GitHub release).
3. **Fallback** — `shutil.which()` or bare name passed to the OS.

The Windows registry is intentionally not consulted. Installers write the resolved
absolute path to `install-state.json` immediately after installing, so the path is
available in any subsequent process regardless of how the shell environment was
inherited.

Components that write to `install-state.json`:

- `ensure_llama_swap` → `component_results.llama_swap.path`
- `ensure_nginx` → `component_results.nginx.path`
- `ensure_llama_cpp` → `component_results.llama_cpp.executable_path`
- `ensure_models` → `component_results.models.model_dir` + per-model paths

---

## Config generation

The generator (`src/launcher/config_loader.py`) merges the three config layers and
writes five output files:

| Output | Path | Consumed by |
| ------ | ---- | ----------- |
| llama-swap config | `config/generated/llama-swap/llama-swap.generated.yaml` | llama-swap |
| LiteLLM config | `config/generated/litellm/litellm.config.yaml` | LiteLLM |
| nginx config | `config/generated/nginx/nginx.conf` | nginx |
| nginx landing page | `config/generated/nginx/index.html` | nginx |
| MCP client config | `config/generated/mcp/litellm.mcp.client.json` | MCP clients |
| systemd unit | `config/generated/systemd/audia-gateway.service` | systemd |

Run generation manually:

```bash
./scripts/AUDiaLLMGateway.sh generate
```

The generator is idempotent and tracks content hashes to detect which outputs
actually changed.
