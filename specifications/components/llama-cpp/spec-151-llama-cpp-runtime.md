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
- Docker runtime launch must ensure backend plugins (`libggml-*.so`) are present alongside the provisioned binaries on every container start, not only on first provision
- Docker runtime persistence must isolate backend-specific runtime state under a backend-namespaced directory rather than reusing one shared runtime path across Vulkan, ROCm, CUDA, and CPU
- backend runtime source definitions must be stored in a dedicated backend runtime catalog, separate from model catalog semantics
- backend runtime catalog must support multiple variants of the same backend concurrently (for example multiple ROCm tags)
- backend runtime catalog must support source types: `github_release`, `direct_url`, and `git`
- each runtime variant must produce a stable executable macro name that model deployments can reference
- generated runtime catalog output must be written to `config/generated/llama-swap/backend-runtime.catalog.json`
- backend runtime catalog must support reusable profile composition so source policy and build policy can be defined once and reused across variants
- profile composition must support inheritance (`extends`) and per-variant override
- runtime catalog must be able to express explicit AMD ROCm build targets (for example `gfx1030` and `gfx1100`) across multiple upstream repos

## Configuration

Project defaults live in `project.component_settings.llama_cpp`.

Machine-local overrides may change:

- selected profile
- profile-specific version
- profile-specific sidecars
- install root
- asset matching rules if needed

Docker runtime variants are configured through layered files:

- `config/project/backend-runtime.base.yaml`
- `config/local/backend-runtime.override.yaml`

Each variant entry must allow:

- `backend` (cpu, cuda, rocm, vulkan, etc.)
- `macro` (for example `llama-server-rocm-b8429`)
- `runtime_subdir` (backend-specific cache path under runtime root)
- source controls:
  - `source_type: github_release` + `repo_owner` + `repo_name` + `version` + `asset_tokens`
  - `source_type: direct_url` + `download_url` + optional `archive_type`
  - `source_type: git` + `git_url` + `git_ref` + build commands/globs

Optional controls:

- `enabled`
- `always`
- `apt_packages`
- `command` (manual override macro command)
- `profile` / `profiles` (reusable runtime profile references)

Optional profile controls:

- `extends` (inherit from one or more profiles)
- any source/build fields supported by variants (`source_type`, `git_url`, `configure_command`, etc.)

## Integration

- generated `llama-swap` config should be able to consume the installed `llama-server` path from install state when local overrides do not explicitly replace it
- Docker entrypoints must refresh backend plugin symlinks before launch so persisted runtime volumes remain runnable after image updates or container recreation
- Docker entrypoints must resolve `/app/runtime` from a backend-specific subdirectory under the visible `BACKEND_RUNTIME_ROOT` base path
- models must not define backend binary source locations directly; models only reference deployment macros produced by backend runtime catalog generation
