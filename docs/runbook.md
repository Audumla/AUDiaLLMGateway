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
.\bootstrap\install-release.ps1 -Owner Audumla -Repo AUDiaLLMGateway -InstallDir "$HOME\AUDiaLLMGateway"
```

### Linux

```bash
./bootstrap/install-release.sh
```

### macOS

```bash
./bootstrap/install-release-macos.sh
```

## Update from release

### Windows

```powershell
.\scripts\update-release.ps1
```

### Linux/macOS

```bash
./scripts/update-release.sh
```

## Check online release availability

### Windows

```powershell
.\scripts\check-updates.ps1
```

### Linux/macOS

```bash
./scripts/check-updates.sh
```

## Local developer setup

```powershell
.\scripts\install-stack.ps1
.\scripts\generate-configs.ps1
```

## Validate layered config

```powershell
.\scripts\validate-configs.ps1
```

Validation reports type conflicts between project defaults and local overrides. It does not overwrite local files.

## Start the stack

```powershell
$env:LLAMA_SWAP_EXE = "C:\development\tools\llama-swap\llama-swap.exe"
$env:LITELLM_MASTER_KEY = "sk-local-dev"
.\scripts\start-stack.ps1
```

## Stop the stack

```powershell
.\scripts\stop-stack.ps1
```

## Health

```powershell
.\scripts\healthcheck.ps1
.\scripts\test-routing.ps1
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
