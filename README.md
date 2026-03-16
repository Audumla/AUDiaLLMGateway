# AUDiaLLMGateway

Local-first LLM gateway for a home lab.

Runtime shape:

- `llama.cpp` as an installable/versioned runtime dependency
- `llama-swap` as the local model router and generated backend runtime
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
- `config/project/models.base.yaml`
- `config/project/mcp.base.yaml`

Local machine overrides:

- `config/local/stack.override.yaml`
- `config/local/llama-swap.override.yaml`
- `config/local/models.override.yaml`
- `config/local/mcp.override.yaml`

Generated outputs:

- `config/generated/llama-swap/llama-swap.generated.yaml`
- `config/generated/litellm/litellm.config.yaml`
- `config/generated/mcp/litellm.mcp.client.json`
- `config/generated/nginx/nginx.conf`

## Shared model catalog

The repo now has a backend-agnostic model catalog layer:

- `config/project/models.base.yaml`
- `config/local/models.override.yaml`

This is the common model definition layer for:

- model profiles
- shared context presets
- shared GPU presets
- runtime presets
- framework-specific deployments
- exposed gateway aliases
- source/download URLs for model artifacts
- load groups for persistent or swappable model sets

Context presets can now use simple aliases like `32k`, `64k`, or `96k`. The generator will translate the alias into the backend arg string, so you do not need a hand-authored macro entry for every context size.

GPU and runtime presets are also defined at the catalog layer as structured `llama.cpp` option maps. The generator renders those into backend-specific `llama-swap` macros, so the project no longer treats the raw macro bodies as the source of truth.

This repo now treats the catalog schema as greenfield: the alias-first model catalog is the current format, and there is no second shipped model catalog in `llama-swap` project config.

## Central network config

Hosts and ports should be configured centrally in `config/project/stack.base.yaml` under `network`.

That central section now drives generated bindings for:

- LiteLLM API base URLs
- `llama-swap` runtime host/port
- generated nginx upstreams and listen address
- generated MCP client URL for the local gateway

Current generators use that catalog to:

- build LiteLLM model exposure config
- generate `llama-swap` model entries, load groups, and translated preset macros for `llama.cpp` deployments

That means model intent and common parameters live once, then get translated into backend-specific config at generation time.

Install/update state:

- `state/install-state.json`

## Initial install from a release

Windows:

```powershell
.\bootstrap\AUDiaLLMGateway-install-release.ps1 -Owner ExampleOrg -Repo AUDiaLLMGateway -InstallDir "$HOME\AUDiaLLMGateway"
```

Linux:

```bash
./bootstrap/AUDiaLLMGateway-install-release.sh
```

macOS:

```bash
./bootstrap/AUDiaLLMGateway-install-release-macos.sh
```

These install scripts:

1. download a GitHub release archive
2. unpack it locally
3. seed local config files if missing
4. install selected components and dependencies
5. write install state

## Unified command

Once the repo is installed locally, use a single command with simple actions and optional targets:

Windows:

```powershell
.\scripts\AUDiaLLMGateway.ps1 help
```

Windows Command Prompt compatibility:

```bat
.\scripts\AUDiaLLMGateway.cmd help
```

Linux or macOS:

```bash
./scripts/AUDiaLLMGateway.sh help
```

Per-action wrapper scripts are not part of the supported installed interface.

Examples:

```powershell
.\scripts\AUDiaLLMGateway.ps1 install
.\scripts\AUDiaLLMGateway.ps1 install stack
.\scripts\AUDiaLLMGateway.ps1 update
.\scripts\AUDiaLLMGateway.ps1 start
.\scripts\AUDiaLLMGateway.ps1 stop gateway
.\scripts\AUDiaLLMGateway.ps1 check
.\scripts\AUDiaLLMGateway.ps1 validate
.\scripts\AUDiaLLMGateway.ps1 test
```

The `.cmd` file is a thin compatibility shim for Command Prompt. PowerShell remains the canonical Windows entrypoint.

## Updating an installed copy

Windows:

```powershell
.\scripts\AUDiaLLMGateway.ps1 update
```

Linux or macOS:

```bash
./scripts/AUDiaLLMGateway.sh update
```

Check upstream release availability without updating:

```powershell
.\scripts\AUDiaLLMGateway.ps1 check
```

## Local development flow

```powershell
.\scripts\AUDiaLLMGateway.ps1 install stack
.\scripts\AUDiaLLMGateway.ps1 generate
.\scripts\AUDiaLLMGateway.ps1 validate
.\scripts\AUDiaLLMGateway.ps1 start
.\scripts\AUDiaLLMGateway.ps1 check health
.\scripts\AUDiaLLMGateway.ps1 test
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
    selected_profile: windows-vulkan
    profiles:
      windows-vulkan:
        version: b9999
```

Current design:

- first-tier platform defaults:
  - Windows: `windows-vulkan`
  - Linux: `linux-cpu`
  - macOS: `macos-metal`
- first-tier install profiles also include:
  - `windows-hip`
  - `windows-cpu`
  - `linux-vulkan`
  - `linux-rocm`
  - `linux-cuda`
  - `macos-cpu`

Installer state records the installed `llama.cpp` profile, version, backend, asset, install path, and resolved `llama-server` executable path.

If a selected Windows AMD/HIP build needs sidecar DLLs, add them in `config/local/stack.override.yaml`:

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

## Reverse proxy

Optional nginx config is included at:

- `config/generated/nginx/nginx.conf`
- `docs/reverse-proxy.md`

## MCP note

MCP remains scaffolded, not fully claimed as production-complete. The repo isolates MCP registry and client config so LiteLLM MCP changes can be absorbed without corrupting the core gateway and backend configuration layers.
