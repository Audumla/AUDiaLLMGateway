# Changelog

## Unreleased

### Scaffolded a native Windows local LLM gateway workspace in AUDiaLLMGateway. (New Feature)
- Created a Git-backed repo scaffold with config, docs, PowerShell wrappers, and Python orchestration for llama-server plus LiteLLM.
- Added health checks, routing tests, and config generation for local model profiles and future MCP registration.
- Ran py_compile, generated LiteLLM config, exercised the stop-stack wrapper, and passed pytest.

### Renamed the local LLM gateway workspace from AUDiaLLMEnvironment to AUDiaLLMGateway. (Documentation Update)
- Renamed the repo directory to AUDiaLLMGateway.
- Updated README and changelog references to the new project name.
- Re-ran tests and config generation from the renamed path.

### Added the first mid-level project spec for AUDiaLLMGateway. (Documentation Update)
- Created a specifications folder with a mid-level phase 1 gateway spec.
- Mapped the original plan to the current scaffold, config model, operational flows, and acceptance criteria.
- Kept the spec intentionally mid-level so follow-on low-level specs can expand backend, LiteLLM, and MCP details.

### Expanded spec-001 to define Windows-first scope and planned Linux options. (Documentation Update)
- Updated the mid-level spec to make Windows the active phase 1 target.
- Added Linux as a planned parallel platform with different launch and deployment options.
- Clarified that platform-specific differences should not change the external gateway contract.

### Refactored AUDiaLLMGateway to use llama-swap as the managed local backend behind LiteLLM. (New Feature)
- Replaced direct llama-server orchestration with a llama-swap runtime, generated config workflow, and LiteLLM alias publishing.
- Added a stack config, imported the provided llama-swap catalog as the repo baseline, and generated MCP client-facing config scaffolding.
- Added Windows install/update/generate scripts and updated docs/specs/tests for the new architecture.

### Moved AUDiaLLMGateway run artifacts into the Gateway workspace artifact root. (Configuration Cleanup)
- Migrated the Gateway-related codex plan-run directories out of AUDiaLLMOverseer artifact storage.
- Created the Gateway-local artifact root and confirmed no AUDiaLLMGateway run artifacts remain in the Overseer workspace.
- Re-ran pytest in AUDiaLLMGateway after the cleanup.

### Added release-based install/update, layered config preservation, install-state tracking, and component specs to AUDiaLLMGateway. (New Feature)
- Implemented a GitHub release installer/update path with bootstrap scripts for Windows, Linux, and macOS plus state tracking in state/install-state.json.
- Restructured config into project, local, and generated layers so updates preserve machine-local overrides while validation warns on conflicts.
- Added component and platform specs, installer manifest/state handling, and verified pytest, py_compile, config generation, config validation, installer help, and separation checks.

### Added versioned llama.cpp component management with backend selection to the Gateway installer model. (New Feature)
- Extended layered config and the release installer to treat llama.cpp as a managed component with backend/version settings and install-state tracking.
- Made generated llama-swap config capable of using the installed llama-server path from install state when local overrides do not replace it.
- Updated docs and specs for Windows Vulkan defaults and added installer tests for release asset selection.

### Added Windows HIP llama.cpp variant support and online release checking for managed components. (New Feature)
- Extended llama.cpp component settings to support Windows HIP asset selection and optional sidecar DLL copying for builds that need extra runtime files.
- Added check-updates commands and state reporting so gateway updates can query upstream release metadata for the gateway and llama.cpp.
- Updated docs/specs and re-verified pytest, py_compile, config generation, and installer CLI help.

### Updated AUDiaLLMGateway defaults to use the Audumla/AUDiaLLMGateway GitHub repository. (Configuration Cleanup)
- Changed the release installer defaults and release manifest owner to Audumla.
- Updated bootstrap and documentation examples to point at the real GitHub repo.
- Re-ran pytest, py_compile, and config validation after the change.

### Branded Gateway scripts are now exposed as the primary install and operations entrypoints. (Configuration Cleanup, Documentation Update)
- Added AUDiaLLMGateway-prefixed script wrappers in scripts/ and bootstrap/ for the public install/update/operations flows.
- Updated README and operational docs to use the branded script names as the default interface while preserving legacy aliases.
- Verified config validation, test suite, and strict separation checks after the rename.

