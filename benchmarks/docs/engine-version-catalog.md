# Engine Version Catalog

This page records which engine versions work with which backend systems. It is
kept separate from the backend source catalog so source channels and engine
compatibility do not get mixed together.

Use this together with:

- [Backend source catalog](backend-catalog.md)
- [Benchmark profile catalog](../data/backend-benchmarks/benchmark-profiles.yaml)
- [Compatibility matrix](../data/backend-benchmarks/compatibility-matrix.yaml)
- [Performance history](../../specifications/docs/llm-backend-performance.md)

## What this catalog records

- engine version or build label
- the backend system(s) it is known to work with
- whether that version is current, historical, regression-only, or blocked

## Current shape

| Engine | Version | Backend systems | State |
| --- | --- | --- | --- |
| llama.cpp | `current_release` | `llamacpp_vulkan_current` | working |
| llama.cpp | `rocm_gfx1100_preview` | `llamacpp_rocm_preview` | working |
| llama.cpp | `rocm_7_2_1_prebuilt_lane` | `llamacpp_rocm72_prebuilt` | working |
| llama.cpp | `rocm_7_2_1_local_source_build` | `llamacpp_rocm721_local_build` | working |
| llama.cpp | `lychee_strix_halo_b8580_gfx1151` | `llamacpp_rocm_lychee_strix_halo` | architecture scoped |
| llama.cpp | `ggml_b8429` | `llamacpp_rocm_ggml_b8429` | historical working |
| llama.cpp | `ggml_git_main` | `llamacpp_rocm_ggml_git_main` | historical working |
| llama.cpp | `lemonade_b1217` | `llamacpp_rocm_lemonade_b1217` | historical working |
| vLLM | `rocm_current` | `vllm_rocm_current` | working on small models |
| vLLM | `rocm_0_17_1_rollback` | `vllm_rocm0171_rollback` | working |
| vLLM | `rocm_7_2_1_wheel_nightly` | `vllm_rocm721_wheel_nightly` | working on small models |
| vLLM | `amd_dev_stream` | `vllm_rocm_amd_dev` | historical working |
| vLLM | `regression_navi_base` | `vllm_rocm_navi_base` | historical working |
| TGI | `latest_rocm` | `tgi_rocm_current` | blocked on gfx1100 |
| TGI | `rocm_3_3_5` | `tgi_rocm_current` | blocked on gfx1100 |
| SGLang | `rocm_0_5_10rc0_mi30x` | `sglang_rocm_current` | blocked on gfx1100 |
| Ollama | `rocm` | `ollama_rocm_current` | working |
| Aphrodite | `latest` | `aphrodite_source_build` | blocked |
| Zinc | `git_head_20260330` | `zinc_source_build` | working |
