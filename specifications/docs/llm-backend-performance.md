# LLM Backend Performance & Optimization

> **Progressive document.** Append a new dated session entry each time benchmarks are run or tuning is attempted. Keep the Summary Table updated so agents and contributors can find the current best-known configuration at a glance.

---

## Revision History

| Date | Author | Entry |
| --- | --- | --- |
| 2026-03-28 | claude | Initial findings — Qwen3.5-27B, vLLM vs llama.cpp on dual RX 7900 XTX |
| 2026-03-28 | claude | Added research notes on AWQ/ROCm compatibility; benchmark plan with exact commands |
| 2026-03-29 | claude | Completed Plans B/C/E; Plans A/D blocked; all vLLM paths exhausted — llama.cpp Vulkan remains winner |
| 2026-03-29 | claude | Identified 4 separate vLLM ROCm build streams (official nightly, self-built, AMD dev, Navi-targeted); planned new test series |

---

## Summary Table (Best-Known Results)

This table is updated with each session. Values are single-sequence throughput on the standard prompt (see [Benchmark Methodology](#benchmark-methodology)).

| Backend | Build / image | Model | GPUs used | tok/s | Date |
| --- | --- | --- | --- | --- | --- |
| **llama.cpp Vulkan** | `llama-server-vulkan` | Qwen3.5-27B Q6_K | Vulkan1 + Vulkan2 (both XTX, 48 GB) | **26.41** | 2026-03-28 |
| llama.cpp Vulkan 3-GPU | `llama-server-vulkan` | Qwen3.5-27B Q6_K | Vulkan0+1+2 (all GPUs, 64 GB) | 21.98 | 2026-03-29 |
| llama.cpp ROCm | `ggml-latest` | Qwen3.5-27B Q6_K | ROCm0 + ROCm1 (both XTX, 48 GB) | ~21–22 | 2026-03-28 |
| llama.cpp ROCm | `ggml-b8429` | Qwen3.5-27B Q6_K | ROCm0 + ROCm1 (both XTX, 48 GB) | ~21 | 2026-03-28 |
| llama.cpp ROCm | `ggml-git-main` | Qwen3.5-27B Q6_K | ROCm0 + ROCm1 (both XTX, 48 GB) | ~21 | 2026-03-28 |
| llama.cpp ROCm | `lemonade-b1217` | Qwen3.5-27B Q6_K | ROCm0 + ROCm1 (both XTX, 48 GB) | ~21 | 2026-03-28 |
| vLLM 0.17.1 ROCm + speculative (ngram) | `vllm-openai-rocm:latest` | Qwen3.5-27B AWQ INT4 | GPU0 + GPU1 (both XTX, TP=2) | 11.06 | 2026-03-29 |
| vLLM 0.17.1 ROCm + TunableOp | `vllm-openai-rocm:latest` | Qwen3.5-27B AWQ INT4 | GPU0 + GPU1 (both XTX, TP=2) | 10.80 | 2026-03-29 |
| vLLM 0.17.1 ROCm baseline | `vllm-openai-rocm:latest` | Qwen3.5-27B AWQ INT4 | GPU0 + GPU1 (both XTX, TP=2) | 10.80 | 2026-03-28 |

---

## Reference Hardware (Server: gpu-host.example)

| rocm-smi ID | Vulkan ID | ROCm ID | Card | VRAM | GFX Arch | renderD |
| --- | --- | --- | --- | --- | --- | --- |
| GPU[0] | Vulkan0 | ROCm0 | AMD RX 6900 XT | 16 GB | gfx1030 (RDNA2) | renderD130 |
| GPU[1] | Vulkan1 | ROCm1 | AMD RX 7900 XTX | 24 GB | gfx1100 (RDNA3) | renderD129 |
| GPU[2] | Vulkan2 | ROCm2 | AMD RX 7900 XTX | 24 GB | gfx1100 (RDNA3) | renderD128 |
| CPU | — | — | Intel i7-12700KF | 20 threads | — | — |
| RAM | — | — | 94 GB | — | — | — |
| ROCm | — | — | 7.0 (HIP 7.0.51831) | — | — | — |

> **Vulkan and ROCm/rocm-smi enumerate GPUs in different orders.** Confirmed from `llama-server-vulkan --list-devices`:
> Vulkan0 = 6900 XT (16 GB), Vulkan1 = 7900 XTX (24 GB), Vulkan2 = 7900 XTX (24 GB).
> Note this is the reverse of rocm-smi order where GPU[0]/GPU[1] are the XTX cards.

---

## Benchmark Methodology

Consistent across all sessions unless noted:

- **Prompt:** "Explain the difference between transformer attention mechanisms and recurrent neural networks in detail, covering architecture, computational complexity, parallelism, and practical use cases."
- **Max tokens:** 300
- **Runs:** 2 per backend; report best warm run (Run 1 may include JIT compilation)
- **Metric:** `usage.completion_tokens / elapsed_seconds` (tok/s)
- **Isolation:** llama-swap container stopped before vLLM benchmarks to avoid GPU contention; vLLM must not be running during llama-swap runs

---

## Session: 2026-03-28 — Qwen3.5-27B: vLLM vs llama.cpp

### Context

Goal: determine best-performing backend for Qwen3.5-27B on the dual-XTX server. Tested vLLM 0.17.1 ROCm with extensive tuning, and five llama.cpp backends via llama-swap. Both sets of tests were run with the other backend stopped to ensure exclusive GPU access.

---

### llama.cpp Results (via llama-swap, port 41080)

All backends serve `Qwen3.5-27B-Q6_K.gguf` with 128 K context, layer-split across two GPUs, flash-attn on.

| Backend (llama-swap name) | Binary | GPUs | Best tok/s |
| --- | --- | --- | --- |
| `qwen3.5-27b-(96k-Q6)` | `llama-server-vulkan` | Vulkan1 + Vulkan2 (both XTX) | **26.41** |
| `qwen3.5-27b-(96k-Q6)-rocm-latest` | `llama-server-rocm-ggml-latest` | ROCm0 + ROCm1 (both XTX) | ~21–22 |
| `qwen27-rocm-ggml-b8429` | `llama-server-rocm-ggml-b8429` | ROCm0 + ROCm1 (both XTX) | ~21 |
| `qwen27-rocm-ggml-git-main` | `llama-server-rocm-ggml-git-main` | ROCm0 + ROCm1 (both XTX) | ~21 |
| `qwen27-rocm-lemonade-b1217` | `llama-server-rocm-lemonade-b1217` | ROCm0 + ROCm1 (both XTX) | ~21 |

> Per-run timing for this session was not individually captured; only the best-run summary was recorded. Future sessions should capture Run 1 / Run 2 individually.
> **Contaminated second run (discarded):** when vLLM was started immediately after the first llama-swap pass it held both XTX GPUs. A re-run of llama-swap during that window produced 0.65 tok/s for the Vulkan backend and HTTP 502 for all ROCm backends. These numbers are invalid and excluded from the Summary Table.

#### Key observation — Vulkan beats ROCm on identical hardware

Both Vulkan and ROCm backends use **both XTX cards (48 GB total)**. Vulkan wins by ~25% purely on kernel efficiency: llama.cpp's Vulkan compute shaders are more mature and better tuned for RDNA3 (gfx1100) than its ROCm/HIP kernels. The 6900 XT (Vulkan0) is intentionally excluded from the Qwen3.5-27B Vulkan config to keep it free for concurrent smaller-model workloads.

---

### vLLM Results (port 41091, exclusive GPU access)

Model: `QuantTrio/Qwen3.5-27B-AWQ` (AWQ INT4, ~21 GB per GPU pair). `--tensor-parallel-size 2`, both XTX GPUs.

| Configuration | Attention backend | Run 1 | Run 2 (warm) |
| --- | --- | --- | --- |
| AITER unified + hipBLASLt + HSA_OVERRIDE | `ROCM_AITER_UNIFIED_ATTN` | 3.36 tok/s† | **10.80 tok/s** |
| hipBLASLt + HSA_OVERRIDE (default Triton) | `TRITON_ATTN` | 3.36 tok/s† | **10.77 tok/s** |

†Run 1 slow due to Triton/AITER JIT kernel compilation on first inference (~89 s total). Stable from Run 2 onward (~28 s / 300 tokens).

**GPU utilization during inference: 100% on both XTX GPUs, ~24.4 GB VRAM each — fully GPU-resident, no CPU offload.**

#### vLLM tuning attempts (all ineffective on RDNA3)

| Env var / flag | Expected benefit | Actual effect |
| --- | --- | --- |
| `VLLM_ROCM_USE_AITER=1` | AITER linear, RMSNorm, MoE kernels | No change |
| `VLLM_ROCM_USE_AITER_UNIFIED_ATTENTION=1` | AMD AITER unified attention | No change |
| `TORCH_BLAS_PREFER_HIPBLASLT=1` | hipBLASLt GEMM ops | No change |
| `HSA_OVERRIDE_GFX_VERSION=11.0.0` | Explicit gfx1100 kernel selection | No change |
| `--disable-chunked-prefill` | Reduce scheduling overhead | Argument removed in vLLM v0.17 |

---

### Root Cause — why vLLM is 2.4× slower

The bottleneck is **Triton AWQ dequantization + GEMM on gfx1100 (RDNA3)**.

- vLLM auto-enables `VLLM_USE_TRITON_AWQ` on ROCm (logged as a warning at startup). There are no native CUDA AWQ kernels for AMD, so vLLM falls back to a Triton implementation that is not optimised for RDNA3.
- AMD's AITER library targets **gfx9 (CDNA: MI100/MI200/MI300)**. The high-performance `ROCM_AITER_FA` backend explicitly raises an error on non-gfx9. `ROCM_AITER_UNIFIED_ATTN` activates on gfx1100 but provides no measurable benefit because attention is not the bottleneck — linear layers are.
- llama.cpp Vulkan uses hand-tuned compute shaders that perform well on RDNA3. Q6_K (more bits than AWQ INT4) still runs 2.4× faster on the same two XTX GPUs.

---

### Session Verdict

| Use case | Recommended backend | tok/s |
| --- | --- | --- |
| Single-user / interactive | llama.cpp **Vulkan** | 26.41 |
| Single-user / ROCm fallback | llama.cpp ROCm (any build) | ~21 |
| High-concurrency / many users | vLLM — lower per-sequence throughput but batches many parallel requests; GPU stays at 100% | 10.8+ |

vLLM on RDNA3 is not competitive for single-sequence throughput today. This is expected to improve as AMD expands AITER/ROCm support to gfx11 (RDNA3).

---

### Research Notes: vLLM / ROCm / RDNA3 Compatibility

Findings from reviewing vLLM, ROCm, PyTorch, SGLang, and TGI docs and open issues (2026-03-28):

**Why AWQ performs poorly on gfx1100:**

- vLLM's quantization compatibility matrix marks **AWQ as unsupported on AMD GPU**. The ROCm platform code still forces AWQ onto the Triton AWQ path at startup (logged: `enabling VLLM_USE_TRITON_AWQ`).
- vLLM's own AWQ docs say AWQ is **under-optimized and can have lower throughput than unquantized models**; AWQ's primary benefit is memory footprint reduction, not speed.
- `custom_all_reduce` is only enabled for MI300-series in the ROCm platform code. `supports_fp8()` only returns `True` for gfx94/gfx95/gfx12 — not gfx1100. Most of the fast-path work targets Instinct/CDNA or newer gfx12, not RX 7900 XTX.
- RX 7900 XTX (gfx1100/1101) **is** a supported ROCm vLLM target (ROCm 6.3+), but it sits on unoptimized paths, not unsupported hardware.

**What will repeat for other models:**

- Any **AWQ checkpoint** (any model family — Qwen, Llama, Mistral, Gemma) is likely to see similar ~10 tok/s on this hardware until the Triton AWQ path improves for RDNA3.
- **Dense BF16/FP16** avoids the AWQ dequantization path entirely and is the cleanest test of base RDNA3 throughput. This is the most likely path to better numbers.
- **GPTQ**: conflicting docs — AMD ROCm page says GPTQ is supported via HIP kernels; vLLM's quantization chart marks it unsupported on AMD. Must be benchmarked, not assumed.
- **GGUF in vLLM**: explicitly described as "highly experimental and under-optimized" in vLLM docs. Not a strong candidate to beat llama.cpp.
- **FP8 on gfx1100**: `supports_fp8()` returns False for gfx1100; plus there is a known RDNA3 bug where fp8 KV cache + prefix caching crashes the process.

**What is not worth further time:**

- TGI ROCm: docs say it is tested on MI210/MI250/MI300; AWQ is explicitly listed as unsupported.
- More AITER toggles: benchmarks confirm no effect on gfx1100; the published AITER gains were all measured on MI300-class hardware.
- `TORCH_BLAS_PREFER_HIPBLASLT=1` alone: no effect on the Triton AWQ dequantization half of the problem.

---

## llama.cpp Operational Notes

Working configuration details for llama.cpp as deployed on this stack. Update in place when config changes.

### Infrastructure

llama.cpp backends are served through **llama-swap** running in the `audia-llama-cpp` container on port **41080**. llama-swap proxies `/v1/chat/completions` requests to the correct backend process, starting and stopping them on demand.

- Container: `audia-llama-cpp`
- Config: `/opt/docker/services/llm_gateway/config/generated/llama-swap/llama-swap.generated.yaml`
- Log level: `warn`
- Health check timeout: 300 s

### Model File

All Qwen3.5-27B backends use the same GGUF:

```text
/app/models/gguf/qwen3.5-27B/Qwen3.5-27B-Q6_K.gguf
```

Q6_K ≈ 21 GB. Fits across any two-GPU combination on this server.

### Backend Binaries and Runtime Paths

Each backend is a different build of `llama-server` with a different Vulkan/ROCm runtime. All live inside the `audia-llama-cpp` container:

| Binary macro | Path | Notes |
| --- | --- | --- |
| `llama-server-vulkan` | `/app/runtime-root/vulkan/bin/llama-server-vulkan` | `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.json` |
| `llama-server-rocm-ggml-latest` | `/app/runtime-root/rocm/ggml-latest/bin/llama-server-rocm` | Latest upstream ggml ROCm |
| `llama-server-rocm-ggml-b8429` | `/app/runtime-root/rocm/ggml-b8429/bin/llama-server-rocm` | ggml build b8429 |
| `llama-server-rocm-ggml-git-main` | `/app/runtime-root/rocm/ggml-git-main/bin/llama-server-rocm` | ggml git-main snapshot |
| `llama-server-rocm-lemonade-b1217` | `/app/runtime-root/rocm/lemonade-b1217/bin/llama-server-rocm` | Lemonade fork build 1217 |

### Effective Commands for Qwen3.5-27B Backends

Resolved from the llama-swap config macros (`${...}` expanded):

**Vulkan (best performer):**

```bash
env VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.json \
    LD_LIBRARY_PATH=/app/runtime-root/vulkan/lib \
  /app/runtime-root/vulkan/bin/llama-server-vulkan \
  --port ${PORT} --host 0.0.0.0 \
  --model /app/models/gguf/qwen3.5-27B/Qwen3.5-27B-Q6_K.gguf \
  --ctx-size 131072 \
  --device Vulkan2,Vulkan1 \
  --split-mode layer --tensor-split 1,1 \
  --gpu-layers 99 --parallel 1 \
  --jinja \
  --reasoning-budget 0 --reasoning-format none \
  --flash-attn on --temp 0 --top-p 0.9 --top-k 20 \
  --threads 8 --threads-batch 24 \
  --batch-size 512 --ubatch-size 512 \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --cache-reuse 128
```

**ROCm (substitute `<build>` with `ggml-latest`, `ggml-b8429`, `ggml-git-main`, or `lemonade-b1217`):**

```bash
env LD_LIBRARY_PATH=/app/runtime-root/rocm/<build>/lib:/opt/rocm/lib \
    ROCBLAS_TENSILE_LIBPATH=/opt/rocm/lib/rocblas/library \
  /app/runtime-root/rocm/<build>/bin/llama-server-rocm \
  --port ${PORT} --host 0.0.0.0 \
  --model /app/models/gguf/qwen3.5-27B/Qwen3.5-27B-Q6_K.gguf \
  --ctx-size 131072 \
  --device ROCm0,ROCm1 \
  --split-mode layer --tensor-split 1,1 \
  --gpu-layers 99 --parallel 1 \
  --jinja \
  --reasoning-budget 0 --reasoning-format none \
  --flash-attn on --temp 0 --top-p 0.9 --top-k 20 \
  --threads 8 --threads-batch 24 \
  --batch-size 512 --ubatch-size 512 \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --cache-reuse 128
```

### Notable Config Details

- **`--reasoning-budget 0 --reasoning-format none`** — disables chain-of-thought in Qwen3.5 (nothink mode). Removes `<think>...</think>` tokens from responses. Required for benchmarking to avoid inflated token counts.
- **`--cache-type-k q8_0 --cache-type-v q8_0`** — KV cache in 8-bit, halving KV VRAM at minimal quality cost.
- **`--cache-reuse 128`** — prefix KV cache reuse; speeds up multi-turn conversations.
- **`--ctx-size 131072`** — 128 K context. Q6_K at this context fits across the two XTX GPUs.
- **`--flash-attn on`** — enabled for all backends.

### Vulkan Device Index Mapping

Confirmed from `llama-server-vulkan --list-devices` inside the container:

| Vulkan index | Card | VRAM | rocm-smi equiv |
| --- | --- | --- | --- |
| Vulkan0 | RX 6900 XT (RADV NAVI21) | 16 GB | GPU[0] |
| Vulkan1 | RX 7900 XTX (RADV NAVI31) | 24 GB | GPU[1] |
| Vulkan2 | RX 7900 XTX (RADV NAVI31) | 24 GB | GPU[2] |

The Qwen3.5-27B Vulkan backend uses `--device Vulkan2,Vulkan1` — **both XTX cards (48 GB total)**. `Vulkan0` (the 6900 XT) is intentionally left free for concurrent smaller-model workloads.

---

## vLLM Operational Notes

Working configuration details for vLLM on this stack. Update in place when config changes.

### VL Model OOM Patch (required for Qwen3.5-27B-AWQ)

`QuantTrio/Qwen3.5-27B-AWQ` is a VL (vision-language) model (`Qwen3_5ForConditionalGeneration`). Without patching, vLLM's `profile_run()` attempts to allocate ~72 GB for vision encoder profiling, crashing with OOM.

**Fix:** force `mm_config.skip_mm_profiling = True` before the profiling check in `gpu_model_runner.py` (~line 5250 in vLLM 0.17.1):

```python
# PATCH: force skip vision profiling to avoid OOM on ROCm
if mm_config is not None:
    mm_config.skip_mm_profiling = True
if mm_config is not None and mm_config.skip_mm_profiling:
    ...
```

The patched file lives at `/tmp/gpu_model_runner_patched.py` on the server and is volume-mounted into the container as a read-only override.

### Working Docker Run Command (as of 2026-03-28)

```bash
docker run -d --name audia-vllm-bench \
  --device /dev/kfd \
  --device /dev/dri/renderD128 \
  --device /dev/dri/renderD129 \
  --group-add video --group-add render \
  --ipc host \
  -v /tmp/gpu_model_runner_patched.py:/usr/local/lib/python3.12/dist-packages/vllm/v1/worker/gpu_model_runner.py:ro \
  -v /opt/docker/services/llm_gateway/models-hf:/models:ro \
  -p 41091:8000 \
  -e ROCR_VISIBLE_DEVICES=0,1 \
  -e HIP_VISIBLE_DEVICES=0,1 \
  -e VLLM_ROCM_USE_AITER=1 \
  -e VLLM_ROCM_USE_AITER_UNIFIED_ATTENTION=1 \
  -e TORCH_BLAS_PREFER_HIPBLASLT=1 \
  -e HSA_OVERRIDE_GFX_VERSION=11.0.0 \
  vllm/vllm-openai-rocm:latest \
  --model /models/hub/models--QuantTrio--Qwen3.5-27B-AWQ/snapshots/56f41874389615226dcd849ded92261a0286ff59 \
  --served-model-name Qwen3.5-27B-AWQ-vLLM \
  --tensor-parallel-size 2 \
  --quantization awq \
  --gpu-memory-utilization 0.95 \
  --max-model-len 8192 \
  --trust-remote-code
```

Note: `renderD128` and `renderD129` correspond to the two XTX GPUs (GPU[1] and GPU[2] in rocm-smi terms; GPU[0] and GPU[1] as seen by ROCR_VISIBLE_DEVICES=0,1 inside the container).

### Startup Timing

| Phase | Duration |
| --- | --- |
| Container start → server ready | ~3 minutes |
| First inference request (Triton/AITER JIT) | ~89 seconds |
| Subsequent requests (300 tokens) | ~28 seconds |

### ROCm Attention Backend Reference (gfx1100)

| Backend | Env to activate | gfx1100 support | Notes |
| --- | --- | --- | --- |
| `TRITON_ATTN` | default | Yes | Default on RDNA3; no measurable difference from AITER |
| `ROCM_AITER_UNIFIED_ATTN` | `VLLM_ROCM_USE_AITER=1` + `VLLM_ROCM_USE_AITER_UNIFIED_ATTENTION=1` | Yes | No measurable benefit on gfx1100 |
| `ROCM_AITER_FA` | `VLLM_ROCM_USE_AITER=1` + `VLLM_ROCM_USE_AITER_MHA=1` | **No** — gfx9 only | Raises ValueError on gfx1100 |
| `ROCM_ATTN` | `use_prefill_decode_attention` config | Yes | Prefill-decode split; untested |

---

## Server File Reference

| Path | Description |
| --- | --- |
| `/tmp/gpu_model_runner_patched.py` | vLLM VL profiling OOM patch |
| `/tmp/bench_vllm2.py` | vLLM benchmark script (port 41091) |
| `/tmp/bench_qwen27.py` | llama-swap benchmark script (port 41080) |
| `/tmp/tunableop/tunableop_untuned0.csv` | TunableOp GEMM shapes — GPU0 worker (522 shapes) |
| `/tmp/tunableop/tunableop_untuned1.csv` | TunableOp GEMM shapes — GPU1 worker (522 shapes) |
| `/tmp/tunableop/tunableop_results.csv` | TunableOp tuned kernel selections (520 shapes, ~45 KB) |
| `/opt/docker/services/llm_gateway/docker-compose.yml` | Stack compose (vLLM in `vllm`/`full` profile) |
| `/opt/docker/services/llm_gateway/models-hf/hub/models--QuantTrio--Qwen3.5-27B-AWQ/snapshots/56f41874.../` | AWQ model weights (HuggingFace format) |
| `/opt/docker/services/llm_gateway/models-hf/hub/models--Qwen--Qwen3.5-27B/snapshots/b7ca741b.../` | BF16 model weights (HuggingFace format, ~54 GB) |
| `/opt/docker/services/llm_gateway/config/generated/llama-swap/llama-swap.generated.yaml` | Generated llama-swap config (5 Qwen3.5-27B backends + others) |
| `/app/models/gguf/qwen3.5-27B/Qwen3.5-27B-Q6_K.gguf` | GGUF model (inside `audia-llama-cpp` container) |

---

## Session: 2026-03-29 — Exhaustive vLLM Optimization Attempts

### Session Context

Continued from 2026-03-28. Goal: exhaust remaining legitimate optimization paths for vLLM on RDNA3. All five plans from the previous session's plan were executed.

---

### Plan A — vLLM BF16 (BLOCKED)

**Goal:** Remove AWQ dequantization overhead entirely by running the native BF16 model.

**Model downloaded:** `Qwen/Qwen3.5-27B` (23 files, ~54 GB) to `/opt/docker/services/llm_gateway/models-hf/hub/models--Qwen--Qwen3.5-27B/snapshots/b7ca741b86de18df552fd2cc952861e04621a4bd`

**Result: Cannot run on this hardware.**

Two failure modes encountered:

1. **TP=3 fails — model architecture incompatibility:** Qwen3.5-27B has 64 attention heads and hidden dim 5120. Neither is divisible by 3. vLLM raises `pydantic_core.ValidationError: 10240 is not divisible by 3` at config validation before loading any weights. Valid TP values for this model are: 1, 2, 4, 8, 16, 32, 64.

2. **TP=2 + `--cpu-offload-gb` fails — vLLM v1 executor incompatibility:** BF16 Qwen3.5-27B = ~54 GB weights; two XTXs = 48 GB VRAM. 6 GB must be offloaded to CPU. vLLM 0.17.1 raises `RuntimeError: Cannot re-initialize the input batch when CPU weight offloading is enabled` (see vllm PR #18298). The v1 multi-process executor does not support `--cpu-offload-gb`.

**Conclusion:** BF16 is not testable on this hardware configuration with vLLM 0.17.1. Would require 4× 16 GB GPUs, 2× 32 GB GPUs, or a future vLLM release that supports CPU offload in v1 mode.

**Alternative path for future testing:** Use `Qwen/Qwen2.5-14B-Instruct` (~28 GB BF16) with TP=2 on the two XTXs. This would fit without offload and confirm whether BF16 avoids the Triton AWQ bottleneck.

---

### Plan B — vLLM TunableOp offline GEMM tuning

**Goal:** let ROCm auto-select optimal rocBLAS/hipBLASLt GEMM kernels for the specific shapes used by this model.

**Execution:**

- Step 1: Ran vLLM with `PYTORCH_TUNABLEOP_RECORD_UNTUNED=1`. Three warmup passes captured 522 GEMM shapes to `/tmp/tunableop/tunableop_untuned0.csv` and `tunableop_untuned1.csv` (one per TP worker).
- Step 2: Offline tuning ran ~20 min (GPU[0] at 100%). 520 of 522 shapes tuned; 2 skipped (batch_size=1 shapes require online tuning). Results: `/tmp/tunableop/tunableop_results.csv` (45 KB).
- Step 3: Ran vLLM with `PYTORCH_TUNABLEOP_FILENAME=/workspace/tunableop_results.csv`, `PYTORCH_TUNABLEOP_TUNING=0`.

**Result: 10.80 tok/s — no improvement.**

TunableOp tunes GEMM operations on the standard BF16/FP16 path. AWQ uses a **Triton custom kernel** for dequantization + GEMM that is not a standard rocBLAS/hipBLASLt GEMM and is not covered by TunableOp. The tuned kernel selections were applied but the AWQ path did not benefit.

---

### Plan C — vLLM speculative decoding (ngram)

**Goal:** reduce single-stream latency by predicting tokens from prompt context without a draft model.

**Command used:**

```bash
vllm serve ... \
  --speculative-config '{"method":"ngram","num_speculative_tokens":5,"prompt_lookup_max":4}'
```

> Note: vLLM 0.17.1 uses `--speculative-config <JSON>` not `--speculative-model [ngram]`. The flag syntax changed in this version.

**Result: 11.06 tok/s — +2.4% improvement over baseline.**

Marginal gain. ngram proposals have a low acceptance rate on technical explanation text (the benchmark prompt) because the model rarely repeats n-gram patterns from the input. Speculative decoding is more effective on code generation or highly repetitive tasks.

---

### Plan D — SGLang ROCm (DEAD END)

**Goal:** test SGLang as an alternative serving engine.

**Result: No RDNA3 support — confirmed dead end.**

All available `lmsysorg/sglang-rocm` image tags are `v0.5.x-rocm700-mi30x` and `mi35x` (CDNA3/MI300 class only). No gfx1100/RDNA3 image exists. The repository name `lmsysorg/sglang:latest-rocm` does not exist; images are under `lmsysorg/sglang-rocm`. SGLang ROCm is AMD datacenter GPU only.

---

### Plan E — llama.cpp 3-GPU Vulkan split

**Goal:** check whether distributing the model across all three GPUs (6900 XT + 2× XTX) improves throughput.

**Configuration:** `--device Vulkan0,Vulkan1,Vulkan2 --tensor-split 16,24,24`

**Result: 21.98 tok/s — WORSE than 2-XTX baseline (26.41 tok/s).**

Adding the 6900 XT (Vulkan0, gfx1030, 16 GB) creates an **imbalanced configuration**. With equal-time layer splitting, the 6900 XT processes the same number of layers as each XTX but is ~25% slower per layer. The XTX workers stall waiting for the 6900 XT. The 2-XTX config keeps both fast GPUs fully utilized.

The 6900 XT adds negative value for Qwen3.5-27B throughput. Keep it reserved for concurrent smaller-model workloads.

---

### Session Verdict (2026-03-29)

All known optimization paths for vLLM on gfx1100 have been exhausted:

| Plan | Result | Improvement |
| --- | --- | --- |
| A — BF16 TP=3 | BLOCKED (divisibility error) | — |
| A — BF16 TP=2 + cpu-offload | BLOCKED (vLLM v1 incompatibility) | — |
| B — TunableOp | 10.80 tok/s | 0% |
| C — Speculative ngram | 11.06 tok/s | +2.4% |
| D — SGLang | BLOCKED (no RDNA3 image) | — |
| E — 3-GPU Vulkan | 21.98 tok/s | −17% vs 2-XTX |

**llama.cpp Vulkan (26.41 tok/s) remains the clear winner for single-sequence throughput on this hardware.** vLLM's advantage would only appear at high concurrency where batching amortizes the AWQ overhead across multiple parallel requests.

---

## vLLM ROCm Build Streams — Architecture & Test Plan (2026-03-29)

The 2026-03-29 session exhausted tuning knobs within vLLM 0.17.1 stable. However, **the bottleneck is not a vLLM setting — it is the Triton AWQ kernel quality on gfx1100.** This kernel lives in the ROCm/PyTorch/Triton runtime stack, not the vLLM application code.

Recent research identified **four separate vLLM ROCm build streams**, each bundling different ROCm/PyTorch/Triton stacks. These are not aliases; they represent genuinely different kernel selections at runtime. Testing them is the next logical step.

### Build Stream Taxonomy

| Stream | Source | Tags | Base Stack | Status |
| --- | --- | --- | --- | --- |
| **Official vLLM nightly** | `vllm/vllm-openai-rocm` | `nightly-<sha>`, `base-nightly` | vLLM's default ROCm base | Current upstream, lowest friction |
| **Self-built current** | `docker/Dockerfile.rocm` in vLLM repo | Build your own | `ARG_PYTORCH_ROCM_ARCH` configurable | Full control over gfx targeting |
| **AMD rocm/vllm-dev** | AMD's dev stream | `nightly`, `rocm721_torch210_triton36_preview_*`, etc. | AMD-curated ROCm/Torch/Triton combos | Weekly dev builds, multiple preview variants |
| **Navi-targeted base** | AMD historical docs | `rocm/vllm-dev:navi_base` (if available) | Explicit RDNA3 optimization path | ROCm 6.3 era; may be deprecated |

### Why These Matter

- **Official nightly:** Tests whether upstream vLLM has fixed RDNA3 kernel issues since 0.17.1 stable.
- **Self-built:** Allows explicit `ARG_PYTORCH_ROCM_ARCH=gfx1100` targeting, isolating the hardware arch selection variable.
- **AMD dev stream:** AMD publishes weekly previews with distinct Triton/rocBLAS combinations. The `rocm721_torch210_triton36_preview_*` tags bundle different kernel libraries than the stable bases.
- **Navi-targeted base:** Historical evidence that RDNA3 had a dedicated build path. If obtainable, confirms whether explicit Navi support improves throughput.

### Benchmark Plan — Four Tests in Order of Priority

All tests use `Qwen3.5-27B-AWQ` (same model), TP=2 (both XTX GPUs), standard benchmark prompt (300 tokens).

---

#### Test 1: Official vLLM ROCm Nightly

**Goal:** Determine if upstream vLLM has addressed RDNA3 Triton AWQ performance since 0.17.1 stable.

```bash
# Get latest nightly SHA
NIGHTLY_SHA=$(curl -s https://api.github.com/repos/vllm-project/vllm/commits?per_page=1 | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['sha'][:12])")
echo "Latest nightly SHA: $NIGHTLY_SHA"

# Pull and run
docker run -d --name audia-vllm-nightly \
  --device /dev/kfd \
  --device /dev/dri/renderD128 --device /dev/dri/renderD129 \
  --group-add video --group-add render --ipc host \
  -v /tmp/gpu_model_runner_patched.py:/usr/local/lib/python3.12/dist-packages/vllm/v1/worker/gpu_model_runner.py:ro \
  -v /opt/docker/services/llm_gateway/models-hf:/models:ro \
  -p 41091:8000 \
  -e ROCR_VISIBLE_DEVICES=0,1 -e HIP_VISIBLE_DEVICES=0,1 \
  -e HSA_OVERRIDE_GFX_VERSION=11.0.0 \
  vllm/vllm-openai-rocm:nightly-${NIGHTLY_SHA} \
  --model /models/hub/models--QuantTrio--Qwen3.5-27B-AWQ/snapshots/56f41874389615226dcd849ded92261a0286ff59 \
  --served-model-name Qwen3.5-27B-AWQ-nightly \
  --tensor-parallel-size 2 --quantization awq \
  --gpu-memory-utilization 0.95 --max-model-len 8192 --trust-remote-code

# Wait for startup
docker logs -f audia-vllm-nightly 2>&1 | grep -m1 "startup complete"

# Benchmark (2 runs)
python3 /tmp/bench_vllm2.py
```

**Expected result:** If recent commits fixed kernel issues, this should exceed 10.8 tok/s. If not, expect similar ~10.8 tok/s.

---

#### Test 2: Self-Built Current vLLM with Explicit gfx1100 Targeting

**Goal:** Test whether explicit architecture targeting during build improves kernel selection.

This requires cloning vLLM and building locally or in CI. Approximate command:

```bash
# Clone vLLM
git clone https://github.com/vllm-project/vllm.git
cd vllm

# Build with explicit gfx1100 targeting
docker build \
  --build-arg BASE_IMAGE=rocm/pytorch:latest \
  --build-arg ARG_PYTORCH_ROCM_ARCH=gfx1100 \
  -f docker/Dockerfile.rocm \
  -t audia-vllm-gfx1100:latest \
  .

# Run
docker run -d --name audia-vllm-gfx1100 \
  --device /dev/kfd \
  --device /dev/dri/renderD128 --device /dev/dri/renderD129 \
  --group-add video --group-add render --ipc host \
  -v /tmp/gpu_model_runner_patched.py:/usr/local/lib/python3.12/dist-packages/vllm/v1/worker/gpu_model_runner.py:ro \
  -v /opt/docker/services/llm_gateway/models-hf:/models:ro \
  -p 41091:8000 \
  -e ROCR_VISIBLE_DEVICES=0,1 -e HIP_VISIBLE_DEVICES=0,1 \
  audia-vllm-gfx1100:latest \
  --model /models/hub/models--QuantTrio--Qwen3.5-27B-AWQ/snapshots/56f41874389615226dcd849ded92261a0286ff59 \
  --served-model-name Qwen3.5-27B-AWQ-gfx1100-built \
  --tensor-parallel-size 2 --quantization awq \
  --gpu-memory-utilization 0.95 --max-model-len 8192 --trust-remote-code

# Wait and benchmark
docker logs -f audia-vllm-gfx1100 2>&1 | grep -m1 "startup complete"
python3 /tmp/bench_vllm2.py
```

**Expected result:** Explicit gfx1100 targeting may improve kernel selection. Could see 10.8–12+ tok/s if arch-specific optimization is meaningful.

---

#### Test 3: AMD rocm/vllm-dev:nightly

**Goal:** Test AMD's dev stream, which may bundle different ROCm/Torch/Triton combinations.

```bash
# Pull AMD dev stream nightly
docker pull rocm/vllm-dev:nightly

docker run -d --name audia-vllm-amd-dev \
  --device /dev/kfd \
  --device /dev/dri/renderD128 --device /dev/dri/renderD129 \
  --group-add video --group-add render --ipc host \
  -v /tmp/gpu_model_runner_patched.py:/usr/local/lib/python3.12/dist-packages/vllm/v1/worker/gpu_model_runner.py:ro \
  -v /opt/docker/services/llm_gateway/models-hf:/models:ro \
  -p 41091:8000 \
  -e ROCR_VISIBLE_DEVICES=0,1 -e HIP_VISIBLE_DEVICES=0,1 \
  rocm/vllm-dev:nightly \
  python3 -m vllm.entrypoints.openai.api_server \
  --model /models/hub/models--QuantTrio--Qwen3.5-27B-AWQ/snapshots/56f41874389615226dcd849ded92261a0286ff59 \
  --served-model-name Qwen3.5-27B-AWQ-amd-dev \
  --tensor-parallel-size 2 --quantization awq \
  --gpu-memory-utilization 0.95 --max-model-len 8192 --trust-remote-code

docker logs -f audia-vllm-amd-dev 2>&1 | grep -m1 "startup complete"
python3 /tmp/bench_vllm2.py
```

> Note: AMD dev images may use different entry points. Adjust if needed.

---

#### Test 4: AMD rocm/vllm-dev with Triton Preview Tag

**Goal:** Test AMD's explicit Triton preview builds, which bundle newer Triton + rocBLAS/hipBLASLt combinations.

```bash
# List available preview tags
docker search rocm/vllm-dev 2>/dev/null | grep preview || curl -s https://hub.docker.com/v2/repositories/rocm/vllm-dev/tags | python3 -c "import json,sys; tags=json.load(sys.stdin)['results']; [print(t['name']) for t in tags if 'preview' in t['name']]" | head -5

# Use one of the preview tags (e.g., rocm721_torch210_triton36_preview_20260328)
docker pull rocm/vllm-dev:rocm721_torch210_triton36_preview_20260328

docker run -d --name audia-vllm-amd-preview \
  --device /dev/kfd \
  --device /dev/dri/renderD128 --device /dev/dri/renderD129 \
  --group-add video --group-add render --ipc host \
  -v /tmp/gpu_model_runner_patched.py:/usr/local/lib/python3.12/dist-packages/vllm/v1/worker/gpu_model_runner.py:ro \
  -v /opt/docker/services/llm_gateway/models-hf:/models:ro \
  -p 41091:8000 \
  -e ROCR_VISIBLE_DEVICES=0,1 -e HIP_VISIBLE_DEVICES=0,1 \
  rocm/vllm-dev:rocm721_torch210_triton36_preview_20260328 \
  python3 -m vllm.entrypoints.openai.api_server \
  --model /models/hub/models--QuantTrio--Qwen3.5-27B-AWQ/snapshots/56f41874389615226dcd849ded92261a0286ff59 \
  --served-model-name Qwen3.5-27B-AWQ-amd-preview \
  --tensor-parallel-size 2 --quantization awq \
  --gpu-memory-utilization 0.95 --max-model-len 8192 --trust-remote-code

docker logs -f audia-vllm-amd-preview 2>&1 | grep -m1 "startup complete"
python3 /tmp/bench_vllm2.py
```

---

### Testing Expectations

These tests target the **runtime kernel selection layer** beneath vLLM's application code. Each build stream makes different choices about:

- Which Triton version and kernel library to include
- Which rocBLAS/hipBLASLt backend to prioritize
- Architecture-specific optimizations (gfx1100 RDNA3)

**Success criteria:** Any result > 11 tok/s indicates improved kernel efficiency. Results ≥ 15 tok/s would suggest a major upstream fix. Results still at ~10.8 tok/s confirm the Triton AWQ dequantization path remains the limiting factor across all builds.

---

## llama.cpp ROCm Optimization — Exhaustive Test Plan (2026-03-29)

While Vulkan dominates for single-sequence throughput (26.41 tok/s), llama.cpp ROCm remains a fallback. Previous testing (2026-03-28) showed:

- `ggml-latest`, `ggml-b8429`, `ggml-git-main`, `lemonade-b1217`: all ~21 tok/s
- All four tested variants achieved identical throughput on the same hardware
- No investigation into runtime tuning, build flags, or GEMM kernel selection

This session's vLLM research identified **build stack variations as a meaningful variable**. The same applies to llama.cpp: different ROCm base versions, different rocBLAS/hipBLASLt kernel selections, and RDNA3-specific optimizations can affect throughput.

### llama.cpp ROCm Build Variables

llama.cpp can be built via:

1. **Prebuilt releases** (`ggml-org` GitHub releases) — Fast, tested binaries
2. **Custom CMake builds** — Full control over `AMDGPU_TARGETS`, `DGGML_HIPBLAS`, rocBLAS variants
3. **Docker multistage** — Isolate build environment from runtime
4. **AMD rocm/rocm-pytorch base images** — Different ROCm versions and kernel libraries

### Exhaustive Test Matrix

Test the following untested combinations on `Qwen3.5-27B-Q6_K.gguf`, ROCm0+ROCm1 (both XTX), flash-attn on, Q8_0 KV cache:

| # | Test Name | Build Source | ROCm Version | hipBLAS | AMDGPU_TARGETS | Expected | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | **Baseline Prebuilt Latest** | `ggml-org` releases b8565+ | System default | auto | auto | ~21 | Confirm current baseline |
| 2 | **Manual CMake b8565 + ROCm 7.2** | Self-build from source | 7.2 explicit | ON | `gfx1030;gfx1100` | 21–22? | Explicit arch targeting for RDNA3 |
| 3 | **Manual CMake b8565 + ROCm 7.2 + rocBLAS** | Self-build from source | 7.2 explicit | rocBLAS only | `gfx1030;gfx1100` | 21–23? | rocBLAS may outperform hipBLASLt on RDNA3 |
| 4 | **Manual CMake b8565 + hipBLASLt only** | Self-build from source | 7.2 explicit | hipBLASLt only (no rocBLAS) | `gfx1030;gfx1100` | 21–22? | hipBLASLt-only path (isolate backend) |
| 5 | **Manual CMake b8565 + gfx1100-only** | Self-build from source | 7.2 explicit | ON | `gfx1100` | 21–22? | Drop gfx1030; focus kernels on 7900 XTX only |
| 6 | **Manual CMake ROCm 6.3 era** | Self-build from ROCm 6.3 era source | 6.3 | ON | `gfx1100` | 19–21? | Older kernels; check for regressions vs 7.2 |
| 7 | **Latest upstream (main)** | git clone + CMake from latest main | System default | ON | `gfx1030;gfx1100` | 21–23? | Test latest unreleased optimizations |
| 8 | **Tensor cores / FP8 fallback test** | b8565 with `-DGGML_CUDA_FA_ALL_QUANTS=ON` (if applicable) | 7.2 | ON | `gfx1030;gfx1100` | 21–22? | Check if compute capability flags help RDNA3 |
| 9 | **Single GPU (GPU[1] XTX only)** | b8565 prebuilt | 7.2 | auto | auto | 13–15? | Measure 1 GPU performance; compare 2-GPU scaling |
| 10 | **All 3 GPUs (unequal split)** | b8565 prebuilt + balanced tensor split | 7.2 | auto | auto | 18–20? | Confirm 6900 XT bottleneck; measure penalty |

### Test Execution Commands

All tests use the same prompt, model, and benchmark methodology. Tests 1–8 run inside the llama-cpp container via `docker exec` (port 41080). Tests 9–10 run standalone.

---

#### Test 1: Baseline Prebuilt Latest (b8565+)

```bash
# Pull latest prebuilt from ggml-org
LATEST_RELEASE=$(curl -s https://api.github.com/repos/ggml-org/llama.cpp/releases/latest | python3 -c "import json,sys; print(json.load(sys.stdin)['tag_name'])")
echo "Testing: $LATEST_RELEASE"

# Inside audia-llama-cpp container, start backend
docker exec audia-llama-cpp \
  env LD_LIBRARY_PATH=/app/runtime-root/rocm/lib:/opt/rocm/lib \
      ROCBLAS_TENSILE_LIBPATH=/opt/rocm/lib/rocblas/library \
  /app/runtime-root/rocm/bin/llama-server-rocm \
  --port 41080 --host 0.0.0.0 \
  --model /app/models/gguf/qwen3.5-27B/Qwen3.5-27B-Q6_K.gguf \
  --ctx-size 131072 \
  --device ROCm0,ROCm1 \
  --split-mode layer --tensor-split 1,1 \
  --gpu-layers 99 --parallel 1 \
  --flash-attn on --temp 0 --top-p 0.9 --top-k 20 \
  --threads 8 --threads-batch 24 \
  --batch-size 512 --ubatch-size 512 \
  --cache-type-k q8_0 --cache-type-v q8_0 &

sleep 30 && python3 /tmp/bench_qwen27.py
```

**Expected:** ~21 tok/s (baseline confirmation).

---

#### Test 2: Manual CMake with Explicit gfx1030;gfx1100 Targeting

This requires building inside the container or on the server. Abbreviated steps:

```bash
# Inside container or on server with ROCm 7.2
git clone https://github.com/ggml-org/llama.cpp.git llama-rocm-gfx-test
cd llama-rocm-gfx-test
git checkout b8565  # Use known good commit

# Build with explicit RDNA3 targets
mkdir build && cd build
cmake .. \
  -DLLAMA_BUILD_SERVER=ON \
  -DGGML_HIPBLAS=ON \
  -DAMDGPU_TARGETS="gfx1030;gfx1100" \
  -DCMAKE_HIP_ARCHITECTURES="gfx1030;gfx1100" \
  -DCMAKE_BUILD_TYPE=Release

cmake --build . --config Release --parallel $(nproc)

# Copy binary to llama-cpp container or run standalone
cp build/bin/llama-server /tmp/llama-server-gfx-explicit

# Test
/tmp/llama-server-gfx-explicit \
  --port 41080 --host 0.0.0.0 \
  --model /app/models/gguf/qwen3.5-27B/Qwen3.5-27B-Q6_K.gguf \
  --ctx-size 131072 \
  --device ROCm0,ROCm1 \
  --split-mode layer --tensor-split 1,1 \
  --gpu-layers 99 --parallel 1 \
  --flash-attn on --temp 0 --top-p 0.9 --top-k 20 \
  --threads 8 --threads-batch 24 \
  --batch-size 512 --ubatch-size 512 \
  --cache-type-k q8_0 --cache-type-v q8_0 &

sleep 30 && python3 /tmp/bench_qwen27.py
```

**Expected:** 21–22 tok/s. Explicit arch targeting may help kernel selection; if it does, continue with other arch-specific tests.

---

#### Test 3: rocBLAS vs hipBLASLt — rocBLAS Only

```bash
# Same build as Test 2, but compile with rocBLAS preference
# (rocBLAS is HIP's native BLAS; hipBLASLt is the newer wrapper)

cmake .. \
  -DLLAMA_BUILD_SERVER=ON \
  -DGGML_HIPBLAS=ON \
  -DGGML_USE_ROCBLAS=ON \
  -DAMDGPU_TARGETS="gfx1030;gfx1100" \
  -DCMAKE_HIP_ARCHITECTURES="gfx1030;gfx1100" \
  -DCMAKE_BUILD_TYPE=Release

cmake --build . --config Release --parallel $(nproc)

# Run as Test 2
```

**Expected:** 21–23 tok/s. rocBLAS is battle-tested on AMD; hipBLASLt may have RDNA3 gaps.

---

#### Test 4: hipBLASLt Only (no rocBLAS fallback)

```bash
cmake .. \
  -DLLAMA_BUILD_SERVER=ON \
  -DGGML_HIPBLAS=ON \
  -DGGML_USE_ROCBLAS=OFF \
  -DAMDGPU_TARGETS="gfx1030;gfx1100" \
  -DCMAKE_HIP_ARCHITECTURES="gfx1030;gfx1100" \
  -DCMAKE_BUILD_TYPE=Release

cmake --build . --config Release --parallel $(nproc)
```

**Expected:** 21–22 tok/s or slower. Isolates hipBLASLt performance if no rocBLAS fallback.

---

#### Test 5: gfx1100-Only Build (drop gfx1030)

```bash
cmake .. \
  -DLLAMA_BUILD_SERVER=ON \
  -DGGML_HIPBLAS=ON \
  -DAMDGPU_TARGETS="gfx1100" \
  -DCMAKE_HIP_ARCHITECTURES="gfx1100" \
  -DCMAKE_BUILD_TYPE=Release

cmake --build . --config Release --parallel $(nproc)
```

**Expected:** 21–22 tok/s (same, since only XTX GPUs are used). Tests whether dropping gfx1030 allows more focused kernel optimization.

---

#### Test 6: ROCm 6.3-Era Build

If a ROCm 6.3 container is available:

```bash
# In ROCm 6.3 container
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
git checkout b8200  # Approximate ROCm 6.3 era commit

cmake .. \
  -DLLAMA_BUILD_SERVER=ON \
  -DGGML_HIPBLAS=ON \
  -DAMDGPU_TARGETS="gfx1100" \
  -DCMAKE_BUILD_TYPE=Release

cmake --build . --config Release --parallel $(nproc)
```

**Expected:** 19–21 tok/s. Older kernels may regress; establishes whether vLLM's ROCm 7.2 standard is optimal.

---

#### Test 7: Latest Upstream (main branch)

```bash
git clone https://github.com/ggml-org/llama.cpp.git llama-main
cd llama-main
# Stay on main (no checkout)

cmake .. \
  -DLLAMA_BUILD_SERVER=ON \
  -DGGML_HIPBLAS=ON \
  -DAMDGPU_TARGETS="gfx1030;gfx1100" \
  -DCMAKE_BUILD_TYPE=Release

cmake --build . --config Release --parallel $(nproc)
```

**Expected:** 21–23 tok/s. Main branch may include unreleased RDNA3 improvements.

---

#### Test 8: Compute Capability Fallback Flags

```bash
# Test if compute capability flags help (similar to vLLM's HSA_OVERRIDE)

cmake .. \
  -DLLAMA_BUILD_SERVER=ON \
  -DGGML_HIPBLAS=ON \
  -DAMDGPU_TARGETS="gfx1030;gfx1100" \
  -DCMAKE_HIP_ARCHITECTURES="gfx1030;gfx1100" \
  -DCMAKE_BUILD_TYPE=Release \
  -DHIP_PATH=/opt/rocm

cmake --build . --config Release --parallel $(nproc)

# At runtime, try:
HSA_OVERRIDE_GFX_VERSION=11.0.0 /tmp/llama-server-...
```

**Expected:** 21–22 tok/s (no change expected; tests whether HSA_OVERRIDE helps llama.cpp like it does vLLM).

---

#### Test 9: Single GPU (GPU[1] / XTX only)

```bash
docker exec audia-llama-cpp \
  env LD_LIBRARY_PATH=/app/runtime-root/rocm/lib:/opt/rocm/lib \
      ROCBLAS_TENSILE_LIBPATH=/opt/rocm/lib/rocblas/library \
      ROCR_VISIBLE_DEVICES=1 \
  /app/runtime-root/rocm/bin/llama-server-rocm \
  --port 41080 --host 0.0.0.0 \
  --model /app/models/gguf/qwen3.5-27B/Qwen3.5-27B-Q6_K.gguf \
  --ctx-size 131072 \
  --device ROCm0 \
  --gpu-layers 99 --parallel 1 \
  --flash-attn on --temp 0 --top-p 0.9 --top-k 20 \
  --threads 8 --threads-batch 24 \
  --batch-size 512 --ubatch-size 512 \
  --cache-type-k q8_0 --cache-type-v q8_0 &

sleep 30 && python3 /tmp/bench_qwen27.py
```

**Expected:** 13–15 tok/s. Single GPU = half the memory bandwidth; measure 2-GPU scaling efficiency.

---

#### Test 10: All 3 GPUs with Balanced Split

```bash
docker exec audia-llama-cpp \
  env LD_LIBRARY_PATH=/app/runtime-root/rocm/lib:/opt/rocm/lib \
      ROCBLAS_TENSILE_LIBPATH=/opt/rocm/lib/rocblas/library \
  /app/runtime-root/rocm/bin/llama-server-rocm \
  --port 41080 --host 0.0.0.0 \
  --model /app/models/gguf/qwen3.5-27B/Qwen3.5-27B-Q6_K.gguf \
  --ctx-size 131072 \
  --device ROCm0,ROCm1,ROCm2 \
  --split-mode layer --tensor-split 16,24,24 \
  --gpu-layers 99 --parallel 1 \
  --flash-attn on --temp 0 --top-p 0.9 --top-k 20 \
  --threads 8 --threads-batch 24 \
  --batch-size 512 --ubatch-size 512 \
  --cache-type-k q8_0 --cache-type-v q8_0 &

sleep 30 && python3 /tmp/bench_qwen27.py
```

**Expected:** 18–20 tok/s (similar to 3-GPU Vulkan test, which yielded 21.98 tok/s but with MUCH larger memory footprint). ROCm should show similar bottlenecking behavior.

---

### Summary Table — llama.cpp ROCm Test Grid

| Test | Variable | Expected tok/s | Pass/Fail Threshold |
| --- | --- | --- | --- |
| 1 | Baseline prebuilt | 21.0 | ±0.5 |
| 2 | Explicit gfx1030;gfx1100 | 21.5–22.5 | >21.0 = win |
| 3 | rocBLAS only | 21.5–23.0 | >21.5 = win |
| 4 | hipBLASLt only | 21.0–21.5 | >21.0 = win |
| 5 | gfx1100-only | 21.0 | ±0.5 |
| 6 | ROCm 6.3-era | 19.0–21.0 | >20.0 = no regression |
| 7 | Latest main | 21.5–23.0 | >21.0 = win |
| 8 | HSA_OVERRIDE flag | 21.0 | No change expected |
| 9 | Single GPU | 13.0–15.0 | Measure scaling |
| 10 | All 3 GPUs | 18.0–20.0 | Measure bottleneck |

### Success Criteria

- **Any result > 22 tok/s** = meaningful kernel improvement found. Continue testing that variable.
- **rocBLAS-only or main-branch > 22 tok/s** = strong candidate for rollout.
- **All tests ~21 tok/s** = confirm Vulkan's 26.41 tok/s as the persistent winner; ROCm kernel quality is the gap, not fixable via build flags.

---

## Model Path Reference

Expected performance by quantization type on RX 7900 XTX (gfx1100), based on current upstream docs and this session's measurements:

| Quantization | Expected vLLM result | Confidence | Reason |
| --- | --- | --- | --- |
| AWQ INT4 (any model family) | ~10 tok/s | High | Same Triton AWQ kernel path |
| Dense BF16/FP16 | Unknown — likely better | Medium | No AWQ dequantization overhead; blocked on this hardware (model too large for TP=2, TP=3 invalid, cpu-offload broken in v1) — test with a 14B model on TP=2 |
| GPTQ INT4 | Unknown — must test | Low | Conflicting AMD/vLLM docs |
| FP8 | Not recommended | High | `supports_fp8()` = False on gfx1100; known crash bug |
| GGUF (in vLLM) | Likely worse than BF16 | High | Explicitly experimental and under-optimized in vLLM docs |
| GGUF (in llama.cpp) | 21–26 tok/s | High | Confirmed; current winner for single-user |

If all remaining tests still leave vLLM far below llama.cpp Vulkan, stop. Based on current upstream state there is no hidden setting that will close a 2.4× gap on RX 7900 XTX for single-stream AWQ inference.
