# Docker Field Notes

This document captures real deployment issues found during AMD/Linux Docker
validation and the fixes that proved reliable.

## Known-Good Combinations

- `llama.cpp` Linux Vulkan: `b8429`
  - This build loaded the tested smaller Qwen 3.5 GGUFs that failed on older builds.
- AMD `vLLM`: `vllm/vllm-openai-rocm:latest`
  - Required `/dev/kfd`, `/dev/dri`, `ipc: host`, and `SYS_PTRACE`.
- Docker default for `VLLM_GPU_MEM`: `1.0`
- Default Docker LiteLLM UI path: PostgreSQL-backed via `DATABASE_URL`

## Proven Validation Order

When debugging inference failures, test in this order:

1. Raw `llama-server` inside the backend container
2. Direct `llama-swap`
3. LiteLLM
4. nginx

This isolates backend/runtime failures from routing failures.

## Issues Found and Resolved

### 1. Backend plugins disappeared after recreate

Symptom:

- `--list-devices` returned no usable backends
- Vulkan devices were not visible
- `invalid device` or `no backends are loaded`

Cause:

- `libggml-*.so` backend plugins were not consistently present next to the
  provisioned `llama-server` binaries after container recreation.

Resolution:

- Startup now re-symlinks backend plugins from `/app/runtime/lib` into
  `/app/runtime/bin` on every container start.

Notes:

- `ldconfig` warnings about `.so.0` files not being symlinks were observed but
  were not the primary failure once the backend plugins were linked correctly.

### 2. One shared runtime path caused backend drift

Symptom:

- runtime signatures matched stale content
- backend changes reused incompatible runtime state
- Vulkan and ROCm testing polluted each other

Resolution:

- `BACKEND_RUNTIME_ROOT` is now treated as a visible base directory
- each backend now lives in its own sibling directory such as `vulkan/`,
  `rocm/`, `cuda/`, or `cpu/`

### 3. Older Linux Vulkan builds failed on newer Qwen 3.5 GGUFs

Symptom:

- raw `llama-server-vulkan` failed to load some Qwen 3.5 models that worked on Windows

Resolution:

- use `LLAMA_VERSION=b8429` for the validated Linux Vulkan path

### 4. AMD `vLLM` failed on the wrong image

Symptom:

- container started but backend was not usable on AMD

Cause:

- a CUDA-oriented image path was being used on an AMD host

Resolution:

- use the official ROCm image:
  - `vllm/vllm-openai-rocm:latest`

### 5. Hugging Face cache and GGUF files were mixed together

Resolution:

- `MODEL_ROOT` stays for GGUF models
- `MODEL_HF_ROOT` is used for raw Hugging Face cache and tensor weights

### 6. Generated Docker hostnames drifted from Compose service names

Symptom:

- routing assumptions depended on old service names

Resolution:

- Compose service names are now:
  - `llm-gateway`
  - `llm-server-llamacpp`
  - `llm-server-vllm`
  - `llm-config-watcher`
- Generated Docker hostnames now use those service names too.

### 7. Model root assumptions were wrong for Docker

Symptom:

- model paths appeared valid in config but did not resolve in the container

Resolution:

- Docker model macros should use `/app/models` as the base path
- the mounted host `MODEL_ROOT` should contain the real model layout beneath that

### 8. Some catalog paths were valid semantically but wrong on disk

Resolution:

- validate every configured `model_file` and `mmproj_file` against the actual
  files under `models/gguf`
- fix path case/layout mismatches in `config/local/models.override.yaml`

### 9. `.env` corruption can silently break the stack

Symptom:

- startup behaved strangely after updates or edits

Cause:

- literal `\n` sequences were written into `.env` in one failed live edit

Resolution:

- inspect `.env` directly when behavior makes no sense
- prefer line-based env editing or the setup helper instead of ad hoc shell concatenation

### 10. LiteLLM warning about `model_group_alias_map`

Symptom:

- startup warning:
  - `model_group_alias_map is not a valid argument for Router.__init__()`

Resolution:

- warning is non-fatal on the current LiteLLM build
- the proxy still comes up and serves requests

### 11. LiteLLM UI login requires a DB-backed deployment

Symptom:

- direct `/ui/` login returned `Authentication Error, Not connected to DB!`

Resolution:

- the default root compose now includes PostgreSQL
- the gateway receives `DATABASE_URL` by default
- PostgreSQL data is persisted visibly under `POSTGRES_DATA_ROOT`

Additional implementation note:

- the gateway image must include the Python `prisma` package and run
  `prisma generate` against LiteLLM's bundled `schema.prisma` during image build
  or the gateway will fail at startup with:
  - `No module named 'prisma'`
  - `Unable to find Prisma binaries. Please run 'prisma generate' first.`

### 12. PostgreSQL can report healthy before LiteLLM can safely migrate

Symptom:

- `llm-db-postgres` shows `healthy`
- `llm-gateway` still logs repeated Prisma migration failures like:
  - `P1001: Can't reach database server at llm-db-postgres:5432`
- the gateway restarts and never becomes healthy

Cause:

- PostgreSQL's container health check can pass during its init/startup cycle
  before the database is stably reachable for LiteLLM's Prisma migration step.

Resolution:

- the gateway entrypoint now waits on `DATABASE_URL` TCP reachability before
  launching LiteLLM
- LiteLLM is started with enforced Prisma migration checks so DB startup issues
  fail clearly instead of surfacing later as a Prisma health-check crash

Useful env knobs:

- `DATABASE_WAIT_SECONDS`
- `DATABASE_WAIT_INTERVAL_SECONDS`

### 13. Watcher stopped reacting after one bad local override edit

Symptom:

- `llm-config-watcher` detected a change once, then never applied later changes
- `docker compose logs llm-config-watcher` showed a traceback from
  `generate-configs` followed by watchdog thread termination