### The Gateway repo now exposes a single AUDiaLLMGateway command with subcommands instead of multiple branded wrapper scripts. (Configuration Cleanup, Documentation Update)
- Added scripts/AUDiaLLMGateway.ps1 and scripts/AUDiaLLMGateway.sh as the unified command surface for install, update, config, runtime, and test actions.
- Removed the per-action AUDiaLLMGateway-* wrapper files from scripts/ and updated README and runbook examples to use subcommands.
- Verified the unified command with validate-configs and help output, and re-ran the test suite and strict separation check.

### The Gateway repo now tracks origin/main correctly instead of the stale origin/master branch. (Configuration Cleanup)
- Set the local main branch upstream to origin/main so git pull uses the correct remote branch.
- Reset origin/HEAD to main and pruned the stale origin/master remote-tracking ref.
- Verified the remote default branch and local pull/push configuration both point to main.

### The Gateway repo now exposes only the unified installed command and branded bootstrap installers. (Configuration Cleanup, Documentation Update)
- Removed the remaining unprefixed wrapper scripts from scripts/ so installed operations go through AUDiaLLMGateway.ps1 or AUDiaLLMGateway.sh.
- Removed the unprefixed bootstrap installer aliases and kept only the branded AUDiaLLMGateway bootstrap installers.
- Updated README, runbook, and platform specs to describe the single-command operational model and verified validation, tests, and separation checks.

### The Gateway command now uses simpler top-level actions with optional targets and sensible defaults. (Configuration Cleanup, Documentation Update)
- Reworked AUDiaLLMGateway.ps1 and AUDiaLLMGateway.sh to use verbs like install, update, start, stop, check, validate, test, and generate.
- Defaulted install and update to release operations while allowing secondary targets like stack, gateway, llamaswap, and future component names.
- Updated the README, runbook, troubleshooting, and mid-level spec examples and verified validation, status, tests, and separation checks.

### Added a thin Windows Command Prompt wrapper that forwards to the canonical PowerShell Gateway command. (Configuration Cleanup, Test Update, Documentation Update)
- Added scripts/AUDiaLLMGateway.cmd as a compatibility shim so Command Prompt can invoke the unified PowerShell entrypoint.
- Documented the wrapper as optional compatibility only and kept PowerShell as the canonical Windows operational interface.
- Added tests to verify the wrapper targets AUDiaLLMGateway.ps1 and re-ran cmd help, pytest, and the strict separation check.

### Added a shared backend-agnostic model catalog that translates common model settings into generated llama-swap and LiteLLM configuration. (New Feature, Documentation Update, Test Update)
- Added config/project/models.base.yaml and config/local/models.override.yaml for shared model profiles, presets, deployments, and exposed aliases.
- Updated the config loader so migrated catalog entries generate llama-swap model definitions and LiteLLM aliases while raw llama-swap config remains available for unmigrated models.
- Expanded tests and docs, then verified generate, validate, pytest, and the strict separation check.

### The shared model catalog is now the authoritative model-definition source for Gateway configuration generation. (New Feature, Documentation Update, Test Update)
- Removed stack-level published model authority and derived published model exposures from config/project/models.base.yaml and config/local/models.override.yaml.
- Updated router/test paths and docs/spec wording so the shared catalog is the master model layer while llama-swap config is treated as backend-specific runtime substrate.
- Verified generation, validation, pytest, and the strict separation check after the source-of-truth change.

### Added model source and download URL metadata to the master model catalog and generated gateway model metadata. (New Feature, Documentation Update)
- Extended the shared model catalog and PublishedModel metadata with model_url, mmproj_url, and source_page_url fields.
- Updated generated LiteLLM model_info output so source/download URLs travel with the exposed model definitions.
- Updated docs and verified generation, validation, pytest, and the strict separation check.

### Added activity-oriented load groups to the master model catalog and generated backend metadata. (New Feature, Documentation Update)
- Extended the shared model catalog with load_groups for persistent, exclusive, and swappable model sets keyed to activities like coding, reasoning, and vision.
- Updated generation so load groups become llama-swap groups and are also surfaced in LiteLLM model metadata for exposed aliases.
- Updated docs/specs and verified generation, validation, pytest, and the strict separation check.

