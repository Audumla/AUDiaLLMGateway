# Docker Field Notes

This document captures real deployment issues found during AMD/Linux Docker
validation and the fixes that proved reliable.

## Known-Good Combinations

- `llama.cpp` Linux Vulkan: `b8429`
  - This build loaded the tested smaller Qwen 3.5 GGUFs that failed on older builds.
- AMD `vLLM`: `vllm/vllm-openai-rocm:latest`
  - Required `/dev/kfd`, `/dev/dri`, `ipc: host`, and `SYS_PTRACE`.
- Docker default for `VLLM_GPU_MEM`: `1.0`

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
- startup resolves `/app/runtime` to a backend-specific subdirectory such as
  `vulkan`, `rocm`, `cuda`, `cpu`, or `auto`

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
docker exec audia-llama-cpp /app/runtime/bin/llama-server-vulkan --list-devices
```
