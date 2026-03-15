# Spec 151: llama.cpp Runtime

## Scope

`llama.cpp` is a managed runtime dependency and must be installable in specific version/backend variants.

## Requirements

- installer must support selecting a `llama.cpp` release version
- installer must support backend variants where release assets exist
- Windows Vulkan is the default baseline for this project
- Windows HIP/ROCm must be selectable as a distinct variant
- sidecar runtime DLLs must be supportable for builds that require them
- install state must record the chosen version, backend, asset, install directory, and executable path

## Configuration

Project defaults live in `project.component_settings.llama_cpp`.

Machine-local overrides may change:

- version
- backend
- install root
- asset matching rules if needed

## Integration

- generated `llama-swap` config should be able to consume the installed `llama-server` path from install state when local overrides do not explicitly replace it
