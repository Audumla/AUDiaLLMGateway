# LLM Backend Build and Update Workflow

**Last reviewed:** 2026-04-05

This document is the maintainer-facing guide for building, provisioning, and
updating differing backend variants.

## Canonical implementation files

- Runtime variant definitions:
  `config/project/backend-runtime.base.yaml`
- Machine-local runtime overrides:
  `config/local/backend-runtime.override.yaml`
- Native managed-component install profiles:
  `config/project/stack.base.yaml`
- Generated runtime catalog:
  `config/generated/llama-swap/backend-runtime.catalog.json`
- Runtime provisioner:
  `scripts/provision-runtime.sh`
- Release installer and update checks:
  `src/installer/release_installer.py`

## Current model

There are two distinct flows:

1. Native component install
   - downloads `llama.cpp` and `llama-swap` into the install root
   - uses install profiles under `component_settings.llama_cpp`
2. Runtime provisioning for backend variants
   - downloads or builds backend binaries into `/app/runtime-root/<runtime_subdir>/active`
   - supports multiple variants concurrently

## Runtime variant fields that matter

Release-backed variants:

- `version`
- `source_type: github_release`
- `repo_owner`
- `repo_name`
- `asset_tokens`
- `runtime_subdir`
- `macro`

Source-build variants:

- `version`
- `source_type: git`
- `git_url`
- `git_ref`
- `configure_command`
- `build_command`
- `binary_glob`
- `library_glob`

## Current enabled runtime variants

Project defaults currently enable:

- `cpu`
- `cuda`
- `rocm`
- `vulkan`
- `rocm-gfx1100-prebuilt`
- `rocm-gfx1030-prebuilt`

These all currently resolve through ggml release assets unless locally
overridden.

## Finding the latest upstream releases

Verified on 2026-04-05:

- ggml latest: `b8661`
  https://github.com/ggml-org/llama.cpp/releases/latest
- Lemonade ROCm latest: `b1199`
  https://github.com/lemonade-sdk/llamacpp-rocm/releases/latest
- llama-swap latest: `v199`
  https://github.com/mostlygeek/llama-swap/releases/latest

From the repo, use:

```bash
python -m src.installer.release_installer check-updates --root .
```

Windows wrapper:

```powershell
.\scripts\AUDiaLLMGateway.ps1 check
```

## Updating versions

### Update the AUDia release itself

```bash
python -m src.installer.release_installer update-release --root .
```

Windows wrapper:

```powershell
.\scripts\AUDiaLLMGateway.ps1 update
```

### Update all ggml-backed runtime variants together

Set the shared runtime default:

```yaml
defaults:
  version: b8661
```

or set `LLAMA_VERSION=b8661` in `.env`.

### Update one runtime variant independently

```yaml
variants:
  vulkan:
    version: b8661

  rocm:
    version: b8583
```

This is the current supported way to maintain differing backend builds at the
same time.

### Add a separate upstream lane

Example: Lemonade ROCm lane

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

Prefer a commit SHA in `git_ref`:

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

## After editing versions or variants

1. Regenerate configs:

```bash
python -m src.launcher.process_manager --root . generate-configs
```

2. Inspect the generated runtime catalog:

```bash
python -m json.tool config/generated/llama-swap/backend-runtime.catalog.json
```

3. Restart the runtime:
   - native: restart the managed processes
   - Docker: restart the backend container or compose stack

## Asset selector vocabulary

Current implementation status:

- Native install profiles still use `asset_match_tokens` in
  `config/project/stack.base.yaml`
- Runtime variants use `asset_tokens`
- The installer now accepts both names for native profiles
- The runtime provisioner accepts `asset_tokens` and still tolerates
  legacy `asset_pattern`

## What is not yet wired end-to-end

The benchmark lifecycle registry under
`benchmarks/data/backend-benchmarks/backend-version-registry.yaml` tracks
governance metadata such as `pinned_version`, but the runtime provisioner still
uses the generated runtime catalog's `version` and `git_ref` fields.

Use the registry for planning and audit context, not as proof that the running
system is already pinned to those values.
