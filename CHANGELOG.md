# Changelog

## [0.9.0](https://github.com/Audumla/AUDiaLLMGateway/compare/v0.8.0...v0.9.0) (2026-03-19)


### Features

* add detect-hardware.sh and provision Vulkan alongside all GPU backends ([2972d5b](https://github.com/Audumla/AUDiaLLMGateway/commit/2972d5b578ec40254c6f6d4829237544311bf162))
* add vLLM profiles and CPU-only compose example to all Docker configurations ([2432343](https://github.com/Audumla/AUDiaLLMGateway/commit/24323436dbab5724617099bbba66e3703410f593))
* added linux distros into support ([d81951d](https://github.com/Audumla/AUDiaLLMGateway/commit/d81951d6a0d8739293a58279dc1b58e40a929f0f))
* added proper installs ([600da16](https://github.com/Audumla/AUDiaLLMGateway/commit/600da163a34b36afc320bddf33744e28f69acc72))
* auto-seed config/local/ on first Docker run ([df78353](https://github.com/Audumla/AUDiaLLMGateway/commit/df783536c33eac7799235e0842c9d47ca38e1f15))
* docker enabled ([11fe981](https://github.com/Audumla/AUDiaLLMGateway/commit/11fe9810796725b212ee8cda906af1d8e56ea697))
* initial implementation ([23d92d9](https://github.com/Audumla/AUDiaLLMGateway/commit/23d92d9e2cebcf64ee46e3eb08b5b5f9287439c7))
* seed llama-swap.override.yaml and models.override.yaml on install ([758c6dc](https://github.com/Audumla/AUDiaLLMGateway/commit/758c6dca6ada640cbd69e6227a2aa70e5d2ad585))


### Bug Fixes

* add --project-directory . to all example compose run commands ([d2f37c8](https://github.com/Audumla/AUDiaLLMGateway/commit/d2f37c8c8866ee87b253d55639fe1a4635cdaf3b))
* add Vulkan auto-detection and proper Vulkan binary provisioning ([85803db](https://github.com/Audumla/AUDiaLLMGateway/commit/85803db485f5919adc3a4bac1ec506fbcc3c27e6))
* added llamacpp install ([c99ab35](https://github.com/Audumla/AUDiaLLMGateway/commit/c99ab35b6c64808554d7582d651c93b642bce353))
* agent release errors ([4977b4c](https://github.com/Audumla/AUDiaLLMGateway/commit/4977b4cea7e9c5681eaf11d9418e6fdb2f44adb1))
* agent syntax errors ([8a8be76](https://github.com/Audumla/AUDiaLLMGateway/commit/8a8be76978ea359c4a09dc1eb685c4d6a8faa62a))
* branch renaming ([ba46780](https://github.com/Audumla/AUDiaLLMGateway/commit/ba467807e28fd85417858576ac638430ee33088f))
* clean release ([6d51333](https://github.com/Audumla/AUDiaLLMGateway/commit/6d51333e086d50188ca2e659bde887774dbc1f0b))
* distro deployment fixes ([6d6a104](https://github.com/Audumla/AUDiaLLMGateway/commit/6d6a1047d7c35e07dc38a66266c0cb106e848f21))
* docker updates ([abe361f](https://github.com/Audumla/AUDiaLLMGateway/commit/abe361ff3aa9303de3a70c2dcddee66748949e33))
* download llamacpp versions ([7eb9782](https://github.com/Audumla/AUDiaLLMGateway/commit/7eb9782e854594b6deb0db0f4556d39beb117db5))
* explicit nfpm file list and workflow cleanup ([3b23fd7](https://github.com/Audumla/AUDiaLLMGateway/commit/3b23fd76cdf0050152dea534ccecf139dd45b653))
* expose all proxied endpoints without auth and fix redirect rewriting ([a8137e8](https://github.com/Audumla/AUDiaLLMGateway/commit/a8137e8a372bb354215c0a39a1af3b48a0e0c31e))
* force release please sync after manifest mismatch ([b0f3fbc](https://github.com/Audumla/AUDiaLLMGateway/commit/b0f3fbce01b35d944d6619575ee1cfc9306f12cc))
* inject litellm auth header in nginx and restore master_key config ([aed96a3](https://github.com/Audumla/AUDiaLLMGateway/commit/aed96a3b433528dcb387bac60b2bae674835f5f7))
* installation fixes ([2b46d50](https://github.com/Audumla/AUDiaLLMGateway/commit/2b46d50cf7c6e195f576103f75c98354525a55ff))
* lifecycle management updates ([c84ab38](https://github.com/Audumla/AUDiaLLMGateway/commit/c84ab385e73956f73e57ffd8258223187ce3c0e4))
* normalize model file paths to forward slashes for Linux compatibility ([7af3142](https://github.com/Audumla/AUDiaLLMGateway/commit/7af3142f1a02a960495a3cc276498dc2ad0c9605))
* pin backend service hosts to 127.0.0.1 in stack.base.yaml ([426a707](https://github.com/Audumla/AUDiaLLMGateway/commit/426a7074007777b31c2fb17d95adea94052edeec))
* release and install updates ([abefbfb](https://github.com/Audumla/AUDiaLLMGateway/commit/abefbfbb66ab6f496a685295c0665b927c919bda))
* release build for distro installation files ([e7e72f8](https://github.com/Audumla/AUDiaLLMGateway/commit/e7e72f8c48c8fff7a31a009955f391ad9af9131f))
* release issues ([d30bbbb](https://github.com/Audumla/AUDiaLLMGateway/commit/d30bbbb8660b20b556279951b29e311818432371))
* release issues ([c16189d](https://github.com/Audumla/AUDiaLLMGateway/commit/c16189d066e9c963a5410e5b27c5b8b11a050741))
* release issues ([a4c523a](https://github.com/Audumla/AUDiaLLMGateway/commit/a4c523abc8625d85f811d6e16dac0058adc6da73))
* release please added ([c772da7](https://github.com/Audumla/AUDiaLLMGateway/commit/c772da779f6ae7d67a19b513e40b92f885ff23a8))
* release please update ([6dde159](https://github.com/Audumla/AUDiaLLMGateway/commit/6dde159b89ede2c3b5a5921f933f491e526005b2))
* release problems ([d7eef0a](https://github.com/Audumla/AUDiaLLMGateway/commit/d7eef0a1f255ef9fba8f2cdc94b7620204acec78))
* release syntax error ([593a5fd](https://github.com/Audumla/AUDiaLLMGateway/commit/593a5fd02e0ed6b45763d0cb9e6e3224b719702a))
* release workflow indentation ([0b67664](https://github.com/Audumla/AUDiaLLMGateway/commit/0b67664ebd008420bc5aead6a5f19448b2e5a09c))
* released installation ([0dc5a85](https://github.com/Audumla/AUDiaLLMGateway/commit/0dc5a85f295b56ef07a4b4e2beedb0ddd410977e))
* remove GPU device requirements from root docker-compose.yml ([c91fe37](https://github.com/Audumla/AUDiaLLMGateway/commit/c91fe374c0807a0c3d174c215455d86ac150d7d8))
* remove master_key from litellm config to allow no_auth to take effect ([3a06c6c](https://github.com/Audumla/AUDiaLLMGateway/commit/3a06c6c7eef06b30620ca8a4cca9243eb81716c2))
* repair provision-runtime.sh and Dockerfile.gateway ([2432343](https://github.com/Audumla/AUDiaLLMGateway/commit/24323436dbab5724617099bbba66e3703410f593))
* restore native install commands and fix CI test failures ([a63cb82](https://github.com/Audumla/AUDiaLLMGateway/commit/a63cb823f885d23823fd4e98d2cec00b59f54f47))
* update branch naming ([bd5bd95](https://github.com/Audumla/AUDiaLLMGateway/commit/bd5bd95db812e49c21790e7549106cbdb3a4a1dc))
* update changelog ([97fe2e7](https://github.com/Audumla/AUDiaLLMGateway/commit/97fe2e736a0bd96d4f94f01a39410f63eee7f601))
* update configuration management ([7dc1df9](https://github.com/Audumla/AUDiaLLMGateway/commit/7dc1df9dd7544693e0f747b2f06261be47f2d3b5))
* updated documentation ([c3508f2](https://github.com/Audumla/AUDiaLLMGateway/commit/c3508f2040f241205f5f696ce29aaa35af28b9e2))
* updated install logic ([9cb9c31](https://github.com/Audumla/AUDiaLLMGateway/commit/9cb9c3119fd9da826230b7a3eceb5f43a8c59759))
* updated install scripts ([aecfd52](https://github.com/Audumla/AUDiaLLMGateway/commit/aecfd52c3b5c593445af193bad431ecc992a201d))
* use direct venv bootstrap in install stack to avoid circular import ([c982ea3](https://github.com/Audumla/AUDiaLLMGateway/commit/c982ea301abf414e445ae07aa2ab7a36c0d5d112))
* use public_host for nginx landing page links ([729a741](https://github.com/Audumla/AUDiaLLMGateway/commit/729a74142f44d9884ca6123bf1a0be02f7050dce))


### Documentation

* add missing GATEWAY_PORT, NGINX_PORT, VLLM_MAX_LEN env vars ([4cae4e5](https://github.com/Audumla/AUDiaLLMGateway/commit/4cae4e53c3f88d0dc3cfa1de078255aa3e066ab4))
* document per-backend macro override pattern in llama-swap.base.yaml ([f88177f](https://github.com/Audumla/AUDiaLLMGateway/commit/f88177f8c5c20501d0e67e88ee01b1f96616a259))
* fix Docker Hub image names in docker.md ([db59be6](https://github.com/Audumla/AUDiaLLMGateway/commit/db59be611ca5e27e40c66a35d9c85828e18b7269))
* revamp documentation and expand Docker deployment ([2432343](https://github.com/Audumla/AUDiaLLMGateway/commit/24323436dbab5724617099bbba66e3703410f593))
* update spec-002 and changelog for nginx proxy fixes ([55b3b8d](https://github.com/Audumla/AUDiaLLMGateway/commit/55b3b8d156a5adb5eaa7e0e7e8a2dbe2c38e9020))
* update specs and docs to reflect v0.6.x state ([3226c5c](https://github.com/Audumla/AUDiaLLMGateway/commit/3226c5cf3a2918323f84eec6ab5530af1f76c2d8))

## [0.8.0](https://github.com/Audumla/AUDiaLLMGateway/compare/v0.7.2...v0.8.0) (2026-03-19)


### Features

* add detect-hardware.sh and provision Vulkan alongside all GPU backends ([2972d5b](https://github.com/Audumla/AUDiaLLMGateway/commit/2972d5b578ec40254c6f6d4829237544311bf162))


### Bug Fixes

* add Vulkan auto-detection and proper Vulkan binary provisioning ([85803db](https://github.com/Audumla/AUDiaLLMGateway/commit/85803db485f5919adc3a4bac1ec506fbcc3c27e6))


### Documentation

* document per-backend macro override pattern in llama-swap.base.yaml ([f88177f](https://github.com/Audumla/AUDiaLLMGateway/commit/f88177f8c5c20501d0e67e88ee01b1f96616a259))

## [0.7.2](https://github.com/Audumla/AUDiaLLMGateway/compare/v0.7.1...v0.7.2) (2026-03-19)


### Bug Fixes

* remove GPU device requirements from root docker-compose.yml ([c91fe37](https://github.com/Audumla/AUDiaLLMGateway/commit/c91fe374c0807a0c3d174c215455d86ac150d7d8))

## [0.7.1](https://github.com/Audumla/AUDiaLLMGateway/compare/v0.7.0...v0.7.1) (2026-03-19)


### Bug Fixes

* add --project-directory . to all example compose run commands ([d2f37c8](https://github.com/Audumla/AUDiaLLMGateway/commit/d2f37c8c8866ee87b253d55639fe1a4635cdaf3b))

## [0.7.0](https://github.com/Audumla/AUDiaLLMGateway/compare/v0.6.0...v0.7.0) (2026-03-19)


### Features

* auto-seed config/local/ on first Docker run ([df78353](https://github.com/Audumla/AUDiaLLMGateway/commit/df783536c33eac7799235e0842c9d47ca38e1f15))


### Documentation

* add missing GATEWAY_PORT, NGINX_PORT, VLLM_MAX_LEN env vars ([4cae4e5](https://github.com/Audumla/AUDiaLLMGateway/commit/4cae4e53c3f88d0dc3cfa1de078255aa3e066ab4))
* fix Docker Hub image names in docker.md ([db59be6](https://github.com/Audumla/AUDiaLLMGateway/commit/db59be611ca5e27e40c66a35d9c85828e18b7269))
* update specs and docs to reflect v0.6.x state ([3226c5c](https://github.com/Audumla/AUDiaLLMGateway/commit/3226c5cf3a2918323f84eec6ab5530af1f76c2d8))

## [0.6.0](https://github.com/Audumla/AUDiaLLMGateway/compare/v0.5.2...v0.6.0) (2026-03-19)


### Features

* add vLLM profiles and CPU-only compose example to all Docker configurations ([2432343](https://github.com/Audumla/AUDiaLLMGateway/commit/24323436dbab5724617099bbba66e3703410f593))


### Bug Fixes

* repair provision-runtime.sh and Dockerfile.gateway ([2432343](https://github.com/Audumla/AUDiaLLMGateway/commit/24323436dbab5724617099bbba66e3703410f593))
* restore native install commands and fix CI test failures ([a63cb82](https://github.com/Audumla/AUDiaLLMGateway/commit/a63cb823f885d23823fd4e98d2cec00b59f54f47))
* use direct venv bootstrap in install stack to avoid circular import ([c982ea3](https://github.com/Audumla/AUDiaLLMGateway/commit/c982ea301abf414e445ae07aa2ab7a36c0d5d112))


### Documentation

* revamp documentation and expand Docker deployment ([2432343](https://github.com/Audumla/AUDiaLLMGateway/commit/24323436dbab5724617099bbba66e3703410f593))

## Changelog

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

### Fix YAML indentation in release workflow (Bug Fix)
- Corrected indentation for package job steps which caused a workflow syntax error

### Update spec-001 to include multi-GPU backend install, per-backend llama-swap macros, install-components requirement, Docker smoke tests, and e2e mock test acceptance criteria (Documentation Update)
- Added goals 11-13 covering multi-GPU variant install, full package-time dependency completion, and CI Docker test requirements
- Expanded Linux platform scope with RPM/DEB packaging, systemd service, and multi-GPU backend detail
- Added section 6 subsections for multi-GPU install, per-backend macros, and install components command
- Added section 7 Package install testing with smoke test and e2e mock test requirements
- Updated Configuration Model, Implementation Mapping, Acceptance Criteria, and Known Gaps

### Make package install fully automatic: seed LITELLM_MASTER_KEY env file, add EnvironmentFile to service unit, start service from postinstall (Build / Packaging)
- scripts/audia-gateway.service: added EnvironmentFile=-/opt/AUDiaLLMGateway/config/local/env so LITELLM_MASTER_KEY is loaded at service start
- scripts/postinstall.sh: create config/local/ and seed config/local/env with default LITELLM_MASTER_KEY=sk-local-dev if not present
- scripts/postinstall.sh: replaced set -e with explicit error handling — component download failure is non-fatal warning, stack and generate failures abort
- scripts/postinstall.sh: added systemctl start audia-gateway at end so service is running immediately after install
- tests/docker/smoke-entrypoint.sh: extended section 7 to verify EnvironmentFile directive in service unit, config/local/env creation, and LITELLM_MASTER_KEY presence

### Seed config/local/stack.override.yaml and set world-writable permissions on config/local/ so users can customise without sudo (Build / Packaging)
- scripts/postinstall.sh: create config/local/stack.override.yaml with commented examples (ports, nginx) if not present; chmod 666
- scripts/postinstall.sh: chmod 777 config/local/ so any local user can edit or add override files without sudo
- scripts/postinstall.sh: chmod 600 config/local/env to protect the master key credential
- tests/docker/smoke-entrypoint.sh: verify stack.override.yaml is seeded and has 666 permissions; verify config/local/ has 777

### Add spec-002 covering deployment-agnostic model catalog, config auto-regen, selective component reload, llama-swap watch mode, and interactive component selection (Documentation Update)
- specifications/spec-002-model-catalog-and-config-lifecycle.md: new mid-level spec
- Model catalog: formalises multi-deployment-target schema (llama_swap, vllm, unsloth, future), backend-agnostic load groups, deployment-enabled flags, framework registry in stack config
- Config lifecycle: deployment-aware generator skips frameworks not in install-state; records generate-report.json, generate-hashes.json, runtime-bindings.json
- Auto-detection: watcher polls source config mtimes, diffs generated outputs, applies per-component reload (litellm restart, nginx reload, llama-swap watch, port-change restart)
- llama-swap watch: always launched with --watch; model changes picked up without process restart; restart only for substrate-level changes
- Component selection: all components default_enabled true; interactive menu in bootstrap; persisted to config/local/components.yaml; package installs use platform-aware defaults
- Port management: watcher detects binding changes, restarts affected component, updates runtime-bindings.json; downstream configs regenerated automatically
- specifications/spec-001: updated Next Specs section to reference spec-002

### Fixed nginx reverse proxy so all endpoints are reachable from external clients. (Bug Fix)
- build_nginx_landing_page used nginx_host (bind address) instead of public_host for link hrefs — links pointed to 127.0.0.1 and failed for remote clients.
- nginx.conf server_name was 127.0.0.1 (rejected non-localhost Host headers) — changed to catch-all underscore.
- stack.base.yaml had no explicit host for litellm/llama_swap services so _detect_local_ip() resolved to LAN IP; nginx upstreams targeted 10.10.x.x while services only listened on 127.0.0.1 causing 502s.
- Added backend_bind_host: 127.0.0.1 and host: 127.0.0.1 for both backend services; all five endpoints now return 2xx through nginx on buri (10.10.100.10:8080).

### Fixed all nginx-proxied endpoints to return correct data without requiring auth. (Bug Fix)
- /v1/models and /health returned 401 — added no_auth: true to LiteLLM general_settings.
- H:/development/tools/Git/ui returned nginx 404 — added /ui/ location block proxying to litellm upstream with proxy_redirect to rewrite absolute redirects.
- H:/development/tools/Git/llamaswap/ redirect pointed to /ui (nginx 404) — added proxy_redirect to rewrite upstream Location headers to /llamaswap/ prefix.
- Added /ui/ link to nginx landing page.
- All 13 endpoints verified: correct HTTP status, data matches direct upstream on /v1/models and /llamaswap/v1/models.

### Fix nginx reverse proxy: inject litellm auth header and normalize model file paths (Bug Fix)
- nginx now reads config/local/env and injects Authorization Bearer header on all litellm-proxied routes so external callers reach the gateway without auth
- Model file paths in models.base.yaml normalized from Windows backslashes to forward slashes
- config_loader.py also normalizes backslashes at generation time for safety
- All proxied endpoints (/v1/models /health /ui/ /litellm/ /llamaswap/) now return HTTP 200

### Revamp documentation: expand docker.md, README navigation, spec-001 accuracy, architecture.md Docker topology, specs README status legend (Documentation Update)
- Rewrote docs/docker.md with full deployment guide (all 4 profiles with complete examples, port reference, env vars, troubleshooting)
- Updated README.md with navigation table, Docker quick-start path, and structured overview sections
- Rewrote spec-001 to reflect actual implemented state and removed aspirational hot-reload claims
- Expanded docs/architecture.md with Docker deployment path alongside native install topology
- Updated specifications/README.md with Implemented/Draft/Planned status legend

### Add vLLM profiles to all Docker compose examples, CPU-only example, integration test with real inference, scheduled CI workflow, and fix provision-runtime.sh GPU detection (New Feature, Test Update, Build / Packaging)
- Added vLLM as opt-in Docker profile (--profile vllm) to all 4 compose examples
- Added CPU-only compose example (docker/examples/docker-compose.cpu.yml)
- Fixed provision-runtime.sh: honors LLAMA_BACKEND env var, /dev/kfd AMD detection, cleaner provisioning flow
- Fixed Dockerfile.gateway: multi-stage build with pip prefix install, removed broken non-root user
- Added pciutils to Dockerfile.unified-backend for reliable lspci GPU detection
- Created integration test (Dockerfile.integration + integration-entrypoint.sh) with real llama.cpp inference using SmolLM2-135M
- Updated run-smoke-tests.sh to include integration target with model caching
- Rewrote tests.yml: added e2e-mock job, integration job (weekly + manual), docker-build validation job, --network=host for all builds

---
