# Backend Matrix Integration Review

**Date:** 2026-04-02  
**Objective:** Review benchmarked backends and identify which should be incorporated into the available matrix (llama-swap runtime configurations).

---

## Executive Summary

| Finding | Action | Priority |
| --- | --- | --- |
| llama.cpp ROCm preview (gfx1100) at 22.49 tok/s is NOT in llama-swap | ADD to matrix | **HIGH** |
| llama.cpp Vulkan (26.28 tok/s) is current best performer | KEEP (already integrated) | — |
| Ollama ROCm (18.12 tok/s) has operational value | CONSIDER adding | MEDIUM |
| vLLM ROCm variants are broken/slow for Qwen3.5-27B | DO NOT add | — |
| ROCm 7.2.1 prebuilt (9.98 tok/s) underperforms | REVIEW/DEPRECATE old variants | LOW |
| Lychee Strix Halo (gfx1151-only) | TRACK for future | — |

---

## Benchmarked Backends Status

### Tier 1: Currently Integrated in llama-swap

#### llama.cpp Vulkan — **26.28 tok/s** ✅ BEST
- **Models served:** qwen3.5-27b-(96k-Q6), qwen3.5-122b, qwen3.5-4b-vision, ministral3b-vision
- **Device:** Vulkan1 + Vulkan2 (both XTX, 48 GB)
- **Status:** Fully operational, persistent model group
- **Config macros:** `llama-server-vulkan`
- **Verdict:** Keep as-is. This is the clear winner for single-sequence throughput.

#### llama.cpp ROCm (ggml-latest) — **~21 tok/s** ⚠️ BASELINE ONLY
- **Models served:** qwen3.5-27b-(96k-Q6)-rocm-latest (uses old ggml-latest binary)
- **Device:** ROCm1 + ROCm2 (both XTX, 48 GB)
- **Status:** Working but outdated binary
- **Issue:** Uses `llama-server-rocm-ggml-latest` which is v8583, benchmarks showed standard prebuilt only reaches 9.98 tok/s. The "~21 tok/s" entry in the performance doc refers to git-main or b8429 variants, not the ggml-latest binary.
- **Config macros:** `llama-server-rocm-ggml-latest`
- **Verdict:** The current naming is misleading. This is actually serving with an inferior build. **Should be updated or replaced.**

#### Tiny Test Model — ROCm Variant ✅ WORKING
- **Models served:** tiny-qwen25-test
- **Device:** ROCm0
- **Status:** Functional smoke test
- **Verdict:** Keep for CI/smoke testing.

---

### Tier 2: Benchmarked but NOT Currently Integrated

#### llama.cpp ROCm preview (gfx1100 custom build) — **22.49 tok/s** 🔴 SHOULD ADD
- **Benchmark date:** 2026-03-30 (4 days old, verified warm result)
- **Build source:** `rocm_gfx1100_preview` from backend-runtime.catalog.json
- **Device:** ROCm0 + ROCm1 (both XTX, 48 GB)
- **Model tested:** Qwen3.5-27B-Q6_K
- **Performance vs Vulkan:** 85% of Vulkan throughput (16% slower, but significant improvement over standard ROCm)
- **Performance vs ggml-latest:** **127% better** (2.27x faster than prebuilt)
- **Performance vs git-main/b8429:** ~7% faster
- **Infrastructure:** Already built and in runtime paths: `/app/runtime-root/rocm/gfx1100/` (from backend-runtime.catalog.json)
- **Enabled:** `enabled: false` in backend-runtime.catalog.json but built and verified

**Recommendation:** ADD to llama-swap.override.yaml
- This should be the primary ROCm option going forward
- Represents best-known ROCm performance on gfx1100 (RDNA3)
- Can serve as fallback when Vulkan is unavailable
- Appropriate naming: `qwen3.5-27b-(96k-Q6)-rocm-preview` or `qwen3.5-27b-(96k-Q6)-rocm-gfx1100`

---

#### llama.cpp Lemonade b1224 — **21.85 tok/s** 🟡 ALTERNATIVE ROCm TRACK
- **Benchmark date:** 2026-03-29
- **Build source:** `lemonade_nightly` from backend-catalog.yaml (lemonade-sdk/llamacpp-rocm)
- **Device:** ROCm0 + ROCm1
- **Model tested:** Qwen3.5-27B-Q6_K
- **Architecture target:** RDNA3/RDNA4 explicitly
- **Status:** Maintained nightly channel with explicit RDNA3 tuning
- **Performance:** 1% slower than preview, but from separate maintained upstream
- **Infrastructure:** Binary at `/app/runtime-root/rocm/lemonade-b1217/` (or newer)

**Recommendation:** TRACK as alternative but do not prioritize
- Good option if preview build becomes unmaintained
- Represents healthy ecosystem diversity
- Could be added as `qwen3.5-27b-(96k-Q6)-rocm-lemonade` but lower priority than preview

---

