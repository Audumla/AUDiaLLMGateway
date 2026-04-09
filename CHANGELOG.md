# Changelog

## [0.15.0](https://github.com/Audumla/AUDiaLLMGateway/compare/v0.14.0...v0.15.0) (2026-04-09)


### Features

* **action-executor:** implement execution coordinator with history tracking ([4e39b7d](https://github.com/Audumla/AUDiaLLMGateway/commit/4e39b7dd464390fb9c8824f1a118f1912da92e95))
* **action-runner:** implement action dispatch system with multi-handler support ([2bcab03](https://github.com/Audumla/AUDiaLLMGateway/commit/2bcab03259f37ac80d87b0c6dcd46783163e057f))
* add detect-hardware.sh and provision Vulkan alongside all GPU backends ([2645a65](https://github.com/Audumla/AUDiaLLMGateway/commit/2645a6563d1468d390cdfcbb42eb4a1282be7ce8))
* add Docker containerization and test infrastructure ([716683f](https://github.com/Audumla/AUDiaLLMGateway/commit/716683f8abb9e4b603469c87df74005818eb69db))
* add image-only docker deployment flow ([790ab8d](https://github.com/Audumla/AUDiaLLMGateway/commit/790ab8da842d45230647eac3474915edf75a6e60))
* add vLLM profiles and CPU-only compose example to all Docker configurations ([75eed62](https://github.com/Audumla/AUDiaLLMGateway/commit/75eed628a95073f56d1b8a42fd98ac0ed36c2cf6))
* added linux distros into support ([360900f](https://github.com/Audumla/AUDiaLLMGateway/commit/360900f6dd4fe5b0461742d865c56a1c85ff50ea))
* added proper installs ([e70eb70](https://github.com/Audumla/AUDiaLLMGateway/commit/e70eb704ec47ac934a86aa1f9b275ccac5442d9b))
* auto-seed config/local/ on first Docker run ([751c4b8](https://github.com/Audumla/AUDiaLLMGateway/commit/751c4b8feb499b72857a116a42bca546c4ee4c98))
* **components-router:** implement components management router with action execution ([2b0be36](https://github.com/Audumla/AUDiaLLMGateway/commit/2b0be36b28ac85916449afac71d64b891577970b))
* docker enabled ([b277c32](https://github.com/Audumla/AUDiaLLMGateway/commit/b277c3225dd74258093721f30f77bc6a171ad1d0))
* **docker-handler:** implement Docker socket integration for container operations ([efc7992](https://github.com/Audumla/AUDiaLLMGateway/commit/efc79920d2b11a1e303a966d4b084fc508a1742c))
* enable monitoring manifests and fix port resolution ([363380a](https://github.com/Audumla/AUDiaLLMGateway/commit/363380a15aae6467eab55587abbb74d775a98377))
* **gateway-config:** implement configuration service for stack and models ([a2562df](https://github.com/Audumla/AUDiaLLMGateway/commit/a2562df60454420ec0fbdf9a4dcbcf9bf0178a59))
* implement Docker auto-start for Windows ([ed42a29](https://github.com/Audumla/AUDiaLLMGateway/commit/ed42a29658aaec38d50d644a5eac4cc444c160da))
* implement Phase 1 dashboard backend infrastructure ([8facef1](https://github.com/Audumla/AUDiaLLMGateway/commit/8facef1b5cf89ff09d2de7ec28991380df9b44e4))
* implement prebuilt binaries strategy with smart caching ([7a546d0](https://github.com/Audumla/AUDiaLLMGateway/commit/7a546d0990a0ec521a95da9090d9586e0975402c))
* initial implementation ([869c812](https://github.com/Audumla/AUDiaLLMGateway/commit/869c812aefce05216290b4b430083a97bfb68979))
* integrate docker watcher and vllm runtime flow ([44d92e7](https://github.com/Audumla/AUDiaLLMGateway/commit/44d92e7d221c72e260b17b63f548585632fef3bd))
* **logger:** implement centralized logging service for SSE streaming ([b63be0f](https://github.com/Audumla/AUDiaLLMGateway/commit/b63be0fb6672fcf4504e512e965ef5983291cccb))
* **logs-router:** implement log streaming endpoints with filtering ([b09dc4e](https://github.com/Audumla/AUDiaLLMGateway/commit/b09dc4e8436cd03d4fa9cb9c5a099e205bb3f098))
* **manifests-router:** implement component manifest discovery endpoints ([51da5d4](https://github.com/Audumla/AUDiaLLMGateway/commit/51da5d4babeeac3633c296f2b0be5a8cf1f20463))
* **prometheus-client:** implement Prometheus metrics client with query support ([e59a4ae](https://github.com/Audumla/AUDiaLLMGateway/commit/e59a4aeb956fdde27b2aa5459b2713e82b9b7bca))
* seed llama-swap.override.yaml and models.override.yaml on install ([a0b6b6e](https://github.com/Audumla/AUDiaLLMGateway/commit/a0b6b6e6ff9299cc5b161e5d0f27223fd668ab37))


### Bug Fixes

* /litellm/ proxies to LiteLLM root (Swagger), not dashboard ([bf357bb](https://github.com/Audumla/AUDiaLLMGateway/commit/bf357bb51b97f4acb1f4e618f4308cadfd3f37e5))
* add --project-directory . to all example compose run commands ([082eb1f](https://github.com/Audumla/AUDiaLLMGateway/commit/082eb1f5b5143328db9c6935090f8ba3f255d9a2))
* add allow_requests_on_db_unavailable to litellm config ([f23cfc4](https://github.com/Audumla/AUDiaLLMGateway/commit/f23cfc4d65e49b697fccd0742f0dad50d534c49b))
* add libatomic1 to backend base image for lemonade llama.cpp binary ([ba0269c](https://github.com/Audumla/AUDiaLLMGateway/commit/ba0269c294cb6344c1bae538b0d751a6bea7fa3b))
* add Vulkan auto-detection and proper Vulkan binary provisioning ([df72acf](https://github.com/Audumla/AUDiaLLMGateway/commit/df72acfabed1ecf613df13606efc04fe670c8e22))
* added dependancy ([fc04c84](https://github.com/Audumla/AUDiaLLMGateway/commit/fc04c84bfa90697faaeb502b817c779868e3b5a7))
* added labels to gpus in config ([d80d06a](https://github.com/Audumla/AUDiaLLMGateway/commit/d80d06afd4d68e1fc6e2d85cf65ba4f5bdb6fe6c))
* added llamacpp install ([987cbc2](https://github.com/Audumla/AUDiaLLMGateway/commit/987cbc2cbd6ff307fc4f27b0873e882c0718eb51))
* added llamacpp versioning ([f8a3cd7](https://github.com/Audumla/AUDiaLLMGateway/commit/f8a3cd77b55f1b535c0872b091010fb637421240))
* agent release errors ([9a3e4a6](https://github.com/Audumla/AUDiaLLMGateway/commit/9a3e4a6126a92231ed6508091e7122a6547305d1))
* agent syntax errors ([fe007b0](https://github.com/Audumla/AUDiaLLMGateway/commit/fe007b047d7e49dbd4960289ed8e07bcef63fb45))
* back end catalog management ([eebc51b](https://github.com/Audumla/AUDiaLLMGateway/commit/eebc51b45b240c2fcd1e7f764d5c8fda28b032dc))
* backend-aware GPU device names and Docker-explicit binary/model paths ([9db6d8b](https://github.com/Audumla/AUDiaLLMGateway/commit/9db6d8b62693aa2ab086caa264eadcf7552d0aba))
* branch renaming ([3986db3](https://github.com/Audumla/AUDiaLLMGateway/commit/3986db3bc1bb808cf815c3ed0da943948602f586))
* clean release ([b1b892e](https://github.com/Audumla/AUDiaLLMGateway/commit/b1b892e83178da53812047917a6b006ba03b6e16))
* config refactor ([044f1b3](https://github.com/Audumla/AUDiaLLMGateway/commit/044f1b36797f7ba0fdcebe508f7e9fd7247dc882))
* config sync ([2f2b308](https://github.com/Audumla/AUDiaLLMGateway/commit/2f2b308146e66e82f542f16facd0e0b6ceef0b3e))
* config update ([52c2278](https://github.com/Audumla/AUDiaLLMGateway/commit/52c2278c5dbe9ee3de8ecd7312eddf1e97a85058))
* config updates ([eb19941](https://github.com/Audumla/AUDiaLLMGateway/commit/eb199414db07ee036f3883c76111a88afdcac148))
* correct logger statistics and test hanging issues ([7aa93b0](https://github.com/Audumla/AUDiaLLMGateway/commit/7aa93b0596d50ce6d6e5fcfe0cc91f18b049548b))
* correct pagination total count in logs endpoint ([756f6a0](https://github.com/Audumla/AUDiaLLMGateway/commit/756f6a0c436e7b7023452e88194fb53272c366eb))
* correct qwen3.5-27B model directory casing on Linux ([abea03f](https://github.com/Audumla/AUDiaLLMGateway/commit/abea03feba005df6836f17ff5204467dd0fe4c9c))
* device_aliases NameError and Docker-aware nginx static root ([187c4a7](https://github.com/Audumla/AUDiaLLMGateway/commit/187c4a7636ea3ad765c31fc91d7853d93df2822a))
* distro deployment fixes ([03cc86b](https://github.com/Audumla/AUDiaLLMGateway/commit/03cc86b070c8397a6835b4099b680149a3485957))
* docker updates ([5d05104](https://github.com/Audumla/AUDiaLLMGateway/commit/5d05104905cc248faee9b942c17b9521da5e3adf))
* download llamacpp versions ([4664adf](https://github.com/Audumla/AUDiaLLMGateway/commit/4664adf03ff308f84ac8c354c2c2874fc9a77668))
* downloads to docker configured locations ([a93b265](https://github.com/Audumla/AUDiaLLMGateway/commit/a93b265489e60f340fe055f7165845b4a005cb3e))
* explicit nfpm file list and workflow cleanup ([693fd83](https://github.com/Audumla/AUDiaLLMGateway/commit/693fd83f27539c2546fc3803508be6faed5f39e5))
* expose all proxied endpoints without auth and fix redirect rewriting ([e0f1efd](https://github.com/Audumla/AUDiaLLMGateway/commit/e0f1efd5ff16fa43c4e391ad0e5c1b58f033a38c))
* force release please sync after manifest mismatch ([298ad16](https://github.com/Audumla/AUDiaLLMGateway/commit/298ad16fa51d32182abcb23416085edcd6a3f28f))
* gateway dashboard ([d7efde1](https://github.com/Audumla/AUDiaLLMGateway/commit/d7efde191374910540fe74e34fd5f9399923305c))
* handle invalid log level gracefully ([f997662](https://github.com/Audumla/AUDiaLLMGateway/commit/f997662140d794470e3ecfcfb904dd8de9dc7eb7))
* include detect-hardware.sh in gateway image ([97c8462](https://github.com/Audumla/AUDiaLLMGateway/commit/97c8462e66600a15925c65a77a981d0445b3dc83))
* inject litellm auth header in nginx and restore master_key config ([836dd7f](https://github.com/Audumla/AUDiaLLMGateway/commit/836dd7fd914f7790ca01bf831ccc9f34fe97beb8))
* installation fixes ([fce0873](https://github.com/Audumla/AUDiaLLMGateway/commit/fce08734f2c5ac42c4c26385ec0767c730fdf28c))
* lifecycle management updates ([21384bc](https://github.com/Audumla/AUDiaLLMGateway/commit/21384bcb974e016565daa7f1f00b98df1d6aeecd))
* litellm db broken ([ea79982](https://github.com/Audumla/AUDiaLLMGateway/commit/ea79982c6034b33b13717401c0068adc946cbb13))
* litellma db backend ([0a041aa](https://github.com/Audumla/AUDiaLLMGateway/commit/0a041aa0413fab01a07dd2762bf69622f5f14853))
* llamacpp backend rules and expansion ([1f006f0](https://github.com/Audumla/AUDiaLLMGateway/commit/1f006f0b365c01866680504b5c968739e0888fd9))
* llamacpp fixes ([448f529](https://github.com/Audumla/AUDiaLLMGateway/commit/448f529398c299c19768f28e3277170bbb0b2443))
* mount only config/local and config/generated, not entire config/ ([20952fb](https://github.com/Audumla/AUDiaLLMGateway/commit/20952fb30476a86d55c5f8a363d8db87bdb115fb))
* new tests ([ad64bf1](https://github.com/Audumla/AUDiaLLMGateway/commit/ad64bf10d56635ec7aff189d3edf10530f4d75c3))
* nginx health prefix route and Docker DNS resolver ([6ad9721](https://github.com/Audumla/AUDiaLLMGateway/commit/6ad9721f67a4269ec3d8f6ae50ee026ba012a698))
* normalize model file paths to forward slashes for Linux compatibility ([c0f2743](https://github.com/Audumla/AUDiaLLMGateway/commit/c0f2743e500d2f41815a0aed9cd7abf99f446c1b))
* pass $http_host to upstream so LiteLLM builds correct redirect URLs ([a3aea4b](https://github.com/Audumla/AUDiaLLMGateway/commit/a3aea4b73d3de796638510ebdc790c154a3b4c0d))
* pin backend service hosts to 127.0.0.1 in stack.base.yaml ([888cbef](https://github.com/Audumla/AUDiaLLMGateway/commit/888cbefb27ce3714d932e0cf17db2e00d6282439))
* proxy /litellm-asset-prefix/ through nginx for UI assets ([3814fec](https://github.com/Audumla/AUDiaLLMGateway/commit/3814fec824bc86a8e4bcebd802940698fdd685af))
* proxy llamaswap API routes through nginx so UI works behind /llamaswap/ prefix ([2f56381](https://github.com/Audumla/AUDiaLLMGateway/commit/2f56381e50a72f992eaef8e042d97d71ae639208))
* redirect /litellm and /litellm/ to dashboard (/litellm/ui/) ([6b62b63](https://github.com/Audumla/AUDiaLLMGateway/commit/6b62b63ed5f1a70f069ce8046a5ae71eb67401c0))
* redirect /litellm/ to dashboard and add swagger/openapi nginx routes ([405cbad](https://github.com/Audumla/AUDiaLLMGateway/commit/405cbad2e058e37d96e7144e429f6211f7894f7a))
* reduce logs ([d46d5a8](https://github.com/Audumla/AUDiaLLMGateway/commit/d46d5a811a80c1ee542ac7b285c66167be886751))
* release and install updates ([b4710d0](https://github.com/Audumla/AUDiaLLMGateway/commit/b4710d0c9a6598e5258cd84ae523d2443a6533ab))
* release build for distro installation files ([3fa81e6](https://github.com/Audumla/AUDiaLLMGateway/commit/3fa81e6b9b6c0085cd233e37da190776f8f3f4cc))
* release issues ([6fcf532](https://github.com/Audumla/AUDiaLLMGateway/commit/6fcf5327f250a705bca9545756c465f5e177ed4e))
* release issues ([6a97a27](https://github.com/Audumla/AUDiaLLMGateway/commit/6a97a271faf972ce700a4ba4d432f789f4441b82))
* release issues ([8b1eaa6](https://github.com/Audumla/AUDiaLLMGateway/commit/8b1eaa67023b1568421d3584fbfc0fe3227d6c82))
* release please added ([4467673](https://github.com/Audumla/AUDiaLLMGateway/commit/4467673e2e276bfbb53c80f159ae8c4a5336afaa))
* release please update ([fdc74ce](https://github.com/Audumla/AUDiaLLMGateway/commit/fdc74ce00d909c0d5b3e5498f82e0756fbbacb15))
* release problems ([1fbcf98](https://github.com/Audumla/AUDiaLLMGateway/commit/1fbcf982129735f16ac17702aa72666282c9e717))
* release syntax error ([ac78e41](https://github.com/Audumla/AUDiaLLMGateway/commit/ac78e41f1aa48eb434aa524a62c3845da91ee774))
* release workflow indentation ([6c32ef9](https://github.com/Audumla/AUDiaLLMGateway/commit/6c32ef903a573f70e74d43f8af2a83d6135c2c32))
* released installation ([2d4026c](https://github.com/Audumla/AUDiaLLMGateway/commit/2d4026cbc2513df62c1df3702c14ef5a0de826f7))
* remove GPU device requirements from root docker-compose.yml ([c0ab277](https://github.com/Audumla/AUDiaLLMGateway/commit/c0ab2774ccc2e0d73cdb185ed833132f9bd65ede))
* remove master_key from litellm config to allow no_auth to take effect ([cd7dc79](https://github.com/Audumla/AUDiaLLMGateway/commit/cd7dc798b18ac7bb945a940e05502debb733e8e4))
* rename component ([a3ec6cd](https://github.com/Audumla/AUDiaLLMGateway/commit/a3ec6cdd71d6b2a3f5057ab9b561d10b251acb1d))
* repair provision-runtime.sh and Dockerfile.gateway ([75eed62](https://github.com/Audumla/AUDiaLLMGateway/commit/75eed628a95073f56d1b8a42fd98ac0ed36c2cf6))
* resolve CI build failures - nfpm packaging and Docker base image access ([a35eac3](https://github.com/Audumla/AUDiaLLMGateway/commit/a35eac3d0e5ef76784fc87936b5f1ce88bf53ff9))
* resolve docker compose boot issues and server configuration ([093de54](https://github.com/Audumla/AUDiaLLMGateway/commit/093de549a2f7fd0f6250830cfa18a458bebd7789))
* resolve Docker matrix build and E2E test failures ([10d4a78](https://github.com/Audumla/AUDiaLLMGateway/commit/10d4a78147bc55101eeece3ed728b714fe6504e6))
* resolve manifest schema validation errors ([034a077](https://github.com/Audumla/AUDiaLLMGateway/commit/034a077d41a9cbba9ad58e5b75b05b51c4bd83ac))
* restore native install commands and fix CI test failures ([6fb47b9](https://github.com/Audumla/AUDiaLLMGateway/commit/6fb47b988967af4d7d1aae87f5a5c90970300ba7))
* revert litellm redirect ╬ô├ç├╢ /litellm/ proxies to litellm root (Swagger catalog) ([ec2d320](https://github.com/Audumla/AUDiaLLMGateway/commit/ec2d320f0baba1caf0aacd481dc4e94433d7b964))
* serve nginx index.html from mounted /app/static volume ([1d9cb27](https://github.com/Audumla/AUDiaLLMGateway/commit/1d9cb27d24c44030c73a939a07812010be81f980))
* symlink ggml backend plugins into bin dir and auto-set AMD Vulkan ICD ([263f3c6](https://github.com/Audumla/AUDiaLLMGateway/commit/263f3c61b28cedf7fcc9b215f9844acaf666a245))
* three Docker startup failures on AMD/SELinux systems ([fdc743f](https://github.com/Audumla/AUDiaLLMGateway/commit/fdc743fe0ead610f66f1d9910fb528537cb4da29))
* update branch naming ([6d8ebdf](https://github.com/Audumla/AUDiaLLMGateway/commit/6d8ebdf4ebcd4dce17ff18653c309fadd717c362))
* update changelog ([b04d512](https://github.com/Audumla/AUDiaLLMGateway/commit/b04d5128c0bd7fc4432729d7cbb7f1861af5ce20))
* update configuration management ([fcebc84](https://github.com/Audumla/AUDiaLLMGateway/commit/fcebc84e722fb480274752bf1d7c432edf29cfb6))
* update Dockerfile for src/monitoring refactoring ([abefd23](https://github.com/Audumla/AUDiaLLMGateway/commit/abefd23e9785d0d75c816a667e6d571b3b4d151b))
* update litellm for db backend ([edd391a](https://github.com/Audumla/AUDiaLLMGateway/commit/edd391a75cdc2016ea489bc2b3695c29d1c4af65))
* updated ([cb33f6f](https://github.com/Audumla/AUDiaLLMGateway/commit/cb33f6f2eed3ac8fa35f7b0cbbcfb11b80574a59))
* updated documentation ([3dea637](https://github.com/Audumla/AUDiaLLMGateway/commit/3dea6379bd485da39a331068bd5fd36b13e08b1d))
* updated install logic ([54d1821](https://github.com/Audumla/AUDiaLLMGateway/commit/54d1821371a87d2696c3ed1b57325d176d6cec4a))
* updated install scripts ([ea71d68](https://github.com/Audumla/AUDiaLLMGateway/commit/ea71d68651254109e680d8d4da3120a4f54d80a7))
* updated ngnix config ([87b8ec5](https://github.com/Audumla/AUDiaLLMGateway/commit/87b8ec5a424809b2ce0cc8b381cd6310110b743d))
* use /health/liveliness for gateway healthcheck ([84b7536](https://github.com/Audumla/AUDiaLLMGateway/commit/84b7536aa1f32f431e95bc44b137f9b92b824167))
* use /tmp paths in generated nginx.conf ([4d1cbd6](https://github.com/Audumla/AUDiaLLMGateway/commit/4d1cbd690bad276c82ab6fb49f50ea4bcfb91b62))
* use direct venv bootstrap in install stack to avoid circular import ([e4eaf60](https://github.com/Audumla/AUDiaLLMGateway/commit/e4eaf60b6835f2a3a6be9342534eab1c5827c86b))
* use minimal test config in E2E test to avoid litellm 1.70+ routing regression ([aef508a](https://github.com/Audumla/AUDiaLLMGateway/commit/aef508ad8f38a804c07aaf49bfe1653a3d9b68d0))
* use public_host for nginx landing page links ([f46958a](https://github.com/Audumla/AUDiaLLMGateway/commit/f46958a147d870aac54eccc632398ce4697f3b5f))
* use relative hrefs in nginx landing page ([fd14c39](https://github.com/Audumla/AUDiaLLMGateway/commit/fd14c394177dc7e1dcd9ce8cf341495793c09c40))


### Performance Improvements

* optimize Docker build for monitoring API ([d9a024a](https://github.com/Audumla/AUDiaLLMGateway/commit/d9a024a20371c0913414eb86b2a430d11f79d70c))


### Documentation

* add aggregate model_name=\"active\" metrics for dashboard ([5d6e3ad](https://github.com/Audumla/AUDiaLLMGateway/commit/5d6e3adcba9e25665ee670b4c9808966db49e2d8))
* add changelog entry for nginx proxy routing fix ([3f479e0](https://github.com/Audumla/AUDiaLLMGateway/commit/3f479e08ce377e2365128fd2f4b1a66ccdcd5f83))
* add combined benchmark priority matrix for vLLM + llama.cpp tests ([38be8d3](https://github.com/Audumla/AUDiaLLMGateway/commit/38be8d3b4d1cea7267571bc989eed7cdbc512103))
* add comprehensive llama.cpp backend versions reference ([8b0e834](https://github.com/Audumla/AUDiaLLMGateway/commit/8b0e83480eae6c75ec8e42e4ef7d299da7986346))
* add comprehensive Vulkan optimization test plan for RDNA3 tuning ([a553cdd](https://github.com/Audumla/AUDiaLLMGateway/commit/a553cdd6d3e4d24151b118e619332187b3f82839))
* add critical blockers & mitigation strategies (75% ╬ô├Ñ├å 85% readiness) ([fdbd5e0](https://github.com/Audumla/AUDiaLLMGateway/commit/fdbd5e0518a2a044bd9453748b02d5de7b7a707b))
* add Docker build and deployment script for Docker Hub ([688a675](https://github.com/Audumla/AUDiaLLMGateway/commit/688a675b186bdf26704985bb53d8956cb5625382))
* add exhaustive llama.cpp ROCm optimization test matrix ([d653c72](https://github.com/Audumla/AUDiaLLMGateway/commit/d653c721aca4da4f074fe32f603463e8c4e37eda))
* add missing GATEWAY_PORT, NGINX_PORT, VLLM_MAX_LEN env vars ([c8d7709](https://github.com/Audumla/AUDiaLLMGateway/commit/c8d7709cfbf09923e2041c80c526d20e680dcc48))
* add step-by-step manual testing instructions for phases 2-4 ([7ac1ac7](https://github.com/Audumla/AUDiaLLMGateway/commit/7ac1ac746d7936b63afb0db76e2d335748d2abcb))
* add testing complete summary with quick reference ([fc637f8](https://github.com/Audumla/AUDiaLLMGateway/commit/fc637f867299ca25fd2d35f35ad8381f236e3029))
* add tier 2 active-model detailed metrics to hybrid monitoring ([8049483](https://github.com/Audumla/AUDiaLLMGateway/commit/80494830e39166cf22b7597ef1e6140e4072af24))
* add vLLM ROCm build stream taxonomy and kernel optimization test plan ([5605aea](https://github.com/Audumla/AUDiaLLMGateway/commit/5605aea9fa4fdd37d56fee55cd97a83de763c52a))
* API reference with data structures and examples for Vue frontend ([d1f077f](https://github.com/Audumla/AUDiaLLMGateway/commit/d1f077f83c92d7c40e760c9d9137845a76905b51))
* apply aggregate model_name=\"active\" metrics to vLLM ([a55b920](https://github.com/Audumla/AUDiaLLMGateway/commit/a55b920215a1de2b9f134e42e2e0d99b32817dee))
* comprehensive build and deployment report for v0.14.0 ([74ac115](https://github.com/Audumla/AUDiaLLMGateway/commit/74ac1151a4cdd404ee9076e406782df1f9df63fb))
* document per-backend macro override pattern in llama-swap.base.yaml ([e86fb5b](https://github.com/Audumla/AUDiaLLMGateway/commit/e86fb5b4cff4a3112d6131e02b2f08856bd9d07b))
* enforce dashboard component independence & separation of concerns ([16b7a96](https://github.com/Audumla/AUDiaLLMGateway/commit/16b7a967b525610459c096510f2860a0f9429eb9))
* fix Docker Hub image names in docker.md ([0bd13dd](https://github.com/Audumla/AUDiaLLMGateway/commit/0bd13ddf5e2e72a2af2c2ac76c3ba363ef1146b2))
* incorporate all features and fixes into specs and documentation ([bf87fe1](https://github.com/Audumla/AUDiaLLMGateway/commit/bf87fe1d53be85f0edbb8a4b9e4ab12eed634f6f))
* optimize dashboard monitoring to single-query approach ([e86091e](https://github.com/Audumla/AUDiaLLMGateway/commit/e86091ec83e198e1a8a33beeebb3dd0195e66065))
* Phase 2 completion summary - Docker integration and action dispatch ([51a72c9](https://github.com/Audumla/AUDiaLLMGateway/commit/51a72c90b90e882e488b0f2691163fbfb5e0691b))
* Phase 3 Part 1 progress - infrastructure services complete ([6f817c2](https://github.com/Audumla/AUDiaLLMGateway/commit/6f817c2d10f4df3a882bcc540f5313382d1f86bc))
* Phase 3 Part 2 completion summary ([38866df](https://github.com/Audumla/AUDiaLLMGateway/commit/38866df8180dd9b841420f6d0e1656d61268f60f))
* record changelog entries for GPU backend and config fixes ([4645149](https://github.com/Audumla/AUDiaLLMGateway/commit/46451498d8d852a6c4745e1ceac0c8cff8a436c6))
* release summary for v0.14.0 ([ee62d2e](https://github.com/Audumla/AUDiaLLMGateway/commit/ee62d2e74215552e60ab16b36afb4e78728c5432))
* revamp documentation and expand Docker deployment ([75eed62](https://github.com/Audumla/AUDiaLLMGateway/commit/75eed628a95073f56d1b8a42fd98ac0ed36c2cf6))
* update dashboard specs with readiness assessment and implementation guidance ([6db242a](https://github.com/Audumla/AUDiaLLMGateway/commit/6db242a5cc3c09924c828741dc23f364eafaa1ce))
* update nginx and vLLM specs for health prefix route and compose profiles ([a90acb9](https://github.com/Audumla/AUDiaLLMGateway/commit/a90acb9e7bb63e0d86c0a51ac736df7290919858))
* update spec-002 and changelog for nginx proxy fixes ([150b479](https://github.com/Audumla/AUDiaLLMGateway/commit/150b479a9e79621a159e4d3d9340c5f6433b9f9d))
* update specs and docs to reflect v0.6.x state ([dce1878](https://github.com/Audumla/AUDiaLLMGateway/commit/dce187812aa824d2a5e3329d31ff132eb909afe6))

## [0.14.0](https://github.com/example/AUDiaLLMGateway/compare/v0.13.1...v0.14.0) (2026-03-28)


### Features

* **action-executor:** implement execution coordinator with history tracking ([aaaab91](https://github.com/example/AUDiaLLMGateway/commit/aaaab91829eb59c803c463585d772e6c0d0ae3b2))
* **action-runner:** implement action dispatch system with multi-handler support ([9005583](https://github.com/example/AUDiaLLMGateway/commit/9005583023757cc6d92e16b932faf6ff3b4f4b60))
* add Docker containerization and test infrastructure ([157855a](https://github.com/example/AUDiaLLMGateway/commit/157855ad436aeb2392cc4d65dae82d8d4c59be36))
* **components-router:** implement components management router with action execution ([e438a06](https://github.com/example/AUDiaLLMGateway/commit/e438a06ec39f51f1af5b8f6ddf08d9055aab8773))
* **docker-handler:** implement Docker socket integration for container operations ([0ddae51](https://github.com/example/AUDiaLLMGateway/commit/0ddae51a48b8836864246bb046cc4e8627611bff))
* enable monitoring manifests and fix port resolution ([b3f97e1](https://github.com/example/AUDiaLLMGateway/commit/b3f97e180b587981906920fdfdf68d1a81574d57))
* **gateway-config:** implement configuration service for stack and models ([e086db1](https://github.com/example/AUDiaLLMGateway/commit/e086db1e0620da944ce9f2776447f810d0abfbd4))
* implement Phase 1 dashboard backend infrastructure ([5a9326f](https://github.com/example/AUDiaLLMGateway/commit/5a9326f9fdf16ce43c5c57d22faf63cbecbc01b6))
* **logger:** implement centralized logging service for SSE streaming ([60114af](https://github.com/example/AUDiaLLMGateway/commit/60114af93026a35002014505c1c7345f53077705))
* **logs-router:** implement log streaming endpoints with filtering ([9f24fec](https://github.com/example/AUDiaLLMGateway/commit/9f24fec3cf46f63e33a280d741e5cdab6bebe00b))
* **manifests-router:** implement component manifest discovery endpoints ([fb2716b](https://github.com/example/AUDiaLLMGateway/commit/fb2716bea6eb6ff307522af58e19ade4f1779bd9))
* **prometheus-client:** implement Prometheus metrics client with query support ([8d58700](https://github.com/example/AUDiaLLMGateway/commit/8d58700582e6d45c582619fbc089b1c8495ae986))


### Bug Fixes

* /litellm/ proxies to LiteLLM root (Swagger), not dashboard ([ca441c2](https://github.com/example/AUDiaLLMGateway/commit/ca441c2ca594deb0fe75618887b6819eea8a7af4))
* add allow_requests_on_db_unavailable to litellm config ([f0b7226](https://github.com/example/AUDiaLLMGateway/commit/f0b722637babdb8900924f18178cf66c1740c68b))
* correct logger statistics and test hanging issues ([20cb271](https://github.com/example/AUDiaLLMGateway/commit/20cb271e2596eb417ba61504f1b648f7bd3b5bd4))
* correct pagination total count in logs endpoint ([f3a7d82](https://github.com/example/AUDiaLLMGateway/commit/f3a7d823aa40951d51dd871c060d19f91ce52c49))
* handle invalid log level gracefully ([89c07d2](https://github.com/example/AUDiaLLMGateway/commit/89c07d2baa8212aed37d561431a303e9ebd0fb62))
* proxy llamaswap API routes through nginx so UI works behind /llamaswap/ prefix ([7087f81](https://github.com/example/AUDiaLLMGateway/commit/7087f81fe43ac36b0a54fe4c8ce9dc04e48ae2a6))
* redirect /litellm and /litellm/ to dashboard (/litellm/ui/) ([63acdb4](https://github.com/example/AUDiaLLMGateway/commit/63acdb4297070d1ba4333cc7bcb780ceb0b8417a))
* redirect /litellm/ to dashboard and add swagger/openapi nginx routes ([e1d3ae1](https://github.com/example/AUDiaLLMGateway/commit/e1d3ae1b9598fabb45fe1e3e53b2bd6b38884a99))
* resolve CI build failures - nfpm packaging and Docker base image access ([413e3a6](https://github.com/example/AUDiaLLMGateway/commit/413e3a68f5e21866187aaf927ad1ca09f40c2c14))
* resolve Docker matrix build and E2E test failures ([94ded30](https://github.com/example/AUDiaLLMGateway/commit/94ded30c2b6a5700f4207fdbc4ccf2047f5e14db))
* resolve manifest schema validation errors ([7bda2e1](https://github.com/example/AUDiaLLMGateway/commit/7bda2e1d2268dfb5b2ded17d71e7344cea42c17a))
* revert litellm redirect — /litellm/ proxies to litellm root (Swagger catalog) ([b4a39fa](https://github.com/example/AUDiaLLMGateway/commit/b4a39fa6501642c297a171396cb74f8a790f226c))
* update Dockerfile for src/monitoring refactoring ([aa5047c](https://github.com/example/AUDiaLLMGateway/commit/aa5047c0cc92152b45d6f980b2c8bb6161478456))
* use minimal test config in E2E test to avoid litellm 1.70+ routing regression ([91d193b](https://github.com/example/AUDiaLLMGateway/commit/91d193b533c6ad92f9e302711451ea284fdf0df7))


### Performance Improvements

* optimize Docker build for monitoring API ([dcac744](https://github.com/example/AUDiaLLMGateway/commit/dcac744d4a46ec4582c9b078eacd05a4cd3e94ac))


### Documentation

* add aggregate model_name=\"active\" metrics for dashboard ([74dce24](https://github.com/example/AUDiaLLMGateway/commit/74dce24ada638daaf57471e333c6c3ed366838b3))
* add changelog entry for nginx proxy routing fix ([cdd0974](https://github.com/example/AUDiaLLMGateway/commit/cdd09742bc1bba3952f23ecc65b275c9e454366c))
* add critical blockers & mitigation strategies (75% → 85% readiness) ([a441550](https://github.com/example/AUDiaLLMGateway/commit/a441550b4d0c47409d37843ba182c467a293115d))
* add Docker build and deployment script for Docker Hub ([90258c6](https://github.com/example/AUDiaLLMGateway/commit/90258c696b4bffd6578831e6d97339cc6555b3b0))
* add tier 2 active-model detailed metrics to hybrid monitoring ([6988f14](https://github.com/example/AUDiaLLMGateway/commit/6988f1412e3686e790774488bd516db753c5eaa9))
* API reference with data structures and examples for Vue frontend ([a13260d](https://github.com/example/AUDiaLLMGateway/commit/a13260d766abe3fffbb4e6030f9708acaa9be91c))
* apply aggregate model_name=\"active\" metrics to vLLM ([99e9fb3](https://github.com/example/AUDiaLLMGateway/commit/99e9fb346070a4a276ff3ea61ab945373d04ab30))
* comprehensive build and deployment report for v0.14.0 ([24c9fdb](https://github.com/example/AUDiaLLMGateway/commit/24c9fdb6244cd1c5644e4b2757331104d0886dea))
* enforce dashboard component independence & separation of concerns ([a459ec1](https://github.com/example/AUDiaLLMGateway/commit/a459ec1c3a063c96bb09d4f84d81a6a5e12d32a8))
* optimize dashboard monitoring to single-query approach ([40d4cc4](https://github.com/example/AUDiaLLMGateway/commit/40d4cc40a20e76dca6ded43fa4fe80600ec9d514))
* Phase 2 completion summary - Docker integration and action dispatch ([0bb8000](https://github.com/example/AUDiaLLMGateway/commit/0bb800080cf887e93e2023aaa631478f77494614))
* Phase 3 Part 1 progress - infrastructure services complete ([c3a041e](https://github.com/example/AUDiaLLMGateway/commit/c3a041ecbf0898955473fcfbd332acc0e775f750))
* Phase 3 Part 2 completion summary ([81f7f49](https://github.com/example/AUDiaLLMGateway/commit/81f7f49009cd916b23cf30bf088c7951f67ad4c1))
* release summary for v0.14.0 ([2af56ca](https://github.com/example/AUDiaLLMGateway/commit/2af56ca2e409d97953615ffb6125d908fcd0e1ac))
* update dashboard specs with readiness assessment and implementation guidance ([7cd47e9](https://github.com/example/AUDiaLLMGateway/commit/7cd47e960d07e9afe1f1e1443d219827e8cad054))

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
- Added backend_bind_host: 127.0.0.1 and host: 127.0.0.1 for both backend services; all five endpoints now return 2xx through nginx on gpu-host (gpu-host.example:8080).

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
- Validated nginx proxy parity against LiteLLM and llama-swap on gpu-host.example and verified watcher regeneration plus nginx reload after fixing SELinux access for the Docker socket.

### Configured the remote gateway host to persistently expose the NTFS-backed model store to the llm_gateway Docker stack. (Configuration Cleanup)
- Mounted NTFS volume UUID 681E56C51E568C46 at /srv/extra-storage via /etc/fstab on gpu-host.example.
- Bound /srv/extra-storage/development/llm-models onto /opt/docker/services/llm_gateway/models after verifying a host symlink did not surface model contents inside Docker.
- Recreated audia-llama-cpp and verified /app/models contains the expected model directories.

### Mounted the secondary NTFS partition persistently at /srv/llm-models on the remote gateway host. (Configuration Cleanup)
- Added UUID=F2CCA3DBCCA397FD /srv/llm-models ntfs entry to /etc/fstab on gpu-host.example.
- Created /srv/llm-models and mounted the volume immediately.
- Verified mount with findmnt and directory listing.

### Published backend-swappable llama-swap port to the host for external testing. (Configuration Cleanup)
- Patched /opt/docker/services/llm_gateway/docker-compose.yml on gpu-host.example to add ${LLAMA_SWAP_PORT:-41080}:41080 under backend-swappable.
- Recreated audia-llama-cpp and verified compose now reports 0.0.0.0:41080->41080/tcp.
- Confirmed host listener with ss and successful HTTP response from localhost:41080.

### Disabled audia-gateway Docker health polling to stop repetitive /health/liveliness access logs. (Configuration Cleanup)
- Patched /opt/docker/services/llm_gateway/docker-compose.yml on gpu-host.example: gateway healthcheck set to disable:true.
- Adjusted nginx depends_on condition from service_healthy to service_started for compose compatibility without health checks.
- Recreated audia-gateway and verified docker inspect reports Test=[NONE] and recent logs no longer contain the periodic liveliness GET entries.

### Enabled AMD GPU device passthrough for backend-swappable on the remote Docker host. (Configuration Cleanup)
- Patched /opt/docker/services/llm_gateway/docker-compose.yml backend-swappable with devices /dev/kfd and /dev/dri.
- Added numeric group_add entries 482 and 485 after named groups failed under Docker.
- Recreated audia-llama-cpp and verified HostConfig.Devices plus /dev/kfd and /dev/dri visibility inside the container.

### Cleaned remote default config overrides and split GGUF model storage from vLLM/HuggingFace cache paths. (Configuration Cleanup)
- Moved existing model directories into /srv/extra-storage/development/llm-models/gguf and added /srv/extra-storage/development/llm-models/hf-cache.
- Updated /etc/fstab bind mounts to map /opt/docker/services/llm_gateway/models -> gguf and /opt/docker/services/llm_gateway/models-hf -> hf-cache.
- Patched remote docker-compose to use MODEL_HF_ROOT for backend-vllm cache and repaired gateway service block after prior edits.
- Reset config/local/models.override.yaml to a clean empty override template and regenerated configs with vLLM gpu_memory_utilization=1.0.

### Restored primary models bind root to llm-models and moved gguf/hf separation into MODEL_ROOT subpaths. (Configuration Cleanup)
- Changed /etc/fstab so /opt/docker/services/llm_gateway/models binds to /srv/extra-storage/development/llm-models (primary root).
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
- Validated full nginx -> LiteLLM -> llama-swap matrix on gpu-host.example and documented ROCm/vLLM host-specific constraints.

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

### Added isolated backend build-root catalog plumbing, validated generation tests, and executed live qwen27 backend performance matrix on gpu-host.example. (Performance Improvement)
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

### Moved project docs under specifications/docs to keep repo root tidy. (Documentation Update)
- Relocated root docs and existing docs/ into specifications/docs.
- Updated README, doc index, spec references, and packaging path to new docs location.
- Removed stray root outputs and empty docs directory.

### Full end-to-end test of deployed LLM gateway on gpu-host (gpu-host.example) covering all 7 phases. (Test Update)
- Phase 1: All 5 endpoints healthy, 13 llama-swap models, generated configs valid
- Phase 2: tiny_qwen25 344 tok/s, qwen4b_vision1 anomalously slow at 3.9 tok/s
- Phase 3: Vulkan 31.1 tok/s beats ROCm 25 tok/s (24% faster) for 27B; 122B at 37.7 tok/s on 3-GPU Vulkan
- Phase 4: vLLM FAIL - custom image is CUDA not ROCm; standard ROCm image fails No HIP GPUs; docker-compose missing config volume mount
- Phase 5: hwexp and node-exporter scraping OK, no LLM inference metrics in Prometheus
- Phase 6: All nginx proxy routes PASS
- Phase 7: 7 issues documented including vLLM bugs and missing Prometheus LLM metrics

---
