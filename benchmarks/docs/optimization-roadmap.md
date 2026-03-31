# Benchmark Optimization Roadmap

This document turns the current benchmark conclusions into a repeatable order of
attack.

The goal is to keep optimization work focused:

- make the harness clean first
- rebaseline the known-good paths
- test the smallest set of plausible alternatives
- stop digging when a path has clearly lost to the current winner

## Current winners

- Interactive path: llama.cpp Vulkan on the two RX 7900 XTX cards
- ROCm fallback: llama.cpp ROCm preview
- Serving path: vLLM current ROCm path, but only on models that fit the hardware well

## Recommended execution order

1. Phase 0: harden the benchmark harness
1. Phase 1: rebaseline the current winners and sanity checks
1. Phase 2: split vLLM into current-supported and regression branches
1. Phase 3: test whether vLLM has a viable dense-model path on RDNA3
1. Phase 4: keep only ROCm llama.cpp builds that beat the ROCm preview
1. Phase 5: continue Vulkan tuning, since that is still the strongest interactive path

## What to stop spending time on

- Qwen3.5-27B AWQ tuning on the current RDNA3 stack
- large-model splits that pull the RX 6900 XT into the 27B fast path
- MI300-oriented ROCm container images when validating gfx1100 hardware

## vLLM Tracks

- Track V-A: current supported ROCm path from the official vLLM docs
- Track V-B: historical `rocm/vllm-dev:navi_base` regression branch for comparison only
- Run Qwen2.5-14B BF16 before Qwen2.5-14B GPTQ
- Do not use Qwen3.5-27B AWQ as the first-line vLLM diagnostic

## How to use this roadmap

- Read the matrix in `../data/backend-benchmarks/optimization-matrix.yaml`
- Select a named profile from `../data/backend-benchmarks/benchmark-profiles.yaml`
- Run one backend at a time
- Record the result with the backend, model, GPU set, and startup/runtime notes
- Promote a path only when it clearly beats the current baseline
- Use the lifecycle scripts in `../bin/` so each run follows the same start,
  stop, reset, wait, and metrics collection pattern

## Named profiles

- `qwen35_compare_4b` for backend bring-up and compatibility checks
- `qwen35_27b_dual_xtx` for the main dual-XTX performance campaign

## Experimental add-on

- Zinc now has a working source-build Vulkan-native AMD lane on the server
- Keep it separate from the ROCm and vLLM lanes, and only promote it further if
  it continues to hold up on the two 7900 XTX cards
