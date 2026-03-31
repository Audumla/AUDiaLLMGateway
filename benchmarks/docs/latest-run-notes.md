# Latest Benchmark Run Notes

This note captures the most recent manual backend sweep and the fixes required
to keep the benchmark harness moving.

## Standard compare model

All future backend comparison runs should use the same smaller Qwen3.5 target:

- `Qwen/Qwen3.5-4B` for HF-serving backends
- `Qwen3.5-4B-Q5_K_XL.gguf` for llama.cpp / Ollama GGUF-backed runs

That keeps the backend comparisons apples-to-apples and avoids mixing 0.6B,
25B, and 27B results into the same performance decision.

## 2026-03-30 03:37Z sweep

- `llama-swap` on `ministral3b-vision`: 194.18 eval tok/s
- `vLLM AWQ` on `Qwen/Qwen3-0.6B`: 113.7 eval tok/s
- `Ollama ROCm` on `qwen25b`: 238.26 eval tok/s
- `vLLM BF16` on `Qwen/Qwen3-0.6B` was still part of the sweep, but this run
  dropped the connection mid-request and should be rerun before treating BF16 as
  stable on the live host
- `TGI ROCm`, `SGLang ROCm`, and `Aphrodite` still failed with connection
  refused after the runner cleaned up their containers

## Confirmed Working

- `llama-swap` on `ministral3b-vision`
- `vLLM AWQ` on `Qwen/Qwen3-0.6B`
- `vLLM BF16` on `Qwen/Qwen3-0.6B`
- `Ollama ROCm` on `qwen25b`

## Retested Failures

- `TGI ROCm` on `ghcr.io/huggingface/text-generation-inference:sha-9f38d93-rocm`
  now reaches shard startup, but still fails with `HIP error: invalid device
  function` and `ShardCannotStart`
- `SGLang ROCm` remains MI300-focused in the official docs and continues to exit
  on gfx1100 startup paths
- `Aphrodite` remains CUDA-dependent on this box and fails on `libcuda.so.1`

## Confirmed Results

- `llama-swap` `ministral3b-vision`: 164.84 eval tok/s
- `vLLM AWQ` `Qwen/Qwen3-0.6B`: 120.36 eval tok/s
- `vLLM BF16` `Qwen/Qwen3-0.6B`: 120.24 eval tok/s
- `Ollama ROCm` `qwen25b`: 158.27 eval tok/s

## 2026-03-30 05:18Z single-model compare sweep

- Shared compare model:
  - `Qwen/Qwen3.5-4B` for HF backends
  - `Qwen3.5-4B-Q5_K_XL.gguf` for llama.cpp / Ollama
- `llama-swap` on `qwen3-5-4b-ud-q5-k-xl-vision1`: 122.39 eval tok/s
- `Ollama ROCm` on `qwen35b`: 84.19 eval tok/s
- `vLLM`, `TGI`, `SGLang`, and `Aphrodite` all failed to stay healthy on the current live image set for this compare model

## Confirmed Working on the Shared Compare Model

- `llama-swap` on `qwen3-5-4b-ud-q5-k-xl-vision1`
- `Ollama ROCm` on `qwen35b`

## Retested Failures on the Shared Compare Model

- `vLLM` exited before readiness on `Qwen/Qwen3.5-4B`
- `TGI ROCm` still fails during startup and then hits the missing `/usr/src/.venv/bin/activate` path in the image entrypoint
- `SGLang ROCm` exited before readiness on `Qwen/Qwen3.5-4B`
- `Aphrodite` exited before readiness on `Qwen/Qwen3.5-4B`

## 2026-03-30 backend recovery pass

- `vLLM` came back online once `AUDIA_ENABLE_VLLM=true` was set in the live
  compose environment. The service responded successfully on the small
  `Qwen/Qwen3-0.6B` path.
- `TGI` on ROCm was retried with both `ghcr.io/huggingface/text-generation-inference:3.3.4-rocm`
  and `latest-rocm`.
  - `Qwen/Qwen3.5-4B` fails with `Unsupported model type qwen3_5`
  - `Qwen/Qwen2.5-0.5B-Instruct` gets further but fails with `HIP error: invalid device function`
- `SGLang` remains unconfirmed on gfx1100; the available ROCm image lane still
  looks MI300-focused.
- `Aphrodite` remains blocked until a non-CUDA AMD path is available.

## 2026-03-30 Zinc source-build validation

- Zinc was cloned into `/srv/llm-models/zinc-src` and built from source on the
  server with a staged toolchain:
  - Zig 0.15.2
  - Bun 1.3.11
  - Vulkan SDK 1.4.341.1
- The build needed local Vulkan include/library staging because the server has
  `vulkaninfo` but not the unversioned `libvulkan.so` or Vulkan headers in a
  standard search path.
- `zig build` passed once shader compilation was enabled against the staged
  `glslc`.
- `zig build test` passed.
- `./zig-out/bin/zinc --check` reached `READY WITH WARNINGS` after the shader
  assets were generated.
