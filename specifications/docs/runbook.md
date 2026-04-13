# Runbook

## Config model

Project-managed defaults live under `config/project/`.

Local machine-specific edits live under `config/local/`.

Generated files are written under `config/generated/`.

Generated outputs are grouped by component:

- `config/generated/llama-swap/`
- `config/generated/litellm/`
- `config/generated/mcp/`
- `config/generated/nginx/`

The updater replaces project-managed files from a release archive but preserves `config/local/`, `.venv/`, `.runtime/`, `.agent_runner/`, and `state/`.

## Central network bindings

Service hosts and ports should be configured once in `config/project/stack.base.yaml` under `network`.

The generated application configs then consume those values so you do not have to edit host and port literals separately in:

- LiteLLM config
- `llama-swap` server args
- nginx config
- generated local MCP client config

## Shared model catalog

The backend-agnostic model catalog now merges from:

- `config/project/models.base.yaml`
- `config/local/models.override.yaml`

This catalog is intended to hold shared model semantics that can survive backend changes, for example:

- context presets
- GPU placement presets
- runtime behavior presets
- model artifacts
- model source and download URLs
- framework deployments such as `llama_cpp` and optional `vllm`
- load groups for activities like coding, reasoning, or vision

Backend runtime binary sources are configured separately in the backend runtime
catalog:

- `config/project/backend-runtime.base.yaml`
- `config/local/backend-runtime.override.yaml`

This catalog defines downloadable/buildable backend variants (`github_release`,
`direct_url`, or `git`) and generates versioned runtime macros consumed by model
deployments.

Backend compatibility is defined in a separate backend support matrix:

- `config/project/backend-support.base.yaml`
- `config/local/backend-support.override.yaml`

This matrix is the only place that encodes model/backend compatibility (for
example, `qwen35` requiring `llama.cpp` releases at or above `b8153`). The code
does not hardcode backend-specific rules — it evaluates the matrix against the
model catalog and backend runtime catalog at generation time.

For release-based rules, set an explicit `version` on each backend variant so
the matrix can compare `b####` tags. If a variant reports `latest` or an
unknown version, the matrix uses `on_unknown`.

## Add backend variant workflow

To add a backend build variant without changing project defaults:

1. Edit `config/local/backend-runtime.override.yaml`.
2. Add reusable entries under `profiles` for source/build policy (optional but recommended).
3. Add a variant under `variants` that references one or more profiles with
   `profile` or `profiles`.
4. Choose `source_type`:
   - `github_release` for tagged GitHub release assets.
   - `direct_url` for a fixed artifact URL.
   - `git` for source build from a repository/ref.
5. Reference the variant macro from a model deployment in
   `config/local/models.override.yaml` via `executable_macro`.
6. Regenerate configs:
   - `python -m src.launcher.process_manager --root . generate-configs`
7. Restart `llm-server-llamacpp` (or let watcher restart when enabled).
8. Validate generated catalog:
   - `config/generated/llama-swap/backend-runtime.catalog.json`

Example (`gfx1100` on ROCm official preview, plus `gfx1030` on lemonade):

```yaml
profiles:
  build-rocm-gfx1030-gfx1100:
    backend: rocm
    configure_command: cmake -S . -B build -DLLAMA_BUILD_SERVER=ON -DGGML_HIPBLAS=ON -DAMDGPU_TARGETS=gfx1030;gfx1100 -DCMAKE_HIP_ARCHITECTURES=gfx1030;gfx1100 -DCMAKE_BUILD_TYPE=Release
    build_command: cmake --build build --config Release --parallel
    binary_glob: build/bin/llama-server
    library_glob: build/bin/*.so*
    apt_packages: [git, cmake, build-essential]

  source-rocm-preview:
    source_type: git
    git_url: https://github.com/ROCm/llama.cpp.git
    git_ref: rocm-7.11.0-preview

  source-lemonade:
    source_type: git
    git_url: https://github.com/lemonade-sdk/llamacpp-rocm.git
    git_ref: main

variants:
  rocm-gfx1100-preview:
    profiles: [source-rocm-preview, build-rocm-gfx1030-gfx1100]
    macro: llama-server-rocm-gfx1100-preview
    runtime_subdir: rocm/gfx1100/preview

  rocm-gfx1030-lemonade:
    profiles: [source-lemonade, build-rocm-gfx1030-gfx1100]
    macro: llama-server-rocm-gfx1030-lemonade
    runtime_subdir: rocm/gfx1030/lemonade
```

