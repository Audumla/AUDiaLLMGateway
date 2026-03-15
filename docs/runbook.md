# Runbook

## Config model

Project-managed defaults live under `config/project/`.

Local machine-specific edits live under `config/local/`.

Generated files are written under `config/generated/`.

The updater replaces project-managed files from a release archive but preserves `config/local/`, `.venv/`, `.runtime/`, `.agent_runner/`, and `state/`.

## llama.cpp version/backend selection

The installer can manage a specific `llama.cpp` build.

Project default:

- `config/project/stack.base.yaml`

Local override example:

```yaml
component_settings:
  llama_cpp:
    version: latest
    backend: vulkan
```

For your current Windows setup, `vulkan` should remain the default backend.

If you want the AMD/HIP build instead:

```yaml
component_settings:
  llama_cpp:
    backend: hip
    sidecar_files:
      - R:\tools\llama-bin-amd\libssl-3-x64.dll
      - R:\tools\llama-bin-amd\libcrypto-3-x64.dll
```

## First install from release

### Windows

```powershell
.\bootstrap\AUDiaLLMGateway-install-release.ps1 -Owner Audumla -Repo AUDiaLLMGateway -InstallDir "$HOME\AUDiaLLMGateway"
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

After install, use the single Gateway command:

### Windows

```powershell
.\scripts\AUDiaLLMGateway.ps1 help
```

### Linux/macOS

```bash
./scripts/AUDiaLLMGateway.sh help
```

## Update from release

### Windows

```powershell
.\scripts\AUDiaLLMGateway.ps1 update-release
```

### Linux/macOS

```bash
./scripts/AUDiaLLMGateway.sh update-release
```

## Check online release availability

### Windows

```powershell
.\scripts\AUDiaLLMGateway.ps1 check-updates
```

### Linux/macOS

```bash
./scripts/AUDiaLLMGateway.sh check-updates
```

## Local developer setup

```powershell
.\scripts\AUDiaLLMGateway.ps1 install-stack
.\scripts\AUDiaLLMGateway.ps1 generate-configs
```

## Validate layered config

```powershell
.\scripts\AUDiaLLMGateway.ps1 validate-configs
```

Validation reports type conflicts between project defaults and local overrides. It does not overwrite local files.

## Start the stack

```powershell
$env:LLAMA_SWAP_EXE = "C:\development\tools\llama-swap\llama-swap.exe"
$env:LITELLM_MASTER_KEY = "sk-local-dev"
.\scripts\AUDiaLLMGateway.ps1 start-stack
```

## Stop the stack

```powershell
.\scripts\AUDiaLLMGateway.ps1 stop-stack
```

## Health

```powershell
.\scripts\AUDiaLLMGateway.ps1 healthcheck
.\scripts\AUDiaLLMGateway.ps1 test-routing
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
