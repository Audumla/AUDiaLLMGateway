# LLM Backend Build and Usage Catalog

This document consolidates build and runtime steps for every backend we have tested or attempted on the dual RX 7900 XTX server. The goal is repeatability: no re-investigation each time a backend is added or revisited.

---

## Common Environment (gpu-host.example)

### GPU Isolation

Always exclude the RX 6900 XT (gfx1030) when benchmarking Qwen3.5-27B on ROCm.

```
ROCR_VISIBLE_DEVICES=0,1
HIP_VISIBLE_DEVICES=0,1
```

### Paths

- GGUF model: `/opt/docker/services/llm_gateway/models/gguf/qwen3.5-27B/Qwen3.5-27B-Q6_K.gguf`
- HF models: `/opt/docker/services/llm_gateway/models-hf`
- Runtime root (llama.cpp): `/opt/docker/services/llm_gateway/config/data/backend-runtime`

### Ports

- llama-swap: `41080`
- benchmark llama-server variants: `41082`
- vLLM: `41090` (bench variants use 41111/41112 in scripts)
- TGI: `41120`
- SGLang: `41110`
- Ollama: `41100`
- KoboldCpp: `41101`
- Aphrodite: `41130`

---

## Backend Catalog

### 0. Likely Candidates (Not Yet Tested)

These are included because they are plausible on AMD RDNA3, but not yet validated.

- **MLC-LLM (Vulkan)**: Likely candidate. MLC can target Vulkan via TVM; would require model compilation to the target GPU. Not compatible with GGUF directly.
- **LMDeploy (ROCm)**: Possible but unverified on RDNA3; primarily documented for NVIDIA/CUDA. Include only if ROCm support is confirmed.
- **Text-Generation-WebUI backends (Vulkan/ROCm)**: Potential wrapper for llama.cpp / exllama. Not a backend itself; only worth including if we want a unified UI layer.

Explicitly excluded (not good candidates for this hardware):

- **TensorRT-LLM**: NVIDIA-only.
- **exllama/exllamav2**: NVIDIA-only (CUDA).
- **OpenVINO**: Intel-focused.

### 1. llama.cpp (Vulkan)

**Source:** ggml-org llama.cpp releases or build from source with Vulkan enabled.

**Build (from source):**

```bash
cmake -B build -DGGML_VULKAN=ON
cmake --build build -j
```

**Runtime:**

```bash
/app/runtime-root/vulkan/bin/llama-server-vulkan \
  --host 0.0.0.0 --port 41082 \
  -m /app/models/gguf/qwen3.5-27B/Qwen3.5-27B-Q6_K.gguf \
  --ctx-size 4096 -n 128 --gpu-layers 99
```

**Notes:** Vulkan currently leads on dual XTX (26.41 tok/s baseline). Keep the 6900 XT out of the split for 27B tests.

### 2. llama.cpp (ROCm variants)

ROCm backends are managed by the backend runtime catalog:

- `config/project/backend-runtime.base.yaml`
- `config/local/backend-runtime.override.yaml`

Each variant declares a `macro` and a `version` to support compatibility rules.

**Example variants:**

- `rocm_gfx1100_preview` (confirmed 22.49 tok/s)
- `rocm_ggml_latest`
- `rocm_ggml_b8429`
- `rocm_ggml_git_main`
- `rocm_lemonade_b1217`
- `rocm_gfx1030_bin` (only for gfx1030 hardware)

**Runtime (inside `audia-llama-cpp` container):**

```bash
docker exec -d audia-llama-cpp bash -c '
  export ROCR_VISIBLE_DEVICES=0,1
  export HIP_VISIBLE_DEVICES=0,1
  export LD_LIBRARY_PATH=/app/runtime-root/rocm/gfx1100/preview/lib:/app/runtime-root/rocm/gfx1100/preview/bin:$LD_LIBRARY_PATH
  /app/runtime-root/rocm/gfx1100/preview/bin/llama-server-rocm \
    --host 0.0.0.0 --port 41082 \
    -m /app/models/gguf/qwen3.5-27B/Qwen3.5-27B-Q6_K.gguf \
    --ctx-size 4096 -n 128 --gpu-layers 99 \
    > /tmp/llama_bench.log 2>&1
'
```

**Important:** `fuser` is not installed in the container. Use:

```bash
docker exec audia-llama-cpp bash -c 'pkill -9 -f "port 41082" 2>/dev/null; sleep 3'
```

### 3. KoboldCpp (Vulkan)

**Source:** `https://github.com/LostRuins/koboldcpp/releases/latest`

**Runtime (inside `audia-llama-cpp` container):**

```bash
docker exec -d audia-llama-cpp bash -c '
  VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.json \
  /tmp/koboldcpp \
    --model /app/models/gguf/qwen3.5-27B/Qwen3.5-27B-Q6_K.gguf \
    --port 41101 --host 0.0.0.0 \
    --usevulkan --gpulayers 99 \
    --contextsize 4096 \
    > /tmp/kobold_bench.log 2>&1
'
```

**Known issue:** readiness timeout; increase to 900s or start with `--contextsize 2048`.