Experimental Vulkan fork example (`llama-cpp-turboquant`, pinned to upstream tag `tqp-v0.1.0` published on April 8, 2026):

```yaml
profiles:
  source-turboquant-git:
    source_type: git
    git_url: https://github.com/TheTom/llama-cpp-turboquant.git
    git_ref: tqp-v0.1.0
    version: tqp-v0.1.0

  build-vulkan-git:
    backend: vulkan
    configure_command: cmake -S . -B build -DLLAMA_BUILD_SERVER=ON -DGGML_VULKAN=ON -DCMAKE_BUILD_TYPE=Release
    build_command: cmake --build build --config Release --parallel
    binary_glob: build/bin/llama-server
    library_glob: build/bin/*.so*
    apt_packages: [git, cmake, build-essential, pkg-config]

variants:
  vulkan-turboquant:
    profiles: [source-turboquant-git, build-vulkan-git]
    macro: llama-server-vulkan-turboquant
    runtime_subdir: vulkan/turboquant
    enabled: false
```

Keep this style of forked backend variant disabled in checked-in defaults. Enable it only in your local override once you are ready to benchmark or smoke-test it on a host with working Vulkan drivers.

Context presets should use human-friendly aliases like `32k`, `64k`, or `96k`. The generator can synthesize the backend context macro from the numeric token value instead of requiring an explicit `llama-swap` macro entry for every size.

GPU and runtime presets should also be expressed in the catalog as structured `llama.cpp` option maps. The generator translates those into `llama-swap` macros, so the backend substrate does not own the preset semantics.

You can also define human-friendly device aliases once and reuse them across
GPU presets and deployments:

```yaml
presets:
  device_aliases:
    gpu_7900_a: ROCm0
    gpu_7900_b: ROCm1
    gpu_6900: ROCm2
    vk_6900: Vulkan0
    vk_7900_a: Vulkan1
    vk_7900_b: Vulkan2
```

This is the current greenfield schema. The default project config no longer carries older compatibility forms for model exposure or context naming.

`config/project/models.base.yaml` is an empty scaffold for shipped defaults.
Install-specific frameworks, presets, model entries, exposures, and load groups
belong in `config/local/models.override.yaml`. `llama-swap` project config is
only backend substrate for executable/path primitives. Project model entries,
load groups, and translated preset macros are generated from the merged catalog
rather than shipped in a separate `llama-swap` inventory.

Load groups should also be defined in the shared catalog. That allows an activity-oriented grouping such as `coding_active` or `reasoning_active` to be translated into backend-specific group mechanics like `llama-swap` persistence and swap behavior.

## Benchmarking capability

Benchmarking is separate from validation. Validation answers whether the stack
starts and routes correctly; benchmarking answers how a specific build, backend,
and settings profile performs under a controlled prompt suite.

Benchmark runs use the same shared model catalog and config overlays as the
gateway, but they write their own additive history under
`test-work/version-benchmarks/`.

Common benchmark entry points:

```powershell
python scripts/run_version_benchmarks.py
python scripts/run_backend_validation_matrix.py
```

The benchmark runner records:

- lane source and exact ref
- build profile and backend device
- toolchain/runtime version
- executable or package identity
- host hardware context
- backend/device- and route-level throughput

