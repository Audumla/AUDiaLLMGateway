# Spec 001: Local LLM Gateway for Home Lab

## Spec Level

Mid-level

## Status

Draft

## Project Name

AUDiaLLMGateway

## Purpose

Define the phase 1 architecture, configuration model, operational flows, and initial delivery boundaries for a local-first LLM gateway that uses `llama-swap` as the local backend router, generated native `llama-server` profiles behind it, and LiteLLM as the OpenAI-compatible gateway layer.

This spec sits between the high-level project intent and the concrete implementation already scaffolded in this repo. It is intended to guide the next build-out steps without dropping into line-by-line implementation detail.

This spec treats Windows, Linux, and macOS as first-tier platforms in the configuration and install model, while Windows remains the first actively exercised baseline runtime.

## Goals

1. Keep native Windows `llama-server` inference as the baseline runtime behind `llama-swap`.
2. Expose multiple local models through one OpenAI-compatible LiteLLM endpoint.
3. Keep model launch configuration explicit, readable, and versioned.
4. Provide a small local orchestrator for start, stop, readiness, config generation, and release-based install/update support.
5. Keep the system easy to inspect and modify from a VS Code terminal.
6. Preserve a clear path to Linux and macOS deployment variants with different runtime choices.
7. Scaffold MCP integration without making it a phase 1 dependency.
8. Support release-archive installation and update without requiring Git on the target machine.
9. Preserve machine-local config during updates while still allowing project-managed defaults to evolve.
10. Treat `llama.cpp` as an installable, versioned runtime dependency with backend-specific variants.
11. Install all applicable GPU backend variants of `llama.cpp` in a single component install pass (CPU, ROCm, Vulkan, CUDA on Linux; Vulkan on Windows; Metal on macOS) and expose each as a named macro in the generated `llama-swap` config.
12. Guarantee that a package install (RPM or DEB) completes a fully operational deployment — including binary downloads — without requiring manual follow-up steps.
13. Verify every package install path through automated Docker-based smoke tests and end-to-end mock tests that run in CI without live GPU hardware.

## Non-Goals

1. No Docker requirement in phase 1.
2. No first-pass web UI.
3. No cloud deployment or hosted orchestration features.
4. No advanced routing logic beyond basic stable model exposure and documented future stubs.
5. No requirement that target machines install the repo through `git clone` or `git pull`.

## Platform Scope

### Windows

- Phase 1 implementation target
- Native `llama-swap` and `llama-server.exe`
- PowerShell bootstrap plus a unified installed command with simple actions and optional targets
- Windows-friendly path handling
- Existing Vulkan-based local setup remains authoritative

### Linux

- First-tier platform in config and installer design
- Expected to reuse the same high-level architecture with platform-specific bootstrap plus a unified installed command
- May use different operational options such as direct shell scripts, systemd services, or alternative backend comparisons when explicitly evaluated
- RPM and DEB package formats are the primary install mechanism for Linux targets
- Package postinstall must complete the full dependency chain: Python venv, pip packages, `llama-swap` binary, and all applicable `llama.cpp` GPU backend variants
- systemd service registration and enablement are performed during package postinstall
- Multi-GPU backend install on Linux covers CPU, Vulkan, ROCm, and CUDA profiles where available in the upstream `llama.cpp` release assets

### macOS

- First-tier platform in config and installer design
- Expected to reuse the same high-level architecture with platform-specific bootstrap plus a unified installed command
- Uses platform-specific `llama.cpp` install profiles such as Metal and CPU

## Environment Assumptions

- OS: Windows 11
- Local router runtime: `llama-swap`
- Inference runtime behind it: native `llama-server.exe`
- GPU strategy: existing Vulkan-based local setup remains authoritative
- Clients: VS Code, Codex workflows, scripts, Cline-compatible clients, and any OpenAI-compatible tool
- Hardware baseline:
  - 2 x Radeon 7900 XTX
  - 1 x Radeon 6900 XT
  - 96 GB RAM
  - Intel 12700K

## Phase 1 Architecture

Client or tool
-> LiteLLM gateway
   -> llama-swap -> local `llama-server` profiles
   -> vLLM (direct) -> local `vLLM` profiles
-> optional MCP servers later

The same logical shape is expected to hold across Windows, Linux, and macOS, even if launch mechanics and supported backend options differ.

### Layer responsibilities

#### Local backend layer

- Uses `llama-swap` as the local model router for `llama.cpp` backends
- Supports `vLLM` as a direct-to-LiteLLM backend for high-throughput or complex model deployments
- Keeps native `llama-server` launch definitions as the performance-critical layer for GGUF-based models
- Preserves explicit executable, model, port, context, and GPU launch arguments inside the `llama-swap` and `vLLM` configurations
- Remains independently debuggable outside LiteLLM
- Must allow platform-specific execution details without changing the external gateway contract