#### Ollama ROCm — **18.12 tok/s** 🟢 OPERATIONAL ALTERNATIVE
- **Benchmark date:** 2026-03-30
- **Container:** Not integrated, runs separately
- **Device:** Works on ROCm (exact GPU split unclear from benchmark)
- **Model tested:** Qwen3.5-27B Q6_K
- **Performance:** 69% of Vulkan (30% slower), but simpler UX
- **Status:** Fully working, official ROCm Docker image
- **Use case:** Better UX/operational experience than raw llama.cpp

**Recommendation:** CONSIDER as secondary option for operational UX
- Add as separate service/container if operational experience becomes priority
- Not suitable for performance-critical tasks (18.12 tok/s vs 26.28 tok/s)
- Would add to deployment complexity without performance benefit
- Could document as "alternative lightweight option" in specifications

---

### Tier 3: Benchmarked but NOT Suitable

#### vLLM 0.17.1 ROCm (Qwen3.5-27B) — **3.41–10.8 tok/s** ❌ DO NOT ADD
- **Root cause:** Triton AWQ dequantization is unoptimized for RDNA3 (gfx1100)
- **Performance:** 13% of Vulkan (87% slower) — unacceptable
- **Status:** Working but too slow for deployment
- **Notes from 2026-03-31 benchmark:** "keep this lane separate from v0.18.x hybrid KV-cache regression"
- **AMD focus:** AITER targets gfx9 (CDNA), not gfx11 (RDNA3)

**Verdict:** This is a known dead-end for RDNA3. Skip entirely.

---

#### vLLM ROCm 7.2.1 nightly — **PARTIAL** ❌ DO NOT ADD FOR LARGE MODELS
- **Status:** Working for Qwen3-0.6B (75.05 tok/s), broken for Qwen3.5-27B
- **Failure mode:** HIP OOM during multimodal profiling, KV-cache page-size unification error on text-only
- **Model state:** Qwen3.5-4B, Qwen3.5-27B text-only both fail with same error
- **Assessment:** Upstream engine issue unfixed; not suitable for deployment

**Verdict:** Skip. Only viable for small model smoke tests, not for Qwen3.5-27B.

---

#### TGI ROCm — **BLOCKED** ❌
- **Failure:** Qwen3.5-4B reports "Unsupported model type qwen3_5"
- **Qwen2.5-0.5B:** Fails with "HIP invalid device function"
- **Assessment:** Not ready for RDNA3 on this stack

---

#### SGLang ROCm — **BLOCKED** ❌
- **Status:** Exits before readiness
- **Assessment:** MI300-targeted, not RDNA3-optimized

---

#### Aphrodite — **BLOCKED** ❌
- **Failure:** Requires libcuda.so.1 (NVIDIA library)
- **Status:** No confirmed AMD prebuilt channel

---

#### Zinc (Vulkan-native) — **CRASHES** ❌
- **Status:** Source-built, reaches "READY WITH WARNINGS"
- **Failure:** Vulkan crash in libvulkan_radeon.so on Qwen3.5-27B Q6_K
- **Assessment:** Promising architecture but not production-ready

---

#### Lychee Strix Halo gfx1151 — **ARCHITECTURE SCOPED** 🟡
- **Target arch:** gfx1151 (Intel Strix Halo)
- **Current host:** gfx1100 (RDNA3 7900 XTX)
- **Status on gfx1100:** Fails with "Illegal instruction"
- **Recommendation:** TRACK for future when gfx1151 hardware becomes available
- **Keep separate:** From gfx1100 optimization lane

---

## Summary Table: Performance Ranked

| Backend | tok/s | Host | Date | Integrated? | Notes |
| --- | --- | --- | --- | --- | --- |
| **llama.cpp Vulkan** | 26.28 | Vulkan1+2 | 2026-03-31 | ✅ YES | Best performer, persistent |
| **llama.cpp ROCm preview** | 22.49 | ROCm0+1 | 2026-03-30 | ❌ NO | **SHOULD ADD** — best ROCm, 85% of Vulkan |
| llama.cpp Lemonade b1224 | 21.85 | ROCm0+1 | 2026-03-29 | ❌ NO | Alternative ROCm track (maintained) |
| vLLM 0.17.1 ROCm (AWQ) | 10.80 | ROCm0+1 | 2026-03-28 | ❌ NO | Too slow, Triton unoptimized for RDNA3 |
| Ollama ROCm | 18.12 | ROCm | 2026-03-30 | ❌ NO | Operational UX but 30% slower |
| llama.cpp ROCm ggml-latest (current) | ~9.98 | ROCm0+1 | 2026-03-28 | ✅ YES | **OUTDATED** — prebuilt slower than preview |
| vLLM ROCm nightly (0.6B only) | 75.05 | GPU | 2026-03-30 | ❌ NO | Broken for Qwen3.5-27B |
| Zinc (Vulkan) | crash | Vulkan | — | ❌ NO | Promising but unstable |

---

## Recommended Actions

