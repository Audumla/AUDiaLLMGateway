# Backend Source Catalog

This page is the maintained index for backend source channels and prebuilt
availability. It does not store engine compatibility data.

Use this together with:

- [Benchmark profile catalog](../data/backend-benchmarks/benchmark-profiles.yaml)
- [Engine version catalog](engine-version-catalog.md)
- [Compatibility matrix](../data/backend-benchmarks/compatibility-matrix.yaml)
- [Performance history](../../specifications/docs/llm-backend-performance.md)
- [Build catalog](../../specifications/docs/llm-backend-builds.md)

## What this catalog records

- whether a backend has a maintained prebuilt channel
- whether the AMD path is source-build only
- which source/release channels exist for each backend family

## Current high-signal entries

| Backend family | Maintained prebuilt? | Current state on this host | Notable source channel |
| --- | --- | --- | --- |
| llama.cpp | Yes | Working | `ggml-org/llama.cpp`, `ROCm/llama.cpp`, `ROCm/ROCm` release lane, `lemonade-sdk/llamacpp-rocm`, `Lychee-Technology/llama-cpp-for-strix-halo` |
| vLLM | Yes, Docker-based | Working on small models; Qwen3.5-4B still regresses | `vllm/vllm-openai-rocm`, `rocm/vllm-dev`, ROCm wheel nightly lane |
| TGI | Yes, Docker-based | Blocked on gfx1100 compare profile | `ghcr.io/huggingface/text-generation-inference` |
| SGLang | Yes, Docker-based | Blocked / MI300-targeted | `lmsysorg/sglang` ROCm images |
| Ollama | Yes, Docker-based | Working | `ollama/ollama:rocm` |
| Aphrodite | No confirmed AMD prebuilt | Blocked | source build only |
| Zinc | No confirmed AMD prebuilt | Working from source | `zolotukhin/zinc` |

## How to keep it current

1. Add new source or release channels here first.
1. Record engine/version compatibility in `engine-version-catalog.md`.
1. Update the compatibility matrix with current working/blocked state.
1. Record the change with the changelog tool so we do not lose the trail.

## Latest addition

- Added ROCm `rocm-7.2.1` runtime release lane to the backend catalog.
- The ROCm release entry itself is a release marker (no direct llama.cpp assets),
  so the prebuilt test lane continues to use ggml ROCm assets while local source
  builds run against the ROCm 7.2.1 container/runtime lane.
- Added Lychee Strix Halo prebuilt lane (`b8580`, `gfx1151`) as an
  architecture-scoped source channel.
- Added the documented vLLM ROCm nightly wheel lane (`rocm721`) and recorded
  the working small-model run on `Qwen/Qwen3-0.6B`.
- Added the vLLM ROCm 0.17.1 rollback lane and confirmed it can serve
  `Qwen3.5-27B-AWQ` on the dual-XTX host with `max_model_len=2048`.