#### LiteLLM gateway layer

- Exposes a single OpenAI-compatible endpoint
- Maps stable logical model names to `llama-swap` model IDs through one backend endpoint
- Normalizes client access across tools
- Acts as the future integration point for richer routing and MCP-aware flows

#### Local orchestration layer

- Loads repo-managed stack config plus the shared model catalog
- Generates `llama-swap`, LiteLLM, and MCP client-facing config artifacts
- Starts and stops `llama-swap` and LiteLLM
- Tracks runtime metadata and logs
- Performs readiness and health checks

## Required Functional Scope

### 1. Repository structure

The project must maintain a structure close to:

- `config/`
- `docs/`
- `scripts/`
- `src/launcher/`
- `tests/`
- `specifications/`
- `install/`
- `bootstrap/`

Over time this structure should be able to accommodate:

- Windows-specific launch helpers
- Linux-specific launch helpers
- shared configuration and validation logic

### 2. Model profile support

Phase 1 must support at least:

- `qwen27_fast`
- `qwen122_smart`

Each published model must define:

- stable gateway model name
- upstream `llama-swap` model identifier
- backend model identifier used in generated LiteLLM config
- intended purpose or usage notes

The underlying generated backend config must define:

- backend executable path
- model path
- port behavior
- context size
- GPU args
- additional inference args

### 3. Stable gateway model names

The OpenAI-compatible gateway must expose:

- `local/qwen27_fast`
- `local/qwen122_smart`

These names are part of the external contract for clients and should remain stable unless intentionally versioned or deprecated.

### 4. Process orchestration

The orchestrator must support:

- start `llama-swap`
- stop `llama-swap`
- start `vLLM` instances
- stop `vLLM` instances
- start gateway
- stop gateway
- start full stack
- stop full stack
- readiness waiting
- runtime status inspection
- generated config regeneration
- layered config validation
- release-install state awareness

The orchestration approach may differ by platform:

- Windows phase 1: Python orchestration plus a unified PowerShell command using actions like `install`, `update`, `start`, `stop`, and `check`
- Linux later: Python orchestration plus a unified shell command using the same action model, systemd integration, or Docker Compose where appropriate

### 5. Health and diagnostics

The system must provide:

- `llama-swap` health probing
- gateway health probing
- end-to-end routing checks through the gateway
- runtime logs written to a local runtime folder
- process metadata written to a local runtime folder
- install/update state written to a local state file

### 6. Release-based install and update

The system must support:

- installation from GitHub release archives
- update from newer GitHub releases without Git operations
- preserving machine-local overrides during update
- automatic dependency installation for required components where supported
- automatic installation of all applicable `llama.cpp` backend variants in a single install pass
- optional component selection for non-mandatory components
- installation of newly added components on update when selected or required
- conflict validation between project defaults and local overrides

#### Multi-GPU backend install

On Linux, the component installer must download and install all applicable `llama.cpp` profiles from the upstream release in a single pass:

- `linux-cpu` — baseline CPU-only build
- `linux-vulkan` — Vulkan GPU acceleration
- `linux-rocm` — AMD ROCm GPU acceleration
- `linux-cuda` — NVIDIA CUDA GPU acceleration (when asset is available)

Each successfully installed profile is recorded in the install-state file as a named variant under `component_results.llama_cpp.variants`. A profile download failure is treated as a non-fatal warning; remaining profiles continue to install.

On Windows, the default profile is `windows-vulkan`. On macOS, `macos-metal`.

#### Per-backend llama-swap macros

After component install, the config generator must write a named macro for each installed backend variant into the generated `llama-swap` config:

- `llama-server-cpu` — path to the CPU build executable
- `llama-server-vulkan` — path to the Vulkan build executable
- `llama-server-rocm` — path to the ROCm build executable
- `llama-server-cuda` — path to the CUDA build executable

The unqualified `llama-server` macro defaults to the CPU variant when available, falling back to the first successfully installed variant. Model entries in the generated config reference the appropriate backend macro rather than a hardcoded path.

The project-managed `llama-swap.base.yaml` defines fallback values for all backend macros using the bare executable name so the system degrades gracefully when a variant was not installed.

#### `install components` command

The orchestration command surface must expose `install components` as a distinct action that:

- downloads and installs `llama-swap` and all applicable `llama.cpp` backend profiles
- writes results to the install-state file
- regenerates all derived config artifacts