- The warnings were environment-related, not fatal:
  - Mesa Vulkan package detection is absent in the current shell
  - GECC / RAS reports `Enabled (-1)`
- This confirmed Zinc as a working, source-built Vulkan-native AMD lane on the
  host, separate from ROCm.

## Confirmed Results on the Shared Compare Model

- `llama-swap` `qwen3-5-4b-ud-q5-k-xl-vision1`: 122.39 eval tok/s
- `Ollama ROCm` `qwen35b`: 84.19 eval tok/s

## Harness Fixes Applied

- TGI health checks now stop early when the container exits instead of waiting
  for the full timeout.
- TGI now tries a single-shard fallback after the multi-shard launch fails.
- Ollama now creates its `Modelfile` inside the container before calling
  `ollama create`.
- The benchmark client now reads Ollama token counts from `eval_count` and
  `prompt_eval_count`.

## Still Blocked

- TGI ROCm: the alternate official ROCm tag gets further than the previous one
  but still dies during shard startup on gfx1100.
- SGLang ROCm: official ROCm images remain MI300-oriented rather than gfx1100
  friendly.
- Aphrodite: current image requires `libcuda.so.1`, so it is not usable on this
  ROCm-only path.

## Interpretation

The repeatable path is now good enough for the backends that actually fit this
hardware:

- keep llama.cpp Vulkan as the interactive winner
- keep llama.cpp ROCm preview as the ROCm fallback
- keep vLLM as a serving/concurrency candidate
- keep Ollama in the catalog only if we continue to use a ROCm-capable image

The comparison pass now standardizes on the Qwen3.5-4B family so each backend
is measured against the same smaller model instead of a mix of 0.6B, 4B, 25B,
and 27B runs.

## 2026-03-30 qwen27 dual-XTX retest

This pass switched back to the real target model on the two 7900 XTX cards:

- `Qwen/Qwen3.5-27B` for HF-backed engines
- `Qwen3.5-27B-Q6_K.gguf` for llama.cpp and Ollama

### llama.cpp engine variants

The qwen27 llama.cpp engine set produced usable warm-state results before the
container was restarted:

- `qwen27-rocm-ggml-b8429`: 20.92 tok/s on the warm run, with an earlier run at 9.98 tok/s
- `qwen27-rocm-ggml-git-main`: 9.85 tok/s
- `qwen27-rocm-lemonade-b1217`: 9.97 tok/s
- `qwen3.5-27b-(96k-Q6)`: 6.97 tok/s
- `qwen3.5-27b-(96k-Q6)-rocm-latest`: 9.84 tok/s

After a fresh restart of `audia-llama-cpp`, the same qwen27 engine variants
started returning HTTP 502 and `ExitError >> exit status 1`, so the current
llama.cpp qwen27 path still needs a reproducibility pass.

### Ollama

- `qwen27b` on `Ollama ROCm`: 18.12 tok/s

This run completed successfully and is the cleanest confirmed qwen27 result in
the current pass.

### vLLM regression

- `bench-vllm-awq` started and resolved `Qwen3_5ForConditionalGeneration`, but
  the engine core failed during qwen27 warm-up with an assertion in
  `causal_conv1d_update`
- `bench-vllm-27b` still fails the BF16 path with HIP OOM / engine-core failure

### Zinc

Zinc can load the qwen27 GGUF, but on both GPU1 and GPU2 it crashes inside
`libvulkan_radeon.so` with an arithmetic exception before any prompt can
complete. The direct CLI run confirmed the crash on both 7900 XTX cards, so
Zinc remains a promising experimental lane but not a usable qwen27 benchmark
path yet.

## 2026-03-31 ROCm 7.2.1 lane add

This pass applied the new ROCm release first through a prebuilt lane, then
through a local-source fallback lane, and added both into the benchmark
catalog/matrix.

### Prebuilt first

- Release discovery confirmed `ROCm/ROCm` `rocm-7.2.1` is published as a
  release marker with no direct llama.cpp binary assets.
- Prebuilt benchmark lane therefore used ggml ROCm release assets with the
  qwen27 profile:
  - engine `qwen3.5-27b-(96k-Q6)-rocm-latest`
  - result `9.98 tok/s`

### Local build fallback

- Source build lane used `ggml-org/llama.cpp` `b8583` inside
  `rocm/dev-ubuntu-24.04:7.2.1`.
- First build came up CPU-only until `GGML_HIP=ON` and `GGML_HIPBLAS=ON` were
  enabled.
- CMake dependencies needed explicit `hipblas-dev`, `rocblas-dev`,
  `hipblaslt-dev`.
- Runtime lane initially failed on missing `libhipblas.so.3` and was fixed by
  installing the same ROCm libs in the run container and setting:
  - `LD_LIBRARY_PATH`
  - `ROCBLAS_TENSILE_LIBPATH`
- Local-source benchmark lane result:
  - engine `ggml-b8583-rocm-7.2.1-local`
  - result `21.49 tok/s`

### Result artifact

- Full artifact: `benchmarks/data/backend-benchmarks/20260331_rocm721_prebuilt_local_results.json`

## 2026-03-31 Lychee Strix Halo lane registration

