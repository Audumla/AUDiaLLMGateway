# Runbook

## Config model

Project-managed defaults live under `config/project/`.

Local machine-specific edits live under `config/local/`.

Generated files are written under `config/generated/`.

Generated outputs are grouped by component:

- `config/generated/llama-swap/`
- `config/generated/litellm/`
- `config/generated/mcp/`
- `config/generated/nginx/`

The updater replaces project-managed files from a release archive but preserves `config/local/`, `.venv/`, `.runtime/`, `.agent_runner/`, and `state/`.

## Central network bindings

Service hosts and ports should be configured once in `config/project/stack.base.yaml` under `network`.

The generated application configs then consume those values so you do not have to edit host and port literals separately in:

- LiteLLM config
- `llama-swap` server args
- nginx config
- generated local MCP client config

## Shared model catalog

The backend-agnostic source of truth for model behavior now lives in:

- `config/project/models.base.yaml`
- `config/local/models.override.yaml`

This catalog is intended to hold shared model semantics that can survive backend changes, for example:

- context presets
- GPU placement presets
- runtime behavior presets
- model artifacts
- model source and download URLs
- framework deployments such as `llama_cpp` now and `vllm` later
- exposed LiteLLM aliases
- load groups for activities like coding, reasoning, or vision

Context presets should use human-friendly aliases like `32k`, `64k`, or `96k`. The generator can synthesize the backend context macro from the numeric token value instead of requiring an explicit `llama-swap` macro entry for every size.

GPU and runtime presets should also be expressed in the catalog as structured `llama.cpp` option maps. The generator translates those into `llama-swap` macros, so the backend substrate does not own the preset semantics.

This is the current greenfield schema. The default project config no longer carries older compatibility forms for model exposure or context naming.

This shared catalog is the authoritative model source. `llama-swap` project config is only backend substrate for executable/path primitives. Project model entries, load groups, and translated preset macros are generated from the shared catalog rather than shipped in a separate `llama-swap` inventory.

Load groups should also be defined in the shared catalog. That allows an activity-oriented grouping such as `coding_active` or `reasoning_active` to be translated into backend-specific group mechanics like `llama-swap` persistence and swap behavior.

## llama.cpp install profiles

The installer manages `llama.cpp` through explicit named install profiles.

Project default:

- `config/project/stack.base.yaml`

Local override example:

```yaml
component_settings:
  llama_cpp:
    selected_profile: windows-vulkan
    profiles:
      windows-vulkan:
        version: latest
```

Current first-tier defaults:

- Windows: `windows-vulkan`
- Linux: `linux-cpu`
- macOS: `macos-metal`

Current first-tier profile matrix:

- `windows-vulkan`
- `windows-hip`
- `windows-cpu`
- `linux-vulkan`
- `linux-rocm`
- `linux-cuda`
- `linux-cpu`
- `macos-metal`
- `macos-cpu`

If you want the AMD/HIP build instead:

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

## First install from release

### Windows

```powershell
.\bootstrap\AUDiaLLMGateway-install-release.ps1 -Owner ExampleOrg -Repo AUDiaLLMGateway -InstallDir "$HOME\AUDiaLLMGateway"
```

### Linux

```bash
./bootstrap/AUDiaLLMGateway-install-release.sh
```

### macOS

```bash
./bootstrap/AUDiaLLMGateway-install-release-macos.sh
```

## Unified command

After install, use the single Gateway command with simple actions and optional targets:

### Windows

```powershell
.\scripts\AUDiaLLMGateway.ps1 help
```

### Windows Command Prompt compatibility

```bat
.\scripts\AUDiaLLMGateway.cmd help
```

### Linux/macOS

```bash
./scripts/AUDiaLLMGateway.sh help
```

Per-action wrapper scripts are not part of the supported installed interface.

Examples:

```powershell
.\scripts\AUDiaLLMGateway.ps1 install
.\scripts\AUDiaLLMGateway.ps1 install stack
.\scripts\AUDiaLLMGateway.ps1 install llama_cpp
.\scripts\AUDiaLLMGateway.ps1 update
.\scripts\AUDiaLLMGateway.ps1 update stack
.\scripts\AUDiaLLMGateway.ps1 start
.\scripts\AUDiaLLMGateway.ps1 stop gateway
.\scripts\AUDiaLLMGateway.ps1 check
.\scripts\AUDiaLLMGateway.ps1 check status
.\scripts\AUDiaLLMGateway.ps1 validate
.\scripts\AUDiaLLMGateway.ps1 test
```

`AUDiaLLMGateway.cmd` is only a thin forwarder to the PowerShell entrypoint.

## Update from release

### Windows

```powershell
.\scripts\AUDiaLLMGateway.ps1 update
```

### Linux/macOS

```bash
./scripts/AUDiaLLMGateway.sh update
```

## Check online release availability

### Windows

```powershell
.\scripts\AUDiaLLMGateway.ps1 check
```

### Linux/macOS

```bash
./scripts/AUDiaLLMGateway.sh check
```

## Local developer setup

```powershell
.\scripts\AUDiaLLMGateway.ps1 install stack
.\scripts\AUDiaLLMGateway.ps1 generate
```

## Validate layered config

```powershell
.\scripts\AUDiaLLMGateway.ps1 validate
```

Validation reports type conflicts between project defaults and local overrides. It does not overwrite local files.

## Start the stack

```powershell
$env:LLAMA_SWAP_EXE = "C:\development\tools\llama-swap\llama-swap.exe"
$env:LITELLM_MASTER_KEY = "sk-local-dev"
.\scripts\AUDiaLLMGateway.ps1 start
```

## Stop the stack

```powershell
.\scripts\AUDiaLLMGateway.ps1 stop
```

## Health

```powershell
.\scripts\AUDiaLLMGateway.ps1 check health
.\scripts\AUDiaLLMGateway.ps1 test
```

## Install state

Installer/update state is recorded in:

- `state/install-state.json`

This file tracks:

- installed release version
- selected components
- component install results
- installed `llama.cpp` version/backend/path details
- config validation output
- install root
- last update time