### Replaced placeholder model URLs with exact source and artifact metadata for the current master model catalog entries. (New Feature, Documentation Update)
- Updated the shared model catalog with exact Hugging Face source pages, direct artifact URLs, revision values, filenames, and multi-shard download metadata where applicable.
- Extended generated model metadata to surface revision, filenames, and additional artifact URLs alongside the existing source/download fields.
- Verified generation, validation, pytest, and the strict separation check after the catalog metadata update.

### Added alias-based context presets that generate backend context macros from numeric token values. (New Feature, Documentation Update, Test Update)
- Updated the master model catalog to use context aliases like 32k, 64k, and 96k with template-driven llama-swap macro generation.
- Extended the generator so backend context args can be synthesized from token counts instead of requiring an explicit hard-coded macro for every size.
- Updated docs and added tests covering alias resolution and synthesized macro output, then verified generation, validation, pytest, and the strict separation check.

### Cleaned the config model to the latest greenfield schema and removed remaining default compatibility shapes. (Configuration Cleanup, Documentation Update)
- Removed the last stack-level published model fallback so the master model catalog is the only supported model-definition source.
- Removed old ctx-style aliases from the default context presets and kept the alias-first numeric context schema as the baseline format.
- Updated docs to describe the current config as greenfield and verified generation, validation, pytest, and the strict separation check.

