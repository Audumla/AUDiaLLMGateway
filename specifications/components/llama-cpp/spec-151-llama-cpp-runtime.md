# Spec 151: llama.cpp Runtime

## Scope

`llama.cpp` is a managed runtime dependency and must be installable through explicit named profiles that model supported platform and backend combinations.

## Requirements

- installer must support selecting a `llama.cpp` release version per install profile
- installer must support explicit install profiles for supported platform/backend combinations where release assets exist
- Windows, Linux, and macOS are all first-tier platforms in the configuration model
- Windows Vulkan must be selectable as a distinct profile
- Windows HIP must be selectable as a distinct profile
- Linux CPU, Vulkan, ROCm, and CUDA must be modelable as distinct profiles
- macOS Metal and CPU must be modelable as distinct profiles
- sidecar runtime DLLs must be supportable for builds that require them
- install state must record the chosen profile, version, backend, asset, install directory, and executable path

## Configuration

Project defaults live in `project.component_settings.llama_cpp`.

Machine-local overrides may change:

- selected profile
- profile-specific version
- profile-specific sidecars
- install root
- asset matching rules if needed

## Integration

- generated `llama-swap` config should be able to consume the installed `llama-server` path from install state when local overrides do not explicitly replace it