### 4. Ollama (ROCm)

**Image:** `ollama/ollama:rocm`

**Runtime:**

```bash
docker run -d --name bench-ollama \
  --device /dev/kfd --device /dev/dri --group-add video --group-add render \
  -e ROCR_VISIBLE_DEVICES=0,1 -e HIP_VISIBLE_DEVICES=0,1 \
  -v /opt/docker/services/llm_gateway/models:/app/models:ro \
  -p 41100:11434 \
  -e OLLAMA_HOST=0.0.0.0 \
  ollama/ollama:rocm
```

**Known issue:** startup hang if ROCm is in a dirty state. Restart `audia-llama-cpp` before running.

### 5. vLLM (ROCm)

**Image:** `vllm/vllm-openai-rocm:latest`

**Runtime (AWQ):**

```bash
docker run -d --name bench-vllm-awq \
  --device /dev/kfd --device /dev/dri --group-add video --group-add render \
  -e ROCR_VISIBLE_DEVICES=0,1 -e HIP_VISIBLE_DEVICES=0,1 \
  --ipc host \
  -v /opt/docker/services/llm_gateway/models-hf:/models:ro \
  -p 41111:8000 \
  vllm/vllm-openai-rocm:latest \
  --model /models/hub/models--QuantTrio--Qwen3.5-27B-AWQ/snapshots/<hash> \
  --served-model-name qwen27b \
  --tensor-parallel-size 2 \
  --quantization awq \
  --gpu-memory-utilization 0.85 \
  --max-model-len 4096 \
  --trust-remote-code
```

**Known issue:** Engine core init failure if ROCm is dirty. Restart `audia-llama-cpp` before vLLM tests.

### 6. TGI (ROCm)

**Image:** `ghcr.io/huggingface/text-generation-inference:latest-rocm`

`3.3.5-rocm` was checked and not found on GHCR. `latest-rocm` is the verified ROCm tag.

**Runtime:**

```bash
docker run -d --name bench-tgi \
  --device /dev/kfd --device /dev/dri --group-add video --group-add render \
  -e ROCR_VISIBLE_DEVICES=0,1 -e HIP_VISIBLE_DEVICES=0,1 \
  -v /opt/docker/services/llm_gateway/models-hf:/models:ro \
  -p 41120:80 \
  ghcr.io/huggingface/text-generation-inference:3.3.5-rocm \
  --model-id /models/hub/models--Qwen--Qwen3.5-27B/snapshots/<hash> \
  --num-shard 2 \
  --dtype bfloat16 \
  --max-total-tokens 4096 \
  --trust-remote-code
```

**Known issue:** `:latest` is CUDA-only and hangs; use `:3.3.5-rocm` or `:latest-rocm`.

### 7. SGLang (ROCm)

**Image:** `lmsysorg/sglang:v0.5.10rc0-rocm720-mi30x`

This image targets MI300X (gfx942) and may not support gfx1100. If it fails, try `lmsysorg/sglang:latest` or build from source with ROCm 7.x.

```bash
docker run -d --name bench-sglang \
  --device /dev/kfd --device /dev/dri --group-add video --group-add render \
  -e ROCR_VISIBLE_DEVICES=0,1 -e HIP_VISIBLE_DEVICES=0,1 \
  --ipc host \
  -v /opt/docker/services/llm_gateway/models-hf:/models:ro \
  -p 41110:30000 \
  -e SGLANG_USE_AITER=0 \
  lmsysorg/sglang:v0.5.10rc0-rocm720-mi30x \
  python3 -m sglang.launch_server \
    --model-path /models/hub/models--Qwen--Qwen3.5-27B/snapshots/<hash> \
    --tensor-parallel-size 2 \
    --port 30000 \
    --host 0.0.0.0 \
    --trust-remote-code \
    --dtype bfloat16
```

### 8. Aphrodite Engine

**Image:** `alpindale/aphrodite-engine:latest` (likely CUDA-only).

If ROCm support is required, build from source:

```bash
git clone https://github.com/PygmalionAI/aphrodite-engine
cd aphrodite-engine
docker build -f Dockerfile.rocm -t aphrodite-rocm .
```

---

## Repeatable Benchmark Steps

1. Stop production traffic or run in a dedicated benchmark window.
2. Export `ROCR_VISIBLE_DEVICES=0,1` and `HIP_VISIBLE_DEVICES=0,1` for all ROCm runs.
3. For llama.cpp variants, use `pkill -9 -f "port <N>"` between runs.
4. Restart `audia-llama-cpp` before Tier 2 backends (vLLM, TGI, Aphrodite, SGLang, Ollama).
5. Record both eval tok/s and prefill tok/s; update `specifications/docs/llm-backend-performance.md`.
6. Save raw run results under `specifications/data/backend-benchmarks/` with a timestamped filename.

---

## Config References

- Backend runtime catalog: `config/project/backend-runtime.base.yaml`
- Backend runtime overrides: `config/local/backend-runtime.override.yaml`
- Backend support matrix: `config/project/backend-support.base.yaml`
- Backend support overrides: `config/local/backend-support.override.yaml`