### Updated nginx so the full LiteLLM and full llama-swap APIs are explicitly proxied through namespaced routes. (Configuration Cleanup, Documentation Update)
- Kept /v1/* mapped to LiteLLM as the primary root API and added explicit full-surface namespace handling for /litellm/* and /llamaswap/*.
- Added namespace redirects and aligned proxy headers so the same nginx front door can expose both products without path collisions.
- Updated reverse-proxy documentation and nginx spec language, then verified pytest and the strict separation check.

### Centralized service hosts and ports in stack network config and generate downstream bindings from it. (New Feature, Configuration Cleanup, Test Update)
- Added a stack-level network section for backend bind host and service hosts/ports.
- Updated config generation so llama-swap, LiteLLM, MCP client, and nginx derive bindings from the central network config.
- Removed the hard-coded server host from the llama-swap substrate and verified generation, validation, tests, and separation checks.

### Removed the shipped llama-swap model inventory so the shared catalog is the only project model-definition source. (Configuration Cleanup, Documentation Update, Test Update)
- Replaced the project llama-swap base config with a substrate-only file containing runtime macros and no project models or groups.
- Updated docs and the mid-level spec to state that the shared model catalog owns model definitions, exposures, and load groups.
- Added a test assertion to verify generated llama-swap config no longer includes the old shipped inventory and re-ran generate, validate, and pytest.

### Reworked llama.cpp selection into explicit first-tier install profiles for Windows, Linux, and macOS. (New Feature, Configuration Cleanup, Documentation Update, Test Update)
- Replaced the flat llama.cpp backend token map with explicit named install profiles and platform defaults in stack config.
- Updated the installer to resolve profiles per platform, reject wrong-platform selections, and record the selected profile in install state.
- Expanded tests and specs to cover the first-tier Windows/Linux/macOS profile matrix and verified generate, validate, pytest, and separation checks.

### Moved nginx runtime config to generated output so project-managed config no longer carries resolved host and port literals. (Configuration Cleanup, Documentation Update, Test Update)
- Changed the nginx runtime config path to config/generated/nginx/nginx.conf and removed the checked-in rendered nginx.conf file.
- Updated nginx config generation to write a generated-file header and refreshed docs and tests to use the generated path.
- Re-ran generate, validate, pytest, and separation checks to verify the central network config still drives nginx output cleanly.

### Moved llama-swap GPU and runtime arg bodies into the shared model catalog and generate backend macros from structured presets. (Configuration Cleanup, New Feature, Documentation Update, Test Update)
- Added structured llama.cpp option maps for GPU and runtime presets in the shared model catalog.
- Updated llama-swap config generation to synthesize preset macros from catalog semantics instead of keeping hard-coded macro bodies in the backend substrate.
- Removed the hard-coded preset arg bodies from the project llama-swap base file, updated specs/docs, and verified generate, validate, pytest, and separation checks.

### Removed the leftover nginx component config folder so nginx follows the same source/generated pattern as the rest of the project. (Configuration Cleanup, Documentation Update)
- Deleted the config/nginx marker folder and removed the managed-path entry for it from the project stack config.
- Kept nginx source settings in stack config and runtime output in config/generated/nginx/nginx.conf.
- Verified there are no remaining config/nginx references and re-ran validation, tests, and separation checks.

### Grouped generated outputs by component and ran a disposable local smoke test from a gitignored test-work workspace. (Configuration Cleanup, Documentation Update, Test Update)
- Moved generated llama-swap, LiteLLM, and MCP outputs into per-component folders under config/generated and updated config, docs, specs, and tests.
- Added a gitignored test-work area and used it as a disposable smoke workspace wired to the local R: model and runtime paths.
- Smoke result: llama-swap and LiteLLM reached readiness enough to expose gateway model listings, but the backend model request crashed the local llama.cpp process while loading the small Qwen model.

### Fix nginx config generation and launcher to work fully sandboxed: resolve path lookup, temp dirs, mime.types, access/error log directives (Bug Fix, Test Update)
- Remove 'include mime.types' from generated nginx.conf (pure proxy needs only default_type)
- Add explicit access_log, client_body_temp_path, proxy_temp_path, etc. directives pointing to .runtime/ so nginx runs with workspace as prefix
- Add -e <error_log_path> to nginx_command to override pre-config startup log path
- Ensure_runtime_dirs() now creates .runtime/temp/ for nginx temp file paths
- Update _resolve_exe() to expand Windows user PATH via winreg so winget-installed executables are found without shell restart
- Apply _resolve_exe to nginx_command and nginx_stop_command
- Inject llama-swap executable from install-state.json in load_stack_config when stack YAML value is unresolved env-var placeholder
- Enable nginx in component-layout-smoke workspace (was missing reverse_proxy.nginx.enabled:true); remove hardcoded llama-swap path
- Full smoke result: stages 1-5 PASS including inference via nginx :8080
- 16/16 unit tests pass

### Replace winreg exe resolution with install-state.json pattern for nginx and other externally-installed tools (Code Refactoring)
- Simplified _resolve_exe() in process_manager.py: removed Windows registry (winreg) PATH expansion, now uses venv Scripts/ + shutil.which() only
- Added nginx executable resolution in load_stack_config() using component_results.nginx.path from install-state.json, same pattern as llama-swap
- Updated docs/architecture.md: added Executable resolution section documenting the three-tier priority chain (YAML > install-state.json > fallback)
- Updated docs/reverse-proxy.md: replaced manual nginx startup example with install/start/stop commands using the process manager

### Fix installer for Linux/OpenSUSE: python3 lookup and nginx path resolution after package install (Bug Fix)
- ensure_python_runtime now tries python3 before python on Linux (OpenSUSE/Ubuntu/Debian use python3 not python)
- Added _find_nginx() helper that checks PATH and well-known system paths (/usr/sbin/nginx etc) so nginx is found after zypper/apt install even in non-login shells
- ensure_nginx raises a clear error if nginx cannot be located after install instead of silently returning empty path

### Fix three Linux installer bugs found by Docker Ubuntu smoke test, plus add docker-install-smoke workspace and Dockerfiles (Bug Fix, Test Update)
- llama.cpp asset tokens were wrong: linux-cpu used 'linux'+'x64' but ggml-org names builds 'ubuntu-x64'; fixed all linux profiles to use ubuntu-* prefix and compound tokens to avoid ambiguous matches (e.g. ubuntu-x64 vs ubuntu-vulkan-x64)
- llama-swap asset token was wrong: used 'x86_64' but mostlygeek/llama-swap names Linux builds 'linux_amd64'; fixed to ['linux','amd64']
- nginx -e flag not supported by nginx <1.19.5 (Ubuntu 22.04 ships 1.18.0); added _nginx_supports_e_flag() version check so -e is only passed when supported
- Added test-work/docker-install-smoke workspace with empty model exposures for pure installer/plumbing smoke test (stages 0-4, no inference)
- Added Dockerfiles for Ubuntu (working), OpenSUSE Leap (python310 workaround), and Tumbleweed test variants

### Fix cross-platform archive extraction and Tumbleweed Python version for smoke tests (Bug Fix, Test Update)
- Replace tarfile.open('r:*') and shutil.unpack_archive with subprocess tar on Unix to avoid Python 3.11/3.12 gzip decompressor bugs on Tumbleweed
- Switch Tumbleweed Dockerfile from python311 to python312 — litellm native extensions segfault on both 3.11 and 3.13 on Tumbleweed, 3.12 is stable
- Add _unpack() helper that uses system tar on POSIX and shutil.unpack_archive on Windows, keeping zipfile for .zip
- All 5 stages now pass on both Ubuntu 22.04 and OpenSUSE Tumbleweed Docker smoke tests
- Update _nginx_supports_e_flag() version check so nginx -e flag only used on nginx >= 1.19.5 (Ubuntu 22.04 ships 1.18.0)

### Add multi-distro Linux support: Debian, Fedora, Rocky Linux, Arch; update spec-611 (New Feature, Documentation Update, Test Update)
- Add Dockerfile.debian (Debian 12), Dockerfile.fedora (Fedora 41), Dockerfile.rocky (Rocky Linux 9) to docker-install-smoke
- Add pacman support to ensure_nginx for Arch Linux and Manjaro
- Rewrite spec-611-linux-install-and-runtime.md with full supported distros matrix, Python version notes, package manager table, and Docker smoke test reference

### Add and validate Docker smoke tests for Debian 12, Fedora 40, Rocky Linux 9, and OpenSUSE Leap 15.6; all pass stages 0-4 (Test Update)
- Debian 12: uses python:3.12-slim-bookworm base (system Python 3.11 has litellm bytecode bug)
- Fedora 40: Python 3.12 system install — PASS. Fedora 41 (Python 3.13) rejected due to SIGSEGV in litellm native ext
- Rocky Linux 9: Python 3.11 from AppStream + EPEL for nginx — PASS
- OpenSUSE Leap 15.6: python312 from default repos — PASS
- OpenSUSE Tumbleweed: python312 — PASS (already tested, python311 had tarfile gzip bug)
- Ubuntu 22.04: Python 3.10 system — PASS (already tested)
- Fixed _unpack() helper in release_installer.py to use subprocess tar on POSIX, bypassing Python gzip bugs
- Updated spec-611-linux-install-and-runtime.md with tested status, Python version caveats, and distro notes

### Add automatic systemd service file generation (New Feature)
- Generated in config/generated/systemd/ during generate-configs
- Uses absolute paths and detects local user/group

### Integrate nFPM for Linux .deb and .rpm packaging (New Feature)
- Added nfpm.yaml configuration
- Updated release-please workflow to build and upload packages
- Added scripts/postinstall.sh for automated setup

### Add vLLM runtime specification (Documentation Update)
- Created specifications/components/vllm/spec-251-vllm-runtime.md
- Updated top-level specification to include vLLM architecture
- Added vLLM placeholders to stack configuration

### Explicitly include ROCm support in vLLM specification (Documentation Update)
- Updated specifications/components/vllm/spec-251-vllm-runtime.md with ROCm hardware requirements
- Added rocm_docker_image placeholder to stack configuration
- Included ROCm deployment example in vLLM spec

### Include Vulkan support in vLLM specification (Documentation Update)
- Updated specifications/components/vllm/spec-251-vllm-runtime.md with Vulkan hardware requirements
- Added vulkan_docker_image placeholder to stack configuration
- Included Vulkan deployment example in vLLM spec

### Build and upload Windows and macOS release artifacts (New Feature)
- Updated release-please workflow to create .zip (Windows) and .tar.gz (macOS) bundles
- Ensures OS-specific downloads are available on every release

### Fix nFPM file globbing in CI (Bug Fix)
- Updated nfpm.yaml to use an explicit file list instead of ./
- Refined GitHub Actions cleanup step to avoid deleting needed files

---