- Added a new architecture-scoped llama.cpp source lane:
  `https://github.com/Lychee-Technology/llama-cpp-for-strix-halo/releases`
- Latest observed release metadata:
  - tag `b8580`
  - asset `llama-cpp-b8580-rocm-7.2.1-gfx1151.tar.xz`
- This lane is cataloged as `gfx1151`-targeted and tracked separately from the
  benchmark host (`gfx1100` dual RX 7900 XTX).
- Policy for this lane is unchanged:
  - prebuilt first on matching architecture
  - source-build fallback on non-matching architecture

## 2026-03-31 vLLM ROCm 7.2.1 wheel lane

The latest vLLM ROCm wheel pass followed the documented ROCm nightly wheel lane
instead of the generic CUDA nightly lane:

- install lane: `https://wheels.vllm.ai/rocm/nightly/${VLLM_ROCM_VARIANT}`
- build image: `local/vllm-rocm721-wheel:nightly`

Results:

- `Qwen/Qwen3-0.6B` served successfully at `75.05 eval tok/s`
- `Qwen/Qwen3.5-4B` still failed during engine startup with HIP OOM in the
  multimodal attention path

This confirms the ROCm nightly wheel lane is valid for small-model smoke tests on
this host, but it still needs triage for the 4B compare model.

## 2026-03-31 qwen27 context follow-up on the ROCm wheel lane

The qwen27 follow-up used the same ROCm 7.2.1 wheel image and the same dual-XTX
topology, but reduced context settings to see whether the model would fit more
comfortably in VRAM.

- `max_model_len=4096`:
  - model loaded and compiled part of the graph path
  - engine failed during KV-cache setup with page-size unification error
- `max_model_len=2048`:
  - same failure mode after load and compile

Net: the wheel lane still works for small models, but qwen27 on this build is
blocked by the engine's KV-cache page-size handling rather than plain VRAM
pressure.

## 2026-03-31 Qwen3.5 text-only follow-up on the ROCm wheel lane

The text-only follow-up used the correct cached snapshots for both Qwen3.5-4B
and Qwen3.5-27B on the ROCm 7.2.1 wheel lane.

- Qwen3.5-4B:
  - `--language-model-only` successfully suppressed multimodal profiling
  - engine still failed during KV-cache page-size unification
- Qwen3.5-27B:
  - `--language-model-only` and a 2096-token batching guardrail still failed
  - same KV-cache page-size unification error

Net: the wheel lane is healthy, but the Qwen3.5 family is still blocked in
vLLM 0.18.1 by hybrid KV-cache setup on this host.

## 2026-03-31 vLLM 0.17.1 rollback lane

The official ROCm image lane was then checked separately so the rollback path
stays distinct from the v0.18.x regression lane.

- `vllm/vllm-openai-rocm:latest` at v0.17.1
  - `/v1/models` responded inside the container
  - `Qwen3.5-27B-AWQ` on the dual 7900 XTX host returned a chat completion at
    `max_model_len=2048` with `--language-model-only`
  - standard compare prompt benchmark: `3.41 tok/s` over `300` completion
    tokens
  - keep this lane as the current recovery path for Qwen3.5 until the v0.18.x
    hybrid KV-cache regression is fixed upstream
- `Qwen3.5-4B` was also confirmed earlier on the same rollback lane
  - it started and returned a completion on the same host topology
  - this makes 0.17.1 the better known-good reference for Qwen3.5 serving on
    this server

## 2026-03-31 Vulkan warm recheck

I re-ran the managed llama.cpp Vulkan qwen27 lane on the dual 7900 XTX host to
get a fresh line-in-the-sand comparison.

- first request on the live backend included cold-path overhead:
  - `13.83 tok/s`
- second request on the warmed backend:
  - `26.28 tok/s`

Net: the warmed managed lane matches the known-good Vulkan class result and is
still the current interactive winner on this host.

## 2026-03-31 implementation refresh pass

This pass reviewed updated upstream implementations and tested updated lanes
against the same qwen benchmark pattern used in prior runs.

- Lemonade (`b1224`, `gfx110X` prebuilt):
  - startup initially failed on missing `libatomic.so.1` on openSUSE
  - fixed by installing host package `libatomic1`
  - qwen27 benchmark result: `21.85 tok/s`
- Lychee Strix Halo (`b8580`, `gfx1151` prebuilt):
  - startup initially failed on missing `libomp.so`
  - after dependency fixes it still exited with `Illegal instruction` on this
    dual-XTX `gfx1100` host
  - attempted source fallback from the Lychee repo was blocked because the repo
    is a packaging/prebuilt wrapper (no direct CMake source tree)
  - remains architecture-scoped and blocked on current hardware
- vLLM (`v0.18.0` image):
  - Qwen3.5-4B engine init failed with HIP OOM in mm-attention path
  - no usable benchmark result produced on this pass
- TGI:
  - explicit `3.3.7-rocm` tag was not found in GHCR

Result artifact:

- `benchmarks/data/backend-benchmarks/20260331_impl_refresh_results.json`