Cause:

- watcher called `generate-configs` with `check=True` and did not catch
  `CalledProcessError`, so a single invalid override killed the event thread

Resolution:

- keep watcher alive on regeneration failure
- log the failure and wait for the next file change instead of crashing

### 14. llama-swap UI under `/llamaswap/` conflicted with LiteLLM `/ui/`

Symptom:

- `/llamaswap/` UI appeared slow or inconsistent
- browser loaded unexpected assets or redirects when both products exposed `/ui/*`

Cause:

- llama-swap UI emits absolute `/ui/*` asset links
- nginx was proxying llama-swap under `/llamaswap/*`, while LiteLLM also owned
  `/ui/*` at root

Resolution:

- normalize llama-swap entrypoints to `/llamaswap/ui/`
- add dedicated `/llamaswap/ui/*` proxy rule with redirect rewriting
- rewrite absolute `/ui/*` links in proxied llama-swap UI responses to
  `/llamaswap/ui/*`

### 15. YAML `on`/`off` values broke `llama.cpp` `--flash-attn`

Symptom:

- model startup failed immediately with:
  - `error while handling argument "--flash-attn": unknown value '--temp'`

Cause:

- unquoted YAML `on`/`off` in runtime presets are parsed as booleans
- renderer previously emitted bare `--flash-attn` for boolean `true`
- current `llama.cpp` expects `--flash-attn on|off|auto`

Resolution:

- config rendering now emits explicit `--flash-attn on|off` when the source
  value is boolean.

### 16. ROCm device IDs are zero-based and must match runtime enumeration

Symptom:

- specific ROCm deployment labels failed with:
  - `invalid device: ROCm3`

Cause:

- host exposed three devices (`ROCm0`, `ROCm1`, `ROCm2`)
- one deployment profile referenced non-existent `ROCm3`

Resolution:

- align `deployment_profiles` device names with `llama-server --list-devices`
  output for the target host
- default local template now uses `ROCm0` for the primary single-GPU ROCm
  profile

### 17. Nginx default proxy timeout was too short for cold model loads

Symptom:

- first requests for larger models returned:
  - `504 Gateway Time-out` at exactly ~60 seconds
- retries often succeeded after the model had already loaded

Cause:

- nginx default `proxy_read_timeout` (60s) was lower than cold-start load time
  for some llama.cpp deployments.

Resolution:

- set server-level proxy timeouts:
  - `proxy_connect_timeout 60s`
  - `proxy_send_timeout 600s`
  - `proxy_read_timeout 600s`

### 18. Live model filenames can differ from template URLs

Symptom:

- a configured model deployment failed with `No such file or directory` even
  though a similarly named model existed on disk.

Cause:

- local model folder had files from a different GGUF source/rename convention
  than the template defaults.

Resolution:

- validate paths against the real host model tree (`models/gguf/**`) and update
  `model_file` / `mmproj_file` per host where needed.

### 19. vLLM ROCm device pinning failed for non-zero device indices on one host

Symptom:

- `llm-server-vllm` worked with `VLLM_VISIBLE_DEVICES=0`
- setting `VLLM_VISIBLE_DEVICES=1` or `2` failed at startup with:
  - `RuntimeError: No HIP GPUs are available`

Cause:

- host/runtime-specific ROCm visibility behavior in the tested environment.

Resolution:

- keep `VLLM_VISIBLE_DEVICES=0` for stable operation on that host
- if per-GPU vLLM workers are required, validate host ROCm runtime behavior
  first and consider running separate vLLM services with explicit device maps.

## First-Install Recommendations

For a clean Docker install on Linux:

1. Run `./scripts/docker-setup.sh`
2. Verify `.env`
3. Put GGUF files under `MODEL_ROOT`
4. Start the stack with `docker compose up -d`
5. Validate bottom-up:
   - raw backend
   - `llama-swap`
   - LiteLLM
   - nginx

## AMD-Specific Notes

- For `llama.cpp`, Vulkan is a good first-install default on AMD.
- For `vLLM`, ROCm is the correct backend.
- Ensure Docker exposes:
  - `/dev/kfd`
  - `/dev/dri`
- Group access commonly requires:
  - `video`
  - `render`

## Useful Commands

Inspect generated config:

```bash
cat config/generated/llama-swap/llama-swap.generated.yaml
cat config/generated/litellm/litellm.config.yaml
```

Inspect runtime directories:

```bash
find ./config/data/backend-runtime -maxdepth 3 -type f | sort
```

Force fresh runtime reprovision:

```bash
rm -rf ./config/data/backend-runtime/*
docker compose up -d
```

Check raw Vulkan device visibility inside the backend container:

```bash
docker exec audia-llama-cpp /app/runtime-root/vulkan/bin/llama-server-vulkan --list-devices
```
- Mixed AMD `llama.cpp` deployments should keep `LLAMA_BACKEND=auto` so the
  runtime provisions both ROCm and Vulkan into separate runtime directories.
- On AMD Vulkan, force `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.json`
  so `llama-server-vulkan` consistently sees the RADV devices in-container.
- On AMD ROCm, the `llama.cpp` backend needs ROCm shared libraries present in the
  backend image. The validated set comes from `/opt/rocm/lib` and includes
  `libamdhip64`, `libhipblas`, `libhipblaslt`, `librocblas`, `librocsolver`,
  `librocroller`, `librocprofiler-register`, `libroctx64`, `libhsa-runtime64`,
  `libamd_comgr`, and `librocm-core`, plus `libnuma1` from Debian.
- ROCm also requires the `rocblas/library` data directory. Without it,
  `llama-server-rocm` fails with missing `TensileLibrary.dat` / `Illegal seek`
  errors for `gfx1100` devices.
