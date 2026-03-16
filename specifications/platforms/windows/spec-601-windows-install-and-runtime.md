# Spec 601: Windows Install And Runtime

## Scope

Windows is the primary implementation target.

## Expectations

- PowerShell bootstrap installers are first-class for initial setup
- the installed operational interface is a single `AUDiaLLMGateway.ps1` command with simple actions and optional targets
- an optional `AUDiaLLMGateway.cmd` wrapper may exist as a thin compatibility shim for Command Prompt
- `winget` may be used for dependency installation where appropriate
- native `llama-swap` and `llama-server.exe` remain the baseline runtime path
- Windows `llama.cpp` install profiles must include `windows-vulkan`, `windows-hip`, and `windows-cpu`
- `windows-vulkan` is the default Windows profile
