# Backend Versions and Maintenance

**Last reviewed:** 2026-04-05

This document describes the current implementation for downloading, building,
tracking, and updating backend binaries. It is intentionally grounded in the
live code paths under `src/installer/`, `src/launcher/`, and
`scripts/provision-runtime.sh`.

## Current source of truth

There are two parallel version-management surfaces in the repo:

1. Native install profiles for managed component downloads:
   - `config/project/stack.base.yaml`
   - `config/local/stack.override.yaml`
2. Docker/backend runtime variants used by `llama-swap` and the backend container:
   - `config/project/backend-runtime.base.yaml`
   - `config/local/backend-runtime.override.yaml`

The generated Docker/runtime catalog is:

- `config/generated/llama-swap/backend-runtime.catalog.json`

## Important distinction

The Phase 5 lifecycle docs and benchmark registry track governance metadata such
as `pinned_version`, `floor_version`, and validation status, but the live
runtime provisioner still provisions from the runtime catalog's `version`
field (or `git_ref` for source builds). Treat the benchmark registry as
planning and audit material, not yet the field consumed by the running
provisioner.

## What the implementation supports today

### Native installer profiles

The release installer manages named `llama.cpp` profiles in
`config/project/stack.base.yaml`.

Supported profile fields in current use:

- `platform`
- `backend`
- `version`
- `asset_match_tokens` or `asset_tokens`
- `sidecar_files`

The installer resolves releases through the GitHub API:

- `releases/latest` when `version: latest`
- `releases/tags/<tag>` when a concrete version is configured

### Backend runtime variants

The Docker/runtime path supports multiple concurrent variants of the same
backend through distinct `macro` and `runtime_subdir` values.

Supported runtime variant fields in current use:

- `backend`
- `macro`
- `runtime_subdir`
- `version`
- `source_type`
- `asset_tokens`
- `repo_owner`
- `repo_name`
- `download_url`
- `archive_type`
- `git_url`
- `git_ref`
- `configure_command`
- `build_command`
- `binary_glob`
- `library_glob`
- `apt_packages`
- `enabled`
- `always`

Supported runtime source types:

- `github_release`
- `direct_url`
- `git`

`asset_tokens` is the canonical runtime selector now. The provisioner still
accepts the older `asset_pattern` field for compatibility, but new runtime
variants should use `asset_tokens`.

## Enabled variants in the current project config

The base project config currently enables six ggml release-backed runtime
variants by default:

- `cpu`
- `cuda`
- `rocm`
- `vulkan`
- `rocm-gfx1100-prebuilt`
- `rocm-gfx1030-prebuilt`

The following source-build ROCm variants exist but are disabled by default:

- `rocm-gfx1100-official-custom`
- `rocm-gfx1100-official-preview`
- `rocm-gfx1030-official-custom`

Each enabled variant gets its own persisted runtime directory under
`/app/runtime-root/<runtime_subdir>/active` inside the container.

## Upstream release state

Verified on 2026-04-05:

- `ggml-org/llama.cpp` latest release: `b8661`
  Source: https://github.com/ggml-org/llama.cpp/releases/latest
- `lemonade-sdk/llamacpp-rocm` latest release: `b1199`
  Source: https://github.com/lemonade-sdk/llamacpp-rocm/releases/latest
- `mostlygeek/llama-swap` latest release: `v199`
  Source: https://github.com/mostlygeek/llama-swap/releases/latest

Those are upstream observations only. They do not automatically become the
project's chosen runtime versions unless you update the config that the
installer or runtime provisioner consumes.

## How updates work today

### Check upstream releases

Use the release installer to inspect current gateway and managed component
release availability:

```bash
python -m src.installer.release_installer check-updates --root .
```

On Windows the PowerShell wrapper also exposes this:

```powershell
.\scripts\AUDiaLLMGateway.ps1 check
```

### Update the project release bundle

To update the AUDia gateway release itself:

```bash
python -m src.installer.release_installer update-release --root .
```

Windows wrapper:

```powershell
.\scripts\AUDiaLLMGateway.ps1 update
```

### Bump all ggml-backed runtime variants together

The runtime catalog defaults to:

```yaml
defaults:
  version: ${LLAMA_VERSION}
```

If you want all default ggml release variants to move together, set
`LLAMA_VERSION` in `.env` or override `defaults.version` locally.

Example:

```yaml
defaults:
  version: b8661
```

### Bump one runtime variant without changing the others

Override that variant in `config/local/backend-runtime.override.yaml`:

```yaml
variants:
  vulkan:
    version: b8661

  rocm:
    version: b8583
```

This is the current mechanism for maintaining differing backend builds at the
same time.

### Add an alternate upstream release channel

Example: add a Lemonade ROCm lane as a runtime variant:

```yaml
variants:
  rocm-lemonade:
    backend: rocm
    macro: llama-server-rocm-lemonade
    runtime_subdir: rocm/lemonade
    source_type: github_release
    repo_owner: lemonade-sdk
    repo_name: llamacpp-rocm
    version: b1199
    asset_tokens:
      - ubuntu
      - rocm
    enabled: false
```

### Add a reproducible source-build lane

For `git` variants, prefer an immutable commit SHA in `git_ref` when you want
reproducibility:

```yaml
variants:
  rocm-gfx1100-preview:
    backend: rocm
    macro: llama-server-rocm-gfx1100-preview
    runtime_subdir: rocm/gfx1100/preview
    source_type: git
    git_url: https://github.com/ROCm/llama.cpp.git
    git_ref: 0123456789abcdef0123456789abcdef01234567
    configure_command: cmake -S . -B build -DLLAMA_BUILD_SERVER=ON -DGGML_HIPBLAS=ON -DAMDGPU_TARGETS=gfx1100 -DCMAKE_HIP_ARCHITECTURES=gfx1100 -DCMAKE_BUILD_TYPE=Release
    build_command: cmake --build build --config Release --parallel
    binary_glob: build/bin/llama-server
    library_glob: build/bin/*.so*
    enabled: false
```

## Operational workflow after a version change

1. Edit the relevant local override.
2. Regenerate configs:

```bash
python -m src.launcher.process_manager --root . generate-configs
```

3. Restart the runtime path you use:
   - native: restart the managed processes
   - Docker: restart the backend container or compose stack
4. Verify the generated runtime catalog and the resolved variant entry:

```bash
python -m json.tool config/generated/llama-swap/backend-runtime.catalog.json
```

## Current compatibility notes

- Native install profiles still use `asset_match_tokens` in
  `config/project/stack.base.yaml`; the installer now accepts both
  `asset_match_tokens` and `asset_tokens`.
- Runtime variants should use `asset_tokens`.
- The benchmark governance registry in
  `benchmarks/data/backend-benchmarks/backend-version-registry.yaml` is not yet
  the provisioner's source of truth.
- The POSIX wrapper `scripts/AUDiaLLMGateway.sh` does not currently expose
  `check-updates` or `update-release`; use the Python module directly on
  Linux/macOS.

## Related files

- `config/project/stack.base.yaml`
- `config/project/backend-runtime.base.yaml`
- `config/local/backend-runtime.override.yaml`
- `config/generated/llama-swap/backend-runtime.catalog.json`
- `src/installer/release_installer.py`
- `src/launcher/config_loader.py`
- `scripts/provision-runtime.sh`
- `benchmarks/data/backend-benchmarks/backend-version-registry.yaml`