Package postinstall scripts must call `install stack` (Python venv and pip dependencies) followed by `install components` (binary downloads) followed by `generate` (config generation) so that a fresh package install produces a fully operational deployment without manual follow-up.

### 7. Package install testing

The project must include automated Docker-based tests that verify the package install path without live GPU hardware or a real internet connection to binary endpoints.

#### Smoke tests

A smoke test suite must:

- build an RPM or DEB package from the current source using `nfpm`
- install the package inside a container image for each supported Linux distribution (OpenSUSE Tumbleweed, Ubuntu, Debian, Fedora, Rocky Linux)
- verify that the Python venv and pip dependencies are installed
- verify that the install-state file is written with component results for `llama-swap` and `llama-cpp`
- verify that the generated `llama-swap` config contains no platform-foreign paths
- verify that the `llama-server` macro is set in the generated config
- verify that `llama-swap` and `llama-server` are importable or callable

Binary downloads are replaced by stub executables placed at well-known PATH locations before package install. The component installer detects stub presence via `PATH` lookup and records the found path without attempting a download.

Smoke tests must be runnable locally via a shell script (`tests/docker/run-smoke-tests.sh`) and must execute in CI as part of the release workflow.

#### End-to-end mock tests

An end-to-end mock test must:

- install the package inside an Ubuntu container
- start a lightweight Python HTTP server that mimics the `llama-swap` API (`/health`, `/v1/models`, `/v1/chat/completions`)
- start `litellm` proxy against the generated config pointing at the mock server
- send an OpenAI-compatible `POST /v1/chat/completions` request through the LiteLLM endpoint
- verify the response contains a valid `choices[0].message.content` value
- verify `/v1/models` returns a non-empty model list

The end-to-end mock test is included in the CI matrix alongside the per-distro smoke tests.

#### Test isolation

All test scripts, Dockerfiles, and entrypoints must live under `tests/docker/`. Generated test artifacts (logs, output files, temporary packages) must be excluded from version control via `.gitignore`.

### 8. MCP scaffolding

Phase 1 must include:

- separate MCP configuration storage
- enable/disable flags per MCP entry
- documentation describing how MCP would be attached later
- local validation of MCP config shape at a basic level

Phase 1 does not require active MCP execution.

## Cross-Platform Direction

### Shared invariants

The following should remain consistent across Windows and Linux variants:

- stable external model names
- one OpenAI-compatible LiteLLM endpoint
- explicit `llama-swap` source model definitions
- generated `llama-swap` and LiteLLM configuration from repo-managed source data
- separate MCP registration/configuration
- health and routing diagnostics

### Platform-specific options

Windows and Linux may diverge in:

- executable naming and paths
- GPU backend flags
- shell wrapper format
- service supervision approach
- packaging and dependency installation flow
- optional containerization strategy

### Linux option set to preserve

The Linux path should remain open for later evaluation of:

- native `llama-swap` plus `llama-server` processes without containers
- Docker Compose for Linux-only deployment
- systemd-managed long-running services
- backend comparison work such as vLLM or other runtimes, if and when that becomes a deliberate phase

## Configuration Model

### Source of truth

The configuration model must separate:

- project-managed defaults shipped in releases
- machine-local overrides preserved across updates
- generated files derived from both

Project-managed stack config is the source of truth for:

- `llama-swap` runtime settings
- LiteLLM runtime settings
- network bindings for hosts and ports
- published gateway aliases
- future routing notes and fallbacks

Project-managed model catalog config is the source of truth for:

- backend-agnostic model profiles
- shared context presets
- shared GPU placement presets
- shared runtime behavior presets
- model source and download metadata
- framework-specific deployments for each model profile
- exposed aliases that should be published through LiteLLM
- load groups that describe which models should stay resident or be swapped for different activities

Project-managed `llama-swap` config is the source of truth for:

- backend execution substrate shared by generated model entries
- executable and path primitives that are not model semantics
- fallback macro values for all GPU backend names (`llama-server`, `llama-server-cpu`, `llama-server-rocm`, `llama-server-vulkan`, `llama-server-cuda`) using bare executable names so uninstalled variants degrade gracefully

The shared model catalog is authoritative for model definitions, exposures, load groups, and preset semantics such as context, GPU placement, cache, and runtime behavior. `llama-swap` model entries, groups, and preset macro bodies must be generated from that catalog rather than treated as a parallel source of truth.

The configuration model should evolve so platform-specific overrides can be added later without duplicating the entire profile set.

### Generated configuration

Generated config files are derived from the layered project plus local configuration and must remain readable enough for direct inspection.

### Separate MCP configuration

The MCP configuration layer remains separate from core runtime config so tool integration concerns do not pollute the model catalog and gateway alias definitions.

An install-state file must track:

