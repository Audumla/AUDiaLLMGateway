# Changelog

## [0.13.1](https://github.com/Audumla/AUDiaLLMGateway/compare/v0.13.0...v0.13.1) (2026-03-25)


### Bug Fixes

* config update ([0ed0d62](https://github.com/Audumla/AUDiaLLMGateway/commit/0ed0d62ac49e5fb061ce9cd957395018600fcdff))

## [0.13.0](https://github.com/Audumla/AUDiaLLMGateway/compare/v0.12.3...v0.13.0) (2026-03-25)


### Features

* add detect-hardware.sh and provision Vulkan alongside all GPU backends ([2972d5b](https://github.com/Audumla/AUDiaLLMGateway/commit/2972d5b578ec40254c6f6d4829237544311bf162))
* add image-only docker deployment flow ([88f0f02](https://github.com/Audumla/AUDiaLLMGateway/commit/88f0f025f1a17de4309c0118b6b792662e771161))
* add vLLM profiles and CPU-only compose example to all Docker configurations ([2432343](https://github.com/Audumla/AUDiaLLMGateway/commit/24323436dbab5724617099bbba66e3703410f593))
* added linux distros into support ([d81951d](https://github.com/Audumla/AUDiaLLMGateway/commit/d81951d6a0d8739293a58279dc1b58e40a929f0f))
* added proper installs ([600da16](https://github.com/Audumla/AUDiaLLMGateway/commit/600da163a34b36afc320bddf33744e28f69acc72))
* auto-seed config/local/ on first Docker run ([df78353](https://github.com/Audumla/AUDiaLLMGateway/commit/df783536c33eac7799235e0842c9d47ca38e1f15))
* docker enabled ([11fe981](https://github.com/Audumla/AUDiaLLMGateway/commit/11fe9810796725b212ee8cda906af1d8e56ea697))
* implement Docker auto-start for Windows ([e66bc0a](https://github.com/Audumla/AUDiaLLMGateway/commit/e66bc0a0f760329d31bf792339a7ca54bc1117e2))
* implement prebuilt binaries strategy with smart caching ([cac723a](https://github.com/Audumla/AUDiaLLMGateway/commit/cac723a6eafc78eb1b924e62d60f99c66c57b534))
* initial implementation ([23d92d9](https://github.com/Audumla/AUDiaLLMGateway/commit/23d92d9e2cebcf64ee46e3eb08b5b5f9287439c7))
* integrate docker watcher and vllm runtime flow ([5ab5a74](https://github.com/Audumla/AUDiaLLMGateway/commit/5ab5a74596ff1ac0bd0a9190965e50315364599b))
* seed llama-swap.override.yaml and models.override.yaml on install ([758c6dc](https://github.com/Audumla/AUDiaLLMGateway/commit/758c6dca6ada640cbd69e6227a2aa70e5d2ad585))


### Bug Fixes

* add --project-directory . to all example compose run commands ([d2f37c8](https://github.com/Audumla/AUDiaLLMGateway/commit/d2f37c8c8866ee87b253d55639fe1a4635cdaf3b))
* add libatomic1 to backend base image for lemonade llama.cpp binary ([cae66d8](https://github.com/Audumla/AUDiaLLMGateway/commit/cae66d89b2f83588c5e5252c69ea98db77e9ad52))
* add Vulkan auto-detection and proper Vulkan binary provisioning ([85803db](https://github.com/Audumla/AUDiaLLMGateway/commit/85803db485f5919adc3a4bac1ec506fbcc3c27e6))
* added dependancy ([fae8f6c](https://github.com/Audumla/AUDiaLLMGateway/commit/fae8f6ccca3768fe0a09f9d232129d385d27412c))
* added labels to gpus in config ([887bfed](https://github.com/Audumla/AUDiaLLMGateway/commit/887bfed61ff6fe8b8c158653086292556e30c959))
* added llamacpp install ([c99ab35](https://github.com/Audumla/AUDiaLLMGateway/commit/c99ab35b6c64808554d7582d651c93b642bce353))
* added llamacpp versioning ([4981ce2](https://github.com/Audumla/AUDiaLLMGateway/commit/4981ce2ade4ac9c435d88800b23eafcb6cecc673))
* agent release errors ([4977b4c](https://github.com/Audumla/AUDiaLLMGateway/commit/4977b4cea7e9c5681eaf11d9418e6fdb2f44adb1))
* agent syntax errors ([8a8be76](https://github.com/Audumla/AUDiaLLMGateway/commit/8a8be76978ea359c4a09dc1eb685c4d6a8faa62a))
* back end catalog management ([2a44b15](https://github.com/Audumla/AUDiaLLMGateway/commit/2a44b155884e8d4ad8cb71a5c1bf361997e97702))
* backend-aware GPU device names and Docker-explicit binary/model paths ([8c88ddb](https://github.com/Audumla/AUDiaLLMGateway/commit/8c88ddb626fa9aab229e4999353b131a2532c067))
* branch renaming ([ba46780](https://github.com/Audumla/AUDiaLLMGateway/commit/ba467807e28fd85417858576ac638430ee33088f))
* clean release ([6d51333](https://github.com/Audumla/AUDiaLLMGateway/commit/6d51333e086d50188ca2e659bde887774dbc1f0b))
* config refactor ([478561b](https://github.com/Audumla/AUDiaLLMGateway/commit/478561b97478e7f11d11385c1ae0d82cd3c4482b))
* config sync ([1ac2560](https://github.com/Audumla/AUDiaLLMGateway/commit/1ac256021e9fadb4141500e0c30c734a1f51bf9e))
* config updates ([4ec0251](https://github.com/Audumla/AUDiaLLMGateway/commit/4ec02515fc4ccb0cecbbeab5770bfb789a91e8fe))
* correct qwen3.5-27B model directory casing on Linux ([4a64b16](https://github.com/Audumla/AUDiaLLMGateway/commit/4a64b1605962c1a80d4c09a7d65b5a8eb11fb82a))
* device_aliases NameError and Docker-aware nginx static root ([03a31ef](https://github.com/Audumla/AUDiaLLMGateway/commit/03a31ef84f4d6718d45894b10d40cb1510a744fb))
* distro deployment fixes ([6d6a104](https://github.com/Audumla/AUDiaLLMGateway/commit/6d6a1047d7c35e07dc38a66266c0cb106e848f21))
* docker updates ([abe361f](https://github.com/Audumla/AUDiaLLMGateway/commit/abe361ff3aa9303de3a70c2dcddee66748949e33))
* download llamacpp versions ([7eb9782](https://github.com/Audumla/AUDiaLLMGateway/commit/7eb9782e854594b6deb0db0f4556d39beb117db5))
* downloads to docker configured locations ([695a9ad](https://github.com/Audumla/AUDiaLLMGateway/commit/695a9ad8c7d49797cf71df65e2321390d01c716a))
* explicit nfpm file list and workflow cleanup ([3b23fd7](https://github.com/Audumla/AUDiaLLMGateway/commit/3b23fd76cdf0050152dea534ccecf139dd45b653))
* expose all proxied endpoints without auth and fix redirect rewriting ([a8137e8](https://github.com/Audumla/AUDiaLLMGateway/commit/a8137e8a372bb354215c0a39a1af3b48a0e0c31e))
* force release please sync after manifest mismatch ([b0f3fbc](https://github.com/Audumla/AUDiaLLMGateway/commit/b0f3fbce01b35d944d6619575ee1cfc9306f12cc))
* gateway dashboard ([8afa380](https://github.com/Audumla/AUDiaLLMGateway/commit/8afa380193fbe157c2fad6d62a5caf39b4b2d706))
* include detect-hardware.sh in gateway image ([9c6d4c6](https://github.com/Audumla/AUDiaLLMGateway/commit/9c6d4c6a1144f98de6d348788522b6b30bb38961))
* inject litellm auth header in nginx and restore master_key config ([aed96a3](https://github.com/Audumla/AUDiaLLMGateway/commit/aed96a3b433528dcb387bac60b2bae674835f5f7))
* installation fixes ([2b46d50](https://github.com/Audumla/AUDiaLLMGateway/commit/2b46d50cf7c6e195f576103f75c98354525a55ff))
* lifecycle management updates ([c84ab38](https://github.com/Audumla/AUDiaLLMGateway/commit/c84ab385e73956f73e57ffd8258223187ce3c0e4))
* litellm db broken ([3374b1f](https://github.com/Audumla/AUDiaLLMGateway/commit/3374b1f0adbe035376fa813c875aa93342f8ec6e))
* litellma db backend ([2cecd1c](https://github.com/Audumla/AUDiaLLMGateway/commit/2cecd1ce72413db40c014a3880143e2d32312c14))
* llamacpp backend rules and expansion ([e06e3f4](https://github.com/Audumla/AUDiaLLMGateway/commit/e06e3f4f786151e33e574c5f98e6ee7531e43906))
* llamacpp fixes ([65ddfc4](https://github.com/Audumla/AUDiaLLMGateway/commit/65ddfc41e46863c7245a5a307b9e4947ee8e22e8))
* mount only config/local and config/generated, not entire config/ ([c10958f](https://github.com/Audumla/AUDiaLLMGateway/commit/c10958f76ddf3bcc18166282f64f6309790fca44))
* new tests ([5021cf7](https://github.com/Audumla/AUDiaLLMGateway/commit/5021cf71a30202c731102e493d7f0c20e2f5c29f))
* nginx health prefix route and Docker DNS resolver ([0365d86](https://github.com/Audumla/AUDiaLLMGateway/commit/0365d866f419e4ab0303c81d8176ee9565b7d072))
* normalize model file paths to forward slashes for Linux compatibility ([7af3142](https://github.com/Audumla/AUDiaLLMGateway/commit/7af3142f1a02a960495a3cc276498dc2ad0c9605))
* pass $http_host to upstream so LiteLLM builds correct redirect URLs ([f450079](https://github.com/Audumla/AUDiaLLMGateway/commit/f450079ff0449f3f59e6828cd888031ed9a0cd50))
* pin backend service hosts to 127.0.0.1 in stack.base.yaml ([426a707](https://github.com/Audumla/AUDiaLLMGateway/commit/426a7074007777b31c2fb17d95adea94052edeec))
* proxy /litellm-asset-prefix/ through nginx for UI assets ([b5e99e9](https://github.com/Audumla/AUDiaLLMGateway/commit/b5e99e91338e9d9d1e43aca9eb0f36c3e4fbbd04))
* reduce logs ([8fdcdd8](https://github.com/Audumla/AUDiaLLMGateway/commit/8fdcdd86b4ce1229b3493d37334cbc2d94a7d526))
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
* rename component ([87cfa20](https://github.com/Audumla/AUDiaLLMGateway/commit/87cfa204611910751e68388184a640b0a328fc12))
* repair provision-runtime.sh and Dockerfile.gateway ([2432343](https://github.com/Audumla/AUDiaLLMGateway/commit/24323436dbab5724617099bbba66e3703410f593))
* resolve docker compose boot issues and server configuration ([6335d9b](https://github.com/Audumla/AUDiaLLMGateway/commit/6335d9b0380888c96a780649c06997e0ef426c5d))
* restore native install commands and fix CI test failures ([a63cb82](https://github.com/Audumla/AUDiaLLMGateway/commit/a63cb823f885d23823fd4e98d2cec00b59f54f47))
* serve nginx index.html from mounted /app/static volume ([37b7b94](https://github.com/Audumla/AUDiaLLMGateway/commit/37b7b94284b521c477511b8c9a5bdd496ce2ebb1))
* symlink ggml backend plugins into bin dir and auto-set AMD Vulkan ICD ([3d26a3e](https://github.com/Audumla/AUDiaLLMGateway/commit/3d26a3e4a2ffd12c0bfb2c01a28f0444e986f11d))
* three Docker startup failures on AMD/SELinux systems ([27e4858](https://github.com/Audumla/AUDiaLLMGateway/commit/27e485833ec7c947f1f0fdb4a3a876f94036a741))
* update branch naming ([bd5bd95](https://github.com/Audumla/AUDiaLLMGateway/commit/bd5bd95db812e49c21790e7549106cbdb3a4a1dc))
* update changelog ([97fe2e7](https://github.com/Audumla/AUDiaLLMGateway/commit/97fe2e736a0bd96d4f94f01a39410f63eee7f601))
* update configuration management ([7dc1df9](https://github.com/Audumla/AUDiaLLMGateway/commit/7dc1df9dd7544693e0f747b2f06261be47f2d3b5))
* update litellm for db backend ([ced2fd9](https://github.com/Audumla/AUDiaLLMGateway/commit/ced2fd9dfeb0c0de1bb78ffd20db6883a149a98b))
* updated ([3e614a2](https://github.com/Audumla/AUDiaLLMGateway/commit/3e614a2e9664ba3ddf863b089f3db3c8ffe2610d))
* updated documentation ([c3508f2](https://github.com/Audumla/AUDiaLLMGateway/commit/c3508f2040f241205f5f696ce29aaa35af28b9e2))
* updated install logic ([9cb9c31](https://github.com/Audumla/AUDiaLLMGateway/commit/9cb9c3119fd9da826230b7a3eceb5f43a8c59759))
* updated install scripts ([aecfd52](https://github.com/Audumla/AUDiaLLMGateway/commit/aecfd52c3b5c593445af193bad431ecc992a201d))
* updated ngnix config ([ac28065](https://github.com/Audumla/AUDiaLLMGateway/commit/ac28065eb261c1616f43ff532ea447fb0b6ab3fa))
* use /health/liveliness for gateway healthcheck ([2beb80e](https://github.com/Audumla/AUDiaLLMGateway/commit/2beb80e356bbfba74c3f77f31e61843d6eb260b6))
* use /tmp paths in generated nginx.conf ([a60424f](https://github.com/Audumla/AUDiaLLMGateway/commit/a60424f94cbfb1e8b010025c61c95e1e50d2eb9e))
* use direct venv bootstrap in install stack to avoid circular import ([c982ea3](https://github.com/Audumla/AUDiaLLMGateway/commit/c982ea301abf414e445ae07aa2ab7a36c0d5d112))
* use public_host for nginx landing page links ([729a741](https://github.com/Audumla/AUDiaLLMGateway/commit/729a74142f44d9884ca6123bf1a0be02f7050dce))
* use relative hrefs in nginx landing page ([1baf2c5](https://github.com/Audumla/AUDiaLLMGateway/commit/1baf2c5c66921efdf43c21ffe08ed6eadc71826f))


### Documentation

* add comprehensive llama.cpp backend versions reference ([8a5624b](https://github.com/Audumla/AUDiaLLMGateway/commit/8a5624bdf3f1d9088419c76ae4e7ab4335686301))
* add missing GATEWAY_PORT, NGINX_PORT, VLLM_MAX_LEN env vars ([4cae4e5](https://github.com/Audumla/AUDiaLLMGateway/commit/4cae4e53c3f88d0dc3cfa1de078255aa3e066ab4))
* add step-by-step manual testing instructions for phases 2-4 ([2191577](https://github.com/Audumla/AUDiaLLMGateway/commit/21915779cf395b89472f21a480badd118b6bd6c3))
* add testing complete summary with quick reference ([551309a](https://github.com/Audumla/AUDiaLLMGateway/commit/551309ab1bd4c02c2bd559950f5e2af438e2c12f))
* document per-backend macro override pattern in llama-swap.base.yaml ([f88177f](https://github.com/Audumla/AUDiaLLMGateway/commit/f88177f8c5c20501d0e67e88ee01b1f96616a259))
* fix Docker Hub image names in docker.md ([db59be6](https://github.com/Audumla/AUDiaLLMGateway/commit/db59be611ca5e27e40c66a35d9c85828e18b7269))
* incorporate all features and fixes into specs and documentation ([36b5867](https://github.com/Audumla/AUDiaLLMGateway/commit/36b5867f25b6101da1c26dfccc9a7147ac49fd92))
* record changelog entries for GPU backend and config fixes ([061d7d1](https://github.com/Audumla/AUDiaLLMGateway/commit/061d7d1a078f9d08e03ca2917ebd0b01fa2e47a7))
* revamp documentation and expand Docker deployment ([2432343](https://github.com/Audumla/AUDiaLLMGateway/commit/24323436dbab5724617099bbba66e3703410f593))
* update nginx and vLLM specs for health prefix route and compose profiles ([77dbbd4](https://github.com/Audumla/AUDiaLLMGateway/commit/77dbbd4c223449e9817d31f5a0b06ea988cd5010))
* update spec-002 and changelog for nginx proxy fixes ([55b3b8d](https://github.com/Audumla/AUDiaLLMGateway/commit/55b3b8d156a5adb5eaa7e0e7e8a2dbe2c38e9020))
* update specs and docs to reflect v0.6.x state ([3226c5c](https://github.com/Audumla/AUDiaLLMGateway/commit/3226c5cf3a2918323f84eec6ab5530af1f76c2d8))

## [0.12.2](https://github.com/Audumla/AUDiaLLMGateway/compare/v0.12.1...v0.12.2) (2026-03-22)


### Bug Fixes

* added labels to gpus in config ([887bfed](https://github.com/Audumla/AUDiaLLMGateway/commit/887bfed61ff6fe8b8c158653086292556e30c959))

## Changelog

## Unreleased

### Implemented prebuilt binaries strategy with smart caching for all llama.cpp backends. (Performance Improvement)

- Replaced failing custom Git-based builds with prebuilt releases from ggml-org
- Implemented smart caching mechanism (always: false) — binaries downloaded once per version change, reused on subsequent restarts
- Reduced boot time from 30-60 minutes to 45-90 seconds (30-60x improvement)
- Enabled all 6 backend variants: CPU, CUDA, ROCm, Vulkan, ROCm GFX1100 (prebuilt), ROCm GFX1030 (prebuilt)
- Fixed ROCm Git branch references: main → master for fallback custom builds
- Added comprehensive documentation: PREBUILT_BINARIES_STRATEGY.md, BACKEND_VERSIONS.md, FAILING_BUILDS_INVESTIGATION.md
- Cache location: config/data/backend-runtime/ — inspectable, backupable, clearable per backend

### Implemented Windows auto-start with Task Scheduler integration. (New Feature)

- Created one-command setup script (setup-autostart.bat) for Windows system boot auto-start
- Configured Task Scheduler trigger at user logon with intelligent retry logic
- Services auto-start: PostgreSQL, llama-cpp, Gateway, nginx — approximately 90 seconds from login to ready
- Added complete setup guide (SETUP_AUTOSTART.md) and 4-phase testing framework (TEST_AUTOSTART.md, MANUAL_TESTING_INSTRUCTIONS.md)
- Startup scripts: startup-audia-gateway.bat, register-startup-task.ps1 with error handling and logging

### Enhanced backend configuration with health checks and explicit backend selection. (Build / Packaging)

- Added health check to docker-compose.yml for llama-cpp container (30s interval, 60s start period)
- Changed default LLAMA_BACKEND from auto to explicit vulkan for predictable behavior
- Added environment variables for cache and build directories (BACKEND_RUNTIME_ROOT, BACKEND_BUILD_ROOT)
- Updated docker-compose to support AMD Radeon GPU via VK_ICD_FILENAMES

### Comprehensive documentation of all supported features and backends. (Documentation Update)

- Created SUPPORTED_FEATURES.md: Executive summary of 6 backends, smart caching, auto-start, testing, health checks
- Created SUPPORTED_FEATURES.md with complete reference tables, configuration examples, performance metrics
- Updated README.md with new documentation index and references to prebuilt strategy
- Documented all 4 previously failing backend builds with solutions and status

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

### Make Docker first-run LiteLLM admin login use the seeded default master key consistently. (Build / Packaging)
- docker/gateway-entrypoint.sh: export LITELLM_MASTER_KEY from config/local/env when Compose or the host did not inject one, so first-run admin login works with the seeded key.
- docker/examples/docker-compose.nvidia.yml, docker/examples/docker-compose.amd.yml, and docker/examples/docker-compose.external-proxy.yml: add sk-local-dev fallbacks to match the root compose behavior.
- README.md and docs/docker.md: document the default admin login (admin / sk-local-dev) and clarify that LITELLM_MASTER_KEY defaults on Docker first install.

### Add publishable Docker base images so gateway and backend rebuilds can reuse heavy layers in CI and Docker Hub. (Build / Packaging)
- docker/Dockerfile.gateway-base and docker/Dockerfile.backend-base: add reusable base images for gateway Python dependencies and backend runtime prerequisites including llama-swap.
- docker/Dockerfile.gateway and docker/Dockerfile.unified-backend: switch final images to ARG-driven FROM lines so release builds can pin published base image tags.
- .github/workflows/release-please.yml and .github/workflows/tests.yml: build/push base images first, then build final images against those base tags for faster CI and Docker Hub publishing.
- docs/docker.md: document the local build order for base images and final images.

### Fix the nginx config f-string in config_loader so the Python module imports and tests run again. (Bug Fix)
- src/launcher/config_loader.py: escape the /ui/ location brace inside the generated nginx f-string so the file is valid Python.
- tests/test_backend_runtime_startup.py: update the backend base-image assertion to match the new GitHub API-based llama-swap asset resolution.
- Validated with py_compile plus pytest for the non-Docker test suite.

### Hardened Docker watcher reload behavior and verified proxy parity end to end. (Bug Fix, Build / Packaging, Test Update)
- Switched the watcher to prefer a polling observer in Docker, added AUDIA_DOCKER=true on the watcher service, and disabled the inherited gateway healthcheck for the watcher container.
- Added a LiteLLM config wait loop in docker/gateway-entrypoint.sh to avoid transient startup failures when generated config files are briefly absent during restarts.
- Validated Docker builds, compose startup, watcher-driven config regeneration, and direct-versus-nginx endpoint parity for LiteLLM and llama-swap.

### Integrated vLLM into generated routing, Docker runtime, watcher reloads, and project documentation. (New Feature, Build / Packaging, Documentation Update, Test Update)
- Added deployment-aware LiteLLM/vLLM config generation, nginx /vllm proxy routes, a vLLM runtime wrapper, and watcher-managed vLLM restarts.
- Updated root and example compose files plus env/docs/specs to use AUDIA_ENABLE_VLLM and VLLM_* settings consistently.
- Validated the end-to-end Docker flow with a mock audia-vllm container, including proxy parity and watcher-driven config regeneration/restart behavior.

### Added an image-only Docker deployment flow, published the vLLM wrapper image, and verified a clean remote Compose install. (Build / Packaging, Documentation Update, Test Update)
- Added docker/Dockerfile.vllm and docker-compose.dev.yml, converted the root deployment compose to image-only, and updated docs/workflows to match.
- Synced only docker-compose.yml to the remote host at /opt/docker/services/llm_gateway, keeping the machine free of git checkouts or extra source files.
- Validated nginx proxy parity against LiteLLM and llama-swap on 10.10.100.10 and verified watcher regeneration plus nginx reload after fixing SELinux access for the Docker socket.

### Configured the remote gateway host to persistently expose the NTFS-backed model store to the llm_gateway Docker stack. (Configuration Cleanup)
- Mounted NTFS volume UUID 681E56C51E568C46 at /mnt/stuff via /etc/fstab on 10.10.100.10.
- Bound /mnt/stuff/development/llm-models onto /opt/docker/services/llm_gateway/models after verifying a host symlink did not surface model contents inside Docker.
- Recreated audia-llama-cpp and verified /app/models contains the expected model directories.

### Mounted the secondary NTFS partition persistently at /mnt/vault on the remote gateway host. (Configuration Cleanup)
- Added UUID=F2CCA3DBCCA397FD /mnt/vault ntfs entry to /etc/fstab on 10.10.100.10.
- Created /mnt/vault and mounted the volume immediately.
- Verified mount with findmnt and directory listing.

### Published backend-swappable llama-swap port to the host for external testing. (Configuration Cleanup)
- Patched /opt/docker/services/llm_gateway/docker-compose.yml on 10.10.100.10 to add ${LLAMA_SWAP_PORT:-41080}:41080 under backend-swappable.
- Recreated audia-llama-cpp and verified compose now reports 0.0.0.0:41080->41080/tcp.
- Confirmed host listener with ss and successful HTTP response from localhost:41080.

### Disabled audia-gateway Docker health polling to stop repetitive /health/liveliness access logs. (Configuration Cleanup)
- Patched /opt/docker/services/llm_gateway/docker-compose.yml on 10.10.100.10: gateway healthcheck set to disable:true.
- Adjusted nginx depends_on condition from service_healthy to service_started for compose compatibility without health checks.
- Recreated audia-gateway and verified docker inspect reports Test=[NONE] and recent logs no longer contain the periodic liveliness GET entries.

### Enabled AMD GPU device passthrough for backend-swappable on the remote Docker host. (Configuration Cleanup)
- Patched /opt/docker/services/llm_gateway/docker-compose.yml backend-swappable with devices /dev/kfd and /dev/dri.
- Added numeric group_add entries 482 and 485 after named groups failed under Docker.
- Recreated audia-llama-cpp and verified HostConfig.Devices plus /dev/kfd and /dev/dri visibility inside the container.

### Cleaned remote default config overrides and split GGUF model storage from vLLM/HuggingFace cache paths. (Configuration Cleanup)
- Moved existing model directories into /mnt/stuff/development/llm-models/gguf and added /mnt/stuff/development/llm-models/hf-cache.
- Updated /etc/fstab bind mounts to map /opt/docker/services/llm_gateway/models -> gguf and /opt/docker/services/llm_gateway/models-hf -> hf-cache.
- Patched remote docker-compose to use MODEL_HF_ROOT for backend-vllm cache and repaired gateway service block after prior edits.
- Reset config/local/models.override.yaml to a clean empty override template and regenerated configs with vLLM gpu_memory_utilization=1.0.

### Restored primary models bind root to llm-models and moved gguf/hf separation into MODEL_ROOT subpaths. (Configuration Cleanup)
- Changed /etc/fstab so /opt/docker/services/llm_gateway/models binds to /mnt/stuff/development/llm-models (primary root).
- Set MODEL_ROOT=./models/gguf and MODEL_HF_ROOT=./models/hf-cache in remote .env to preserve separated storage layout without changing the primary link root.
- Recreated backend/gateway/watcher and verified backend-swappable mount source /opt/docker/services/llm_gateway/models/gguf -> /app/models.

### Promoted the full model catalog into local models.override.yaml for host-local editability. (Configuration Cleanup)
- Backed up existing /opt/docker/services/llm_gateway/config/local/models.override.yaml and replaced it with model_profiles, exposures, and load_groups from the active base catalog in the gateway container.
- Regenerated generated configs after promotion.
- Verified local catalog now contains 5 model profiles, 5 exposures, and 4 load groups.

### Shifted primary model definitions to local config and seeded a tiny downloadable GGUF test model. (Configuration Cleanup)
- Created local empty-base catalog (frameworks/presets only, zero model declarations) and pointed stack override models.project_config_path to it.
- Kept primary model definitions in config/local/models.override.yaml and added tiny_qwen25_test exposure/deployment.
- Downloaded Qwen2.5-0.5B-Instruct-Q4_K_M.gguf (~380MB) into models/gguf and regenerated configs to confirm model wiring.

### Moved model declarations out of project base catalog into local override. (Configuration Cleanup)
- Removed concrete model profiles/exposures/load groups from config/project/models.base.yaml
- Added full model declarations to config/local/models.override.yaml
- Validated config generation after merge-layer changes

### Moved remaining model catalog defaults from project base into local override. (Configuration Cleanup)
- Set config/project/models.base.yaml to empty scaffold only
- Moved frameworks and presets into config/local/models.override.yaml
- Regenerated all generated configs successfully

### Validated the live Docker stack end-to-end, fixed runtime/config drift, and updated docs for AMD/vLLM behavior. (Bug Fix)
- Patched runtime provisioning to resync ggml backend plugins so persisted llama.cpp volumes stay runnable across container restarts.
- Aligned model-catalog docs with install-local overrides and updated nginx/vLLM documentation to match the validated routing and cache layout.
- Normalized vLLM defaults to MODEL_HF_ROOT plus VLLM_GPU_MEM=1.0 and added python3 fallback handling in the vLLM entrypoint.

### Validated and documented the working AMD ROCm vLLM path, and repaired live llama.cpp runtime assumptions found during deep E2E testing. (Bug Fix)
- Validated the official ROCm vLLM image on the AMD host and updated the AMD compose example/docs/spec to match the path that actually works end-to-end.
- Confirmed the nginx proxy path for vLLM after reload and verified tiny GGUF inference again through LiteLLM and nginx after restoring runtime plugin symlinks and correcting the live model-root assumption.

### Persist llama.cpp runtime to visible host paths via BACKEND_RUNTIME_ROOT and update Docker docs/examples. (Configuration Cleanup)
- Replaced the opaque backend-runtime Docker volume with a bind mount rooted at ./config/data/backend-runtime across the main and example compose files.
- Documented BACKEND_RUNTIME_ROOT and the visible persistence layout in README and docs/docker.md, and kept models-hf separate for vLLM caches.

### Auto-resolve backend-specific llama.cpp runtime subdirectories under BACKEND_RUNTIME_ROOT and update Docker docs/examples. (Configuration Cleanup)
- Changed the backend provisioner to mount a runtime base path at /app/runtime-root and symlink /app/runtime to a backend-specific subdirectory such as vulkan, rocm, cpu, or auto.
- Updated compose files and docs so BACKEND_RUNTIME_ROOT is treated as a visible base directory instead of a single shared runtime path.

### Align compose examples, generated Docker hostnames, and docs with the llm-gateway / llm-server-* naming convention. (Configuration Cleanup)
- Renamed compose services to llm-gateway, llm-server-llamacpp, llm-server-vllm, and llm-config-watcher while keeping the existing audia-* container_name values.
- Updated Docker-specific hostnames in config generation plus the docs/specs/commands so examples and generated routing use the same service names.

### Add guided Docker setup, capture resolved deployment issues in field notes, and harden the generic Docker install path. (Configuration Cleanup)
- Added scripts/docker-setup.sh and AUDiaLLMGateway.sh docker setup to detect hardware, prompt for Docker settings, write .env, and create visible runtime/model/cache directories.
- Documented the resolved AMD/Linux Docker failure modes, validated versions, backend-specific runtime layout, and bottom-up debugging path in docs/docker-field-notes.md while removing a host-specific GID from the generic compose.

### Suppress successful gateway liveliness access logs while preserving failed health probes and normal request logging. (Configuration Cleanup)
- Added a custom uvicorn access-log filter and log-config JSON, then wired the gateway entrypoint to launch LiteLLM with that log config.
- Successful GET /health/liveliness 200 probes are now suppressed, while non-200 health responses and all non-health requests still appear in the logs.

### Enable DB-backed LiteLLM UI in the gateway image by bundling Prisma and generating the LiteLLM client during the Docker build. (Build / Packaging)
- Added prisma==0.15.0 to gateway Python dependencies and updated docker/Dockerfile.gateway-base to run prisma generate against LiteLLM's bundled schema.prisma during image build.
- Removed the empty model_group_alias_map emission to eliminate the non-fatal LiteLLM Router warning while keeping the Postgres-backed default compose path intact.

### Hardened the gateway DB-backed startup path so LiteLLM waits for PostgreSQL before Prisma migration. (Bug Fix)
- Patched docker/gateway-entrypoint.sh to wait on DATABASE_URL reachability and launch LiteLLM with enforced Prisma migration checks.
- Documented DATABASE_WAIT_SECONDS and DATABASE_WAIT_INTERVAL_SECONDS plus the Postgres init race in the Docker docs and field notes.

### Unified the AMD Docker example so Vulkan and ROCm usage live in the same config. (Documentation Update)
- Updated docker/examples/docker-compose.amd.yml to use LLAMA_BACKEND for Vulkan or ROCm while keeping vLLM ROCm-only.
- Updated README, docs/docker.md, and spec-001 to point to the single AMD example and show both backend commands.

### Added backend-aware GPU preset resolution and hardened llama.cpp runtime dependencies. (Bug Fix)
- Generator now supports backend-specific GPU macro synthesis so logical presets like gpu1 can resolve differently for Vulkan and ROCm deployments.
- Backend startup now re-checks container-level Vulkan and NUMA packages on every start instead of assuming persisted runtime volumes include system libraries.
- Backend base image now carries the ROCm shared libraries needed for llama-server-rocm, and the AMD compose/docs were updated for mixed-backend auto provisioning.

### Bundled rocBLAS data files into the backend image for durable ROCm startup. (Bug Fix)
- Backend base image now copies /opt/rocm/lib/rocblas so ROCm devices do not fail on missing TensileLibrary.dat after fresh deploys.
- Runtime startup now exports ROCBLAS_TENSILE_LIBPATH by default to the bundled rocBLAS library directory.
- Field notes now document the rocBLAS data requirement that caused gfx1100 startup failures.

### Simplified backend runtime layout to one directory per llama.cpp backend. (Configuration Cleanup)
- Removed the shared runtime namespace concept and now provision cpu, cuda, rocm, and vulkan into sibling directories under BACKEND_RUNTIME_ROOT.
- Docker-side backend macros now point directly at backend-specific binary paths and env wrappers instead of /app/runtime symlinks.
- Updated docs, templates, and tests to match the per-backend runtime directory model.

### Add model-catalog-driven vLLM startup/split configuration. (New Feature, Documentation Update, Test Update)
- Support vLLM startup overrides in models.override.yaml at defaults.vllm and deployments.<name>.vllm.
- Emit tensor/pipeline split and related startup fields into generated vllm.config.json with env fallback compatibility.
- Update vLLM entrypoint to pass split/runtime flags and optional HIP_VISIBLE_DEVICES from generated config.
- Document and seed new VLLM_* env variables and add tests for generated vLLM config behavior.

### Add preset-based vLLM split profiles in model catalog. (New Feature, Documentation Update, Test Update)
- Support presets.vllm_profiles with vllm_preset/vllm_presets selectors on vLLM deployments.
- Keep precedence defaults<deployment<exposure and allow direct vllm overrides over preset values.
- Document vLLM preset usage and add regression tests for preset-driven tensor/pipeline split config.

### Unify backend-specific GPU split settings under shared gpu_profiles. (Configuration Cleanup, New Feature, Documentation Update, Test Update)
- Add new backend-keyed gpu profile schema using llamacpp-<backend> and vllm-<backend> blocks.
- Use gpu_preset in vLLM path so a single profile name can drive both llama.cpp and vLLM split behavior.
- Keep backward compatibility with legacy llama_cpp_options and llama_cpp_options_by_backend.
- Update defaults/docs and add regression tests for vLLM gpu profile backend block resolution.

### Refactor model catalog to deployment-profile-first layout and update active config. (Configuration Cleanup, Code Refactoring, Test Update)
- Add deployment profile resolution and merging across model generation, exposures, groups, and vLLM startup config.
- Update config/local/models.override.yaml to deployment_profiles and remove gpu_preset dependencies from active model deployments.
- Adjust tests to assert deployment-profile-generated llama.cpp args and vLLM deployment profile precedence behavior.

### Fixed watcher resilience, llama-swap/nginx timeout behavior, and ROCm/Vulkan profile validation with live server verification. (Bug Fix, Configuration Cleanup, Documentation Update)
- Hardened config regeneration path and live reload behavior for override edits.
- Fixed llama.cpp flash-attn arg rendering for YAML boolean values and corrected default model/runtime mappings.
- Validated full nginx -> LiteLLM -> llama-swap matrix on 10.10.100.10 and documented ROCm/vLLM host-specific constraints.

### Added regression tests for watcher resilience, config generation, and compose defaults. (Test Update)
- Cover watcher generate-config failure path and restart/reload decision matrix.
- Assert llama-swap/nginx generated config invariants and Docker defaults for Postgres plus AMD vLLM device env wiring.

### Added configurable nginx base URL routing and defaulted it to /audia/llmgateway. (Configuration Cleanup)
- Added network.base_path handling in config loader and generated nginx namespace passthrough routes.
- Updated landing-page links/docs and added regression tests for base-path route generation.

### Added versioned backend-runtime catalog support for Docker provisioning and macros. (New Feature)
- Gateway now generates backend-runtime.catalog.json and versioned llama-server macros from backend_runtime_variants.
- Provisioning script now reads the catalog to download multiple backend variants (e.g. rocm/vulkan versions) into dedicated runtime subdirectories.
- Watcher now restarts llama-cpp when runtime-catalog or env changes; regression tests and docs updated.

### Separated backend runtime variant sources from model catalog and added multi-source backend provisioning. (New Feature)
- Added config/project/backend-runtime.base.yaml and config/local/backend-runtime.override.yaml as the dedicated backend source catalog.
- Provisioning now supports github_release, direct_url, and git source types with versioned backend macros and generated runtime catalog output.

### Documented how to add backend runtime variants and aligned specs with separate backend runtime catalog. (Documentation Update)
- Added step-by-step backend variant onboarding in docker docs and runbook with github_release/direct_url/git examples.
- Updated specs and postinstall seeding so backend-runtime.override.yaml is part of default local config templates.

### Added reusable backend-runtime profiles and AMD-targeted ROCm variants (New Feature)
- Added profile composition (profile/profiles/extends) to backend runtime catalog resolution and generated catalog output.
- Added default backend-runtime profiles and disabled sample variants for gfx1030/gfx1100 using ROCm official and lemonade sources.
- Updated README/runbook/docker docs + llama.cpp runtime spec and added regression tests for profile-based runtime variants.

### Added isolated backend build-root catalog plumbing, validated generation tests, and executed live qwen27 backend performance matrix on 10.10.100.10. (Performance Improvement)
- Extended backend-runtime variant schema and generated catalog output with source_subdir/build_root_subdir/build_env/pre_configure_command.
- Updated compose/docs/postinstall templates for persistent BACKEND_BUILD_ROOT and profile-based backend source builds.
- Ran local smoke/regression tests (26 passed) plus live 2-pass benchmark across Vulkan and ROCm variant labels; captured pass/fail and latency report artifacts.

### Added config-driven backend support matrix for model/backend compatibility. (New Feature)
- Added backend-support base and override config files with version-based rules.
- Wired compatibility checks into config generation and publishing, using backend runtime catalog versions.
- Documented backend support matrix usage and version requirements in runbook and Docker docs.

### Fix nginx root serving: computed static root from config path; add 6 routing regression tests (Bug Fix, Test Update)
- build_nginx_config hardcoded 'root /app/static' in the landing-page location block — path that never exists on native installs or in Docker — causing 404 on GET / (and GET /audia/llmgateway/ via base-path passthrough).
- Fixed by computing nginx_static_root from stack.reverse_proxy nginx config_path so the root directive always resolves to the directory where write_nginx_config writes index.html.
- Added 6 regression tests in test_litellm_config_generation.py covering: static root path does not use /app/static, all required proxy routes present, proxy headers on upstream blocks, landing-page links prefixed with base_path, base-path passthrough rewrite, and no-base-path omits namespace routes.

### Added device alias mapping for GPU presets and deployment options. (Configuration Cleanup)
- Implemented device alias expansion in config generation so readable names map to ROCm/Vulkan device IDs.
- Documented device_aliases usage in runbook.

### Fix nginx health route to prefix match so /health/liveliness routes correctly (Bug Fix)
- location = /health was an exact match, causing /health/liveliness and other sub-paths to return 404 from nginx's default static file handler instead of proxying to LiteLLM
- Changed to prefix 'location /health' so all /health/* paths route to litellm_upstream

### Add Docker DNS resolver to nginx config to prevent 502 after gateway container restart (Bug Fix)
- nginx upstream blocks cache DNS at startup; when the gateway container is recreated with a new IP, nginx returns 502 until manually reloaded
- Added 'resolver 127.0.0.11 valid=30s' to nginx http block so Docker's embedded DNS is used for re-resolution after restarts

### Add nginx tests for health prefix route and Docker DNS resolver directive (Test Update)
- test_nginx_health_is_prefix_route_not_exact_match: asserts location /health is prefix (not exact), so /health/liveliness routes through
- test_nginx_config_contains_docker_dns_resolver: asserts resolver 127.0.0.11 is present in generated config
- Updated test_nginx_config_contains_all_required_proxy_routes to expect prefix /health not exact = /health

### Disable vLLM on live server: stop container and lock COMPOSE_PROFILES=watcher in .env (Configuration Cleanup)
- audia-vllm was running despite AUDIA_ENABLE_VLLM=false because it had unless-stopped restart policy from a previous compose up with --profile vllm
- Stopped the container and added COMPOSE_PROFILES=watcher to live .env so docker compose up will not start vLLM on next stack restart

### Update nginx and vLLM specs for health prefix route, Docker DNS resolver, and vLLM compose profiles (Documentation Update)
- spec-401-nginx-reverse-proxy: /health is now documented as prefix location; Docker DNS resolver note added
- spec-251-vllm-runtime: clarified vLLM is not started by default and requires COMPOSE_PROFILES=watcher,vllm and AUDIA_ENABLE_VLLM=true

---
