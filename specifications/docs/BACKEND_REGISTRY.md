# Backend Registry

This document is the operational registry for `llama.cpp` backend lanes.

Use it to answer:

- which backend lanes exist
- which ones are primary vs experimental
- where the source comes from
- how a lane is pinned
- whether it is enabled in tracked samples or only in private deployment overlays
- what to update when a new version or new backend lane is introduced

---

## Model

Backend management in this repo follows a four-layer model:

1. `config/project/backend-runtime.base.yaml`
   Holds shared source/build profiles and sample backend variants.
2. `config/local/backend-runtime.override.yaml`
   Holds tracked sample rollout decisions and commented examples.
3. `config/local/backend-runtime.private.yaml`
   Holds real machine-specific pins and enablement choices. This file is git-ignored.
4. `config/local/models.override.yaml` or `config/local/models.private.yaml`
   Binds model deployments to backend macros such as `llama-server-vulkan` or `llama-server-vulkan-turboquant`.

That separation keeps the public repo generic while still allowing one private host to be reproduced exactly.

---

## Lane Types

### Primary lanes

These are the normal deployment targets:

- `cpu`
- `cuda`
- `rocm`
- `vulkan`

They should generally come from `ggml-org/llama.cpp` GitHub releases unless there is a proven reason to use a different source.

### Specialized lanes

These are architecture-specific or comparison lanes:

- `rocm-gfx1100-prebuilt`
- `rocm-gfx1030-prebuilt`
- custom ROCm git builds

They should stay disabled unless they are actively being benchmarked or promoted.

### Experimental fork lanes

These are non-default upstreams or forks such as:

- `vulkan-turboquant`

They must be pinned to an explicit tag or ref and should stay disabled in tracked config.

---

## Registry Fields

Each backend lane should have these management fields recorded here before it is treated as real:

| Field | Meaning |
| ----- | ------- |
| `lane` | Stable runtime variant name |
| `macro` | Macro consumed by model deployments |
| `backend` | `cpu`, `cuda`, `rocm`, `vulkan`, etc. |
| `source_type` | `github_release`, `direct_url`, or `git` |
| `source` | Upstream repo or artifact origin |
| `pin` | Concrete release tag, build number, or git ref |
| `runtime_subdir` | Runtime cache path under `BACKEND_RUNTIME_ROOT` |
| `state` | `primary`, `candidate`, `experimental`, `deprecated`, or `disabled` |
| `tracked_default` | Whether checked-in sample config enables it |
| `private_rollout` | Whether private deployment overlay enables it |
| `purpose` | Why this lane exists |
| `validation` | Which smoke tests or benchmarks are required |

---

## Current Registry

| lane | macro | backend | source_type | source | pin model | state | tracked default | private rollout | purpose | validation |
| ---- | ----- | ------- | ----------- | ------ | --------- | ----- | --------------- | --------------- | ------- | ---------- |
| `cpu` | `llama-server-cpu` | `cpu` | `github_release` | `ggml-org/llama.cpp` | pinned in private overlay | primary | enabled | enabled | CPU fallback and lowest-risk compatibility lane | Included in the config-driven validation matrix; Docker fallback is the most reliable portable smoke path |
| `cuda` | `llama-server-cuda` | `cuda` | `github_release` | `ggml-org/llama.cpp` | pinned in private overlay | primary | enabled | enabled | Standard NVIDIA lane | Config generation/tests plus host-specific smoke when a CUDA private overlay is present |
| `rocm` | `llama-server-rocm` | `rocm` | `github_release` | `ggml-org/llama.cpp` | pinned in private overlay | primary | enabled | enabled | Standard AMD ROCm lane | Config generation/tests plus host-specific smoke when a ROCm private overlay is present |
| `vulkan` | `llama-server-vulkan` | `vulkan` | `github_release` | `ggml-org/llama.cpp` | pinned in private overlay | primary | enabled | enabled | Standard Vulkan lane | Native smoke with `local/qwen2b_validation_vulkan`; Docker integration uses the same fast Qwen 2B Q4 model by default, with the 4B Q8 profile available on demand |
| `rocm-gfx1100-prebuilt` | `llama-server-rocm-gfx1100` | `rocm` | `github_release` | `ggml-org/llama.cpp` | inherits tracked default unless overridden | candidate | enabled | disabled | Comparison lane for gfx1100-specific rollout | Enable intentionally and benchmark against the primary ROCm lane before promotion |
| `rocm-gfx1030-prebuilt` | `llama-server-rocm-gfx1030` | `rocm` | `github_release` | `ggml-org/llama.cpp` | inherits tracked default unless overridden | candidate | enabled | disabled | Comparison lane for gfx1030-specific rollout | Enable intentionally and benchmark against the primary ROCm lane before promotion |
| `rocm-gfx1100-official-custom` | `llama-server-rocm-gfx1100-official` | `rocm` | `git` | `ROCm/llama.cpp` | explicit git ref only | disabled | disabled | disabled | Custom ROCm build fallback | No default smoke; treat as manual benchmark-only until a stable validation lane is added |
| `rocm-gfx1030-official-custom` | `llama-server-rocm-gfx1030-official` | `rocm` | `git` | `ROCm/llama.cpp` | explicit git ref only | disabled | disabled | disabled | Custom ROCm build fallback | No default smoke; treat as manual benchmark-only until a stable validation lane is added |
| `vulkan-turboquant` | `llama-server-vulkan-turboquant` | `vulkan` | `git` | `TheTom/llama-cpp-turboquant` | explicit tag only | experimental | disabled | disabled | Experimental Vulkan fork for benchmarking | Included as an experimental matrix target; on Windows bootstrap a local SDK cache with `python scripts/bootstrap_vulkan_sdk.py --source-dir <sdk>` before running the TurboQuant build |