- installed release version
- selected components
- install locations
- validation warnings
- last successful update time
- per-variant llama.cpp results including executable path and backend name for each successfully installed profile

## Current Implementation Mapping

The current scaffold already maps this spec into the following components:

- config loading and config generation in `src/launcher/config_loader.py`
- process lifecycle management in `src/launcher/process_manager.py`
- health checks in `src/launcher/health.py`
- end-to-end routing tests in `src/launcher/router_test.py`
- branded bootstrap installers in `bootstrap/`
- unified installed commands in `scripts/AUDiaLLMGateway.ps1` and `scripts/AUDiaLLMGateway.sh`
- multi-profile `llama.cpp` component installer and `install-components` subcommand in `src/installer/release_installer.py`
- per-backend macro generation in `src/launcher/config_loader.py` (`build_llama_swap_config`)
- RPM and DEB package definitions in `install/`
- Docker smoke tests for five Linux distributions in `tests/docker/`
- end-to-end mock test with LiteLLM proxy round-trip in `tests/docker/`
- operational documentation in `docs/`
- verification coverage in `tests/`

Windows is the primary development target. Linux package install (RPM/DEB) is implemented and verified via Docker-based CI smoke tests. macOS support is specification-ready but not yet exercised.

## Operational Flows

### Start flow

1. Load stack config and `llama-swap` source config.
2. Generate downstream config artifacts.
3. Start `llama-swap`.
4. Wait for `llama-swap` readiness.
5. Start LiteLLM gateway.
6. Wait for gateway readiness.

### Stop flow

1. Stop LiteLLM gateway.
2. Stop `llama-swap`.
3. Remove or refresh stale runtime metadata if needed.

### Health flow

1. Probe `llama-swap` health endpoints.
2. Probe the gateway across configured health paths.
3. Report service-level and overall stack status.

### Routing validation flow

1. Send an OpenAI-compatible chat request to the gateway.
2. Select `local/qwen27_fast`.
3. Select `local/qwen122_smart`.
4. Confirm each returns a valid chat completion response shape.

## Constraints

1. Important launch arguments must remain visible in config.
2. Windows-friendly paths must be supported cleanly.
3. The design must not block later Linux-specific wrappers and deployment options.
4. The repo must remain cloneable and editable without hidden infrastructure.
5. LiteLLM must be treated as orchestration, not the inference optimization target.
6. The design should avoid premature abstraction around routing and MCP.
7. Updates must not overwrite machine-local override files.

## Acceptance Criteria

Phase 1 is complete when:

1. One command starts `llama-swap` and the LiteLLM gateway.
2. One OpenAI-compatible endpoint can address `local/qwen27_fast` and `local/qwen122_smart`.
3. Health checks report service readiness across the full stack.
4. A similar Windows machine can run the repo after local path edits.
5. MCP support is documented and scaffolded even if not enabled in live traffic.
6. A target machine can install and update the product from GitHub releases without using Git.
7. Installing the RPM or DEB package on a supported Linux distribution completes a fully operational deployment, including `llama-swap`, all applicable `llama.cpp` GPU backend variants, and the generated `llama-swap` config.
8. Docker-based smoke tests pass for OpenSUSE Tumbleweed, Ubuntu, Debian, Fedora, and Rocky Linux in CI.
9. The end-to-end mock test passes, confirming a complete OpenAI-compatible request round-trip through LiteLLM to a mocked `llama-swap` backend.
10. The generated `llama-swap` config contains named macros for all GPU backends installed on the target platform.

Linux RPM/DEB package install is part of phase 1 acceptance. macOS support remains specification-ready but is not required for phase 1 completion.

## Known Gaps Between Spec and Live Validation

The package install path and Docker smoke tests are fully implemented and pass in CI. Live inference validation still depends on the target machine having real model files and a compatible GPU.

The implementation is currently verified for:

- config loading
- generated LiteLLM config
- health helper logic
- routing-test request logic
- script and CLI surface
- RPM/DEB package install on five Linux distributions (via Docker)
- full `install components` flow with stub binaries (via Docker)
- LiteLLM proxy round-trip against a mocked `llama-swap` backend (via Docker e2e)

Not yet verified against live local inference:

- real GGUF model loading and token generation
- per-backend GPU selection under real hardware conditions
- multi-GPU split across Vulkan, ROCm, and CUDA on the same host

## Next Specs

Likely follow-on specs:

1. Low-level `llama-swap` catalog and launch argument specification
2. Windows implementation detail specification
3. Linux deployment options and migration specification
4. vLLM runtime and integration specification
5. LiteLLM gateway behavior and routing policy specification
6. MCP integration specification
7. Observability and logging specification
