# Changelog

## [0.2.0](https://github.com/example/AUDiaLLMGateway/compare/v0.1.0...v0.2.0) (2026-03-15)


### Features

* initial implementation ([23d92d9](https://github.com/example/AUDiaLLMGateway/commit/23d92d9e2cebcf64ee46e3eb08b5b5f9287439c7))


### Bug Fixes

* added llamacpp install ([c99ab35](https://github.com/example/AUDiaLLMGateway/commit/c99ab35b6c64808554d7582d651c93b642bce353))
* branch renaming ([ba46780](https://github.com/example/AUDiaLLMGateway/commit/ba467807e28fd85417858576ac638430ee33088f))
* release please added ([c772da7](https://github.com/example/AUDiaLLMGateway/commit/c772da779f6ae7d67a19b513e40b92f885ff23a8))
* release please update ([6dde159](https://github.com/example/AUDiaLLMGateway/commit/6dde159b89ede2c3b5a5921f933f491e526005b2))
* update branch naming ([bd5bd95](https://github.com/example/AUDiaLLMGateway/commit/bd5bd95db812e49c21790e7549106cbdb3a4a1dc))
* updated install logic ([9cb9c31](https://github.com/example/AUDiaLLMGateway/commit/9cb9c3119fd9da826230b7a3eceb5f43a8c59759))
* updated install scripts ([aecfd52](https://github.com/example/AUDiaLLMGateway/commit/aecfd52c3b5c593445af193bad431ecc992a201d))

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

### Updated AUDiaLLMGateway defaults to use the ExampleOrg/AUDiaLLMGateway GitHub repository. (Configuration Cleanup)
- Changed the release installer defaults and release manifest owner to ExampleOrg.
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

---
