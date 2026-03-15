# AUDiaLLMGateway

Local-first LLM gateway for a home lab.

Runtime shape:

- `llama.cpp` as an installable/versioned runtime dependency
- `llama-swap` as the local model router and profile catalog
- native `llama-server` processes behind `llama-swap`
- LiteLLM as the OpenAI-compatible gateway
- optional nginx as a single front-door reverse proxy
- MCP scaffolding kept separate and version-aware

## Release install model

This project is now designed to be installed and updated from GitHub release archives, not `git clone`.

Key properties:

- standalone bootstrap scripts for Windows, Linux, and macOS
- update flow that pulls the latest release archive
- project-managed files are replaced on update
- `config/local/*` and `state/*` are preserved on update
- local override configs are validated during updates and warnings are recorded in install state
- `llama.cpp` can be installed in a selected backend/version variant, with Windows Vulkan as the default baseline

## Config layering

Project-managed defaults:

- `config/project/stack.base.yaml`
- `config/project/llama-swap.base.yaml`
- `config/project/mcp.base.yaml`

Local machine overrides:

- `config/local/stack.override.yaml`
- `config/local/llama-swap.override.yaml`
- `config/local/mcp.override.yaml`

Generated outputs:

- `config/generated/llama-swap.generated.yaml`
- `config/generated/litellm.config.yaml`
- `config/generated/litellm.mcp.client.json`

Install/update state:

- `state/install-state.json`

## Initial install from a release

Windows:

```powershell
.\bootstrap\install-release.ps1 -Owner AUDia -Repo AUDiaLLMGateway -InstallDir "$HOME\AUDiaLLMGateway"
```

Linux:

```bash
./bootstrap/install-release.sh
```

macOS:

```bash
./bootstrap/install-release-macos.sh
```

These install scripts:

1. download a GitHub release archive
2. unpack it locally
3. seed local config files if missing
4. install selected components and dependencies
5. write install state

## Updating an installed copy

Windows:

```powershell
.\scripts\update-release.ps1
```

Linux or macOS:

```bash
./scripts/update-release.sh
```

## Local development flow

```powershell
.\scripts\install-stack.ps1
.\scripts\generate-configs.ps1
.\scripts\validate-configs.ps1
.\scripts\start-stack.ps1
.\scripts\healthcheck.ps1
.\scripts\test-routing.ps1
```

## Published LiteLLM aliases

- `local/qwen27_fast` -> `qwen3.5-27b-(96k-Q6)`
- `local/qwen122_smart` -> `qwen3.5-122b`
- `local/qwen4b_vision` -> `qwen3-5-4b-ud-q5-k-xl-vision`

Change those in `config/project/stack.base.yaml` or override them in `config/local/stack.override.yaml`.

## Optional components

The release installer tracks installed components and can install newly added ones during update. Current component set:

- `python_runtime`
- `gateway_python_deps`
- `llama_cpp`
- `llama_swap`
- `nginx` optional

## llama.cpp component

`llama.cpp` is now treated as a managed component.

The project defaults live in `config/project/stack.base.yaml` under `project.component_settings.llama_cpp`.

Machine-specific overrides can go in `config/local/stack.override.yaml`, for example:

```yaml
component_settings:
  llama_cpp:
    version: b9999
    backend: vulkan
```

Current design:

- Windows default backend: `vulkan`
- macOS default backend: `metal`
- Linux default backend: `cpu` unless you override it

Installer state records the installed `llama.cpp` version, backend, asset, install path, and resolved `llama-server` executable path.

## Reverse proxy

Optional nginx config is included at:

- `config/nginx/nginx.conf`
- `docs/reverse-proxy.md`

## MCP note

MCP remains scaffolded, not fully claimed as production-complete. The repo isolates MCP registry and client config so LiteLLM MCP changes can be absorbed without corrupting the core gateway and backend configuration layers.
