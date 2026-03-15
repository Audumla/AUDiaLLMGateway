# Runbook

## Config model

Project-managed defaults live under `config/project/`.

Local machine-specific edits live under `config/local/`.

Generated files are written under `config/generated/`.

The updater replaces project-managed files from a release archive but preserves `config/local/`, `.venv/`, `.runtime/`, `.agent_runner/`, and `state/`.

## First install from release

### Windows

```powershell
.\bootstrap\install-release.ps1 -Owner AUDia -Repo AUDiaLLMGateway -InstallDir "$HOME\AUDiaLLMGateway"
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
- config validation output
- install root
- last update time