### Action 1: ADD llama.cpp ROCm preview to llama-swap (HIGH PRIORITY)

**File:** `config/local/llama-swap.override.yaml`

Add macro:
```yaml
llama-server-rocm-gfx1100-preview: "env LD_LIBRARY_PATH=/app/runtime-root/rocm/gfx1100/lib:/opt/rocm/lib ROCBLAS_TENSILE_LIBPATH=/opt/rocm/lib/rocblas/library /app/runtime-root/rocm/gfx1100/bin/llama-server-rocm"
```

**File:** `config/local/models.override.yaml`

Add model definition:
```yaml
qwen3.5-27b-(96k-Q6)-rocm-preview:
  cmd: ${llama-server-rocm-gfx1100-preview} ${server-args} ${model-path}/qwen3.5-27B/Qwen3.5-27B-Q6_K.gguf ${context-96k-args} --device ROCm0,ROCm1 --split-mode layer --tensor-split 1,1 --gpu-layers 99 --parallel 1 --metrics ${jinja-args} ${nothink-args} ${coder_args}
```

**Regenerate config:**
```bash
python -m src.launcher.process_manager generate-configs
```

**Justification:**
- 22.49 tok/s is only 16% behind Vulkan's 26.28 tok/s
- Represents 127% improvement over current ggml-latest (9.98 → 22.49)
- Ensures ROCm fallback is competitive and well-optimized
- Binary already exists in runtime paths

**Expected outcome:** Users have option to select ROCm preview for better ROCm performance or Vulkan for best performance.

---

### Action 2: Review/Update current ROCm ggml-latest configuration (MEDIUM PRIORITY)

**Issue:** Current `qwen3.5-27b-(96k-Q6)-rocm-latest` uses `llama-server-rocm-ggml-latest`, which appears to be v8583. Performance doc shows this gets ~9.98 tok/s prebuilt but only 21 tok/s with git-main/b8429 builds.

**Options:**
1. **Keep as baseline** for regression testing
2. **Rename to** `qwen3.5-27b-(96k-Q6)-rocm-baseline` to clarify it's the prebuilt fallback
3. **Replace with** lemonade b1224 (21.85 tok/s) or preview (22.49 tok/s)
4. **Add comment** explaining the performance difference vs preview

**Recommendation:** Option 2 or 3 — current naming is misleading about which binary is actually running.

---

### Action 3: Consider Ollama for operational track (OPTIONAL, LOW PRIORITY)

**If** operational ease/UX becomes a priority over raw performance:
- Document Ollama ROCm as "lightweight alternative" in specifications
- Do NOT integrate into primary llama-swap (adds complexity for 30% perf loss)
- Could be parallel service/container option documented separately

**Decision:** Defer unless UX requirements change.

---

### Action 4: Track emerging backends (FUTURE)

Keep monitoring:
- **Zinc** (Vulkan-native) — may become viable after stabilization
- **Lychee Strix Halo** — valuable once gfx1151 hardware available
- **vLLM upstream** — if Triton AWQ optimization comes to RDNA3 (currently blocked)

---

## Backend Catalog Status

Current entries in `benchmarks/data/backend-benchmarks/backend-catalog.yaml` to review:

| Entry | Status | Action |
| --- | --- | --- |
| `llama_cpp.ggml_org_release` | ✅ Primary | Keep |
| `llama_cpp.rocm_official_preview` | ✅ Proven 22.49 tok/s | **ADD TO LLAMA-SWAP** |
| `llama_cpp.lemonade_nightly` | ✅ Alternative | Keep tracked |
| `llama_cpp.rocm_7_2_1_runtime_release` | ✅ Documented | Keep as reference |
| `llama_cpp.lychee_strix_halo_release` | ⚠️ gfx1151 only | Keep scoped |
| `vllm.rocm_current` | ⚠️ Small models only | Review deprecation |
| `vllm.rocm_0_17_1_rollback` | ⚠️ Slow (3.41 tok/s) | Consider deprecating |
| `vllm.rocm_7_2_1_wheel_nightly` | ⚠️ Broken for large models | Deprecate |
| `tgi.rocm_docker` | ❌ Blocked | Deprecate |
| `sglang.rocm_docker` | ❌ Blocked | Deprecate |
| `ollama.rocm_docker` | ✅ Working | Keep as alternative reference |
| `aphrodite.source_build` | ❌ Blocked | Deprecate |
| `zinc.source_build` | ⚠️ Crashes | Keep tracked |

---

## Conclusion

**Immediate action:** Integrate llama.cpp ROCm preview (22.49 tok/s) into llama-swap matrix. This backend:
- Is already built and verified
- Provides strong ROCm fallback (85% of Vulkan performance)
- Represents significant improvement over current baseline
- Requires minimal effort (config additions only, binary exists)

**Secondary:** Clean up misleading/outdated backend references in configs and documentation.

**Monitoring:** vLLM upstream and Zinc for future viability as alternative or specialized paths.