Keep benchmark settings in `config/project/backend-validation.base.yaml` and
model/deployment definitions in the shared model catalog. Use local overrides
only for machine-specific deployment choices or experimental lanes.

## llama.cpp install profiles

The installer manages `llama.cpp` through explicit named install profiles.

Project default:

- `config/project/stack.base.yaml`

Local override example:

```yaml
component_settings:
  llama_cpp:
    selected_profile: windows-vulkan
    profiles:
      windows-vulkan:
        version: latest
```

Current first-tier defaults:

- Windows: `windows-vulkan`
- Linux: `linux-cpu`
- macOS: `macos-metal`

Current first-tier profile matrix:

- `windows-vulkan`
- `windows-hip`
- `windows-cpu`
- `linux-vulkan`
- `linux-rocm`
- `linux-cuda`
- `linux-cpu`
- `macos-metal`
- `macos-cpu`

If you want the AMD/HIP build instead:

```yaml
component_settings:
  llama_cpp:
    selected_profile: windows-hip
    profiles:
      windows-hip:
        sidecar_files:
          - R:\tools\llama-bin-amd\libssl-3-x64.dll
          - R:\tools\llama-bin-amd\libcrypto-3-x64.dll
```

## First install from release

### Windows

```powershell
.\bootstrap\AUDiaLLMGateway-install-release.ps1 -Owner ExampleOrg -Repo AUDiaLLMGateway -InstallDir "$HOME\AUDiaLLMGateway"
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

After install, use the single Gateway command with simple actions and optional targets:

### Windows

```powershell
.\scripts\AUDiaLLMGateway.ps1 help
```

### Windows Command Prompt compatibility

```bat
.\scripts\AUDiaLLMGateway.cmd help
```

### Linux/macOS

```bash
./scripts/AUDiaLLMGateway.sh help
```

Per-action wrapper scripts are not part of the supported installed interface.

Examples:

```powershell
.\scripts\AUDiaLLMGateway.ps1 install
.\scripts\AUDiaLLMGateway.ps1 install stack
.\scripts\AUDiaLLMGateway.ps1 install llama_cpp
.\scripts\AUDiaLLMGateway.ps1 update
.\scripts\AUDiaLLMGateway.ps1 update stack
.\scripts\AUDiaLLMGateway.ps1 start
.\scripts\AUDiaLLMGateway.ps1 stop gateway
.\scripts\AUDiaLLMGateway.ps1 check
.\scripts\AUDiaLLMGateway.ps1 check status
.\scripts\AUDiaLLMGateway.ps1 validate
.\scripts\AUDiaLLMGateway.ps1 test
```

`AUDiaLLMGateway.cmd` is only a thin forwarder to the PowerShell entrypoint.

## Update from release

### Windows

```powershell
.\scripts\AUDiaLLMGateway.ps1 update
```

### Linux/macOS

```bash
./scripts/AUDiaLLMGateway.sh update
```

## Check online release availability

### Windows

```powershell
.\scripts\AUDiaLLMGateway.ps1 check
```

### Linux/macOS

```bash
./scripts/AUDiaLLMGateway.sh check
```

## Local developer setup

```powershell
.\scripts\AUDiaLLMGateway.ps1 install stack
.\scripts\AUDiaLLMGateway.ps1 generate
```

## Validate layered config

```powershell
.\scripts\AUDiaLLMGateway.ps1 validate
```

Validation reports type conflicts between project defaults and local overrides. It does not overwrite local files.

## Start the stack

```powershell
$env:LLAMA_SWAP_EXE = "C:\development\tools\llama-swap\llama-swap.exe"
$env:LITELLM_MASTER_KEY = "sk-local-dev"
.\scripts\AUDiaLLMGateway.ps1 start
```

## Stop the stack

```powershell
.\scripts\AUDiaLLMGateway.ps1 stop
```

## Health

```powershell
.\scripts\AUDiaLLMGateway.ps1 check health
.\scripts\AUDiaLLMGateway.ps1 test
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
