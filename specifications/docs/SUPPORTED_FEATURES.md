# Supported Backend Features

**Last reviewed:** 2026-04-05

This page summarizes the backend-management features that are implemented and
usable today.

## Implemented

- Managed `llama.cpp` install profiles for Windows, Linux, and macOS
- Managed backend runtime catalog for Docker/native generation
- Concurrent runtime variants for the same backend family via distinct
  `macro` and `runtime_subdir` values
- Release-backed provisioning from GitHub releases
- Direct-download provisioning via `direct_url`
- Source-build provisioning via `git`
- Smart caching based on runtime signature and version/source settings
- Generated runtime catalog at
  `config/generated/llama-swap/backend-runtime.catalog.json`
- Upstream release checks through
  `python -m src.installer.release_installer check-updates --root .`

## Current backend runtime shape

The runtime catalog currently supports these backend families:

- `cpu`
- `cuda`
- `rocm`
- `vulkan`

The project base config currently ships these enabled variants:

- `cpu`
- `cuda`
- `rocm`
- `vulkan`
- `rocm-gfx1100-prebuilt`
- `rocm-gfx1030-prebuilt`

Optional source-build ROCm variants exist but are disabled by default:

- `rocm-gfx1100-official-custom`
- `rocm-gfx1100-official-preview`
- `rocm-gfx1030-official-custom`

## Version management

### Native installer

Native managed-component downloads use install profiles under
`config/project/stack.base.yaml`.

Current installer profile version field:

- `version`

Current installer asset selector fields accepted by the code:

- `asset_match_tokens`
- `asset_tokens`

### Runtime catalog

Runtime variants use:

- `version` for GitHub release or direct-download lanes
- `git_ref` for source-build lanes
- `asset_tokens` for release asset selection

The lifecycle-governance fields documented in the Phase 5 specs
(`pinned_version`, `floor_version`, `drift_policy`, and related metadata) are
not yet the live fields consumed by the runtime provisioner.

## Supported source types

### `github_release`

Used for ggml release lanes and any alternate GitHub release channel.

Important fields:

- `repo_owner`
- `repo_name`
- `version`
- `asset_tokens`

### `direct_url`

Used when an asset URL is already known and should be downloaded directly.

Important fields:

- `download_url`
- `archive_type`

### `git`

Used for reproducible source builds and experimental ROCm lanes.

Important fields:

- `git_url`
- `git_ref`
- `configure_command`
- `build_command`
- `binary_glob`
- `library_glob`

## Smart caching

Backend runtime provisioning is skipped when the persisted runtime directory
already matches the effective version/source signature and the expected binary
exists. The signature includes:

- backend name
- selected version
- source type
- repository or URL
- asset selector
- git ref
- build commands
- build environment
- runtime subdirectory

## Release discovery

The following upstream release endpoints were verified on 2026-04-05:

- ggml `llama.cpp`: `https://github.com/ggml-org/llama.cpp/releases/latest`
- Lemonade ROCm lane: `https://github.com/lemonade-sdk/llamacpp-rocm/releases/latest`
- `llama-swap`: `https://github.com/mostlygeek/llama-swap/releases/latest`

Use the installer to check current observed versions from code:

```bash
python -m src.installer.release_installer check-updates --root .
```

## Maintainer workflow

### Change all ggml release-backed runtime variants together

Set `LLAMA_VERSION` or override `defaults.version`.

### Change one runtime variant independently

Override that variant in `config/local/backend-runtime.override.yaml` and set
its own `version`.

### Add a new alternate build lane

Create a new variant with a unique:

- `name`
- `macro`
- `runtime_subdir`

Then choose one of:

- `github_release`
- `direct_url`
- `git`

## Known current limitations

- The POSIX wrapper `scripts/AUDiaLLMGateway.sh` does not expose `check-updates`
  or `update-release`; use the Python module directly on Linux/macOS.
- The benchmark/version registry is maintained separately from the live runtime
  catalog and is not yet the provisioner's source of truth.
- Some historical docs still describe older `asset_pattern` or
  `asset_match_tokens` terminology; new runtime docs should use `asset_tokens`.

## References

- `specifications/docs/BACKEND_VERSIONS.md`
- `specifications/docs/llm-backend-builds.md`
- `specifications/docs/runbook.md`
- `config/project/backend-runtime.base.yaml`
- `config/project/stack.base.yaml`
- `src/installer/release_installer.py`
- `src/launcher/config_loader.py`
- `scripts/provision-runtime.sh`