Notes:

- The private deployment overlay currently pins the four primary lanes to concrete release builds.
- The tracked sample config remains broader than the private rollout on purpose, so the repo can still demonstrate supported lane types without forcing them on a real host.
- The sample validation model labels live in `config/local/models.override.yaml` so local validation can exercise the same quick 2B Q4 path by default in both Docker and native smoke runs, while keeping the heavier 4B Q8 option switchable.

---

## Update Workflow

When updating an existing backend lane:

1. Find the latest upstream release or intended git ref.
2. Decide whether the update is:
   - a tracked sample change
   - a private deployment pin change
   - both
3. Update the right file:
   - tracked sample lane shape in `config/project/backend-runtime.base.yaml`
   - tracked sample rollout in `config/local/backend-runtime.override.yaml`
   - real deployment pin in `config/local/backend-runtime.private.yaml`
4. Regenerate configs.
5. Run tests:
   - `python -m pytest tests -q`
   - Docker compose config validation if compose overlays changed
6. Run the config-driven validation matrix for the target platform and collect benchmarks:
   - `python scripts/run_backend_validation_matrix.py`
   - add `--include-experimental` when validating an opt-in lane such as TurboQuant
7. If the lane is used by real models, smoke-test at least one model bound to that macro.
8. Update this registry entry:
   - `pin`
   - `state`
   - `validation`
   - any change in purpose or rollout

---

## Add-New-Lane Checklist

When adding a new backend lane:

1. Add or reuse a source/build profile in `config/project/backend-runtime.base.yaml`.
2. Add the variant with:
   - stable `name`
   - stable `macro`
   - explicit `runtime_subdir`
   - explicit `source_type`
3. Keep the lane disabled by default unless it is clearly safe as a primary lane.
4. If it is experimental or fork-based, pin it to an explicit tag or commit-ref.
5. Add or adjust a model deployment to use the macro only when you are ready to test it.
6. Add a validation target in `config/project/backend-validation.base.yaml` if the lane should participate in matrix testing.
7. Record the lane in this registry before calling it supported.
8. Add or extend tests if the new lane introduces new config behavior.

---

## Promotion Rules

Use these states consistently:

- `primary`
  The normal supported lane for real deployments.
- `candidate`
  A lane worth testing or comparing, but not yet standard.
- `experimental`
  A fork or unproven lane; opt-in only.
- `disabled`
  Kept for reference or fallback, but intentionally not active.
- `deprecated`
  Still documented for migration/history, should be removed when safe.

A lane should only be promoted to `primary` when:

- it has a concrete pin
- it passes local config/test validation
- at least one real model deployment works against it
- it does not create unacceptable startup or maintenance cost

---

## Ownership Rules

To keep backend management clean:

- Models should never embed backend source/build details directly.
- Backend lanes should always be referenced through stable macros.
- Real host paths, real rollout pins, and sensitive deployment details belong only in private overlays.
- Experimental lanes should not replace primary lanes without an explicit promotion step.
- If a lane is not recorded here, it should not be treated as a maintained deployment target.
