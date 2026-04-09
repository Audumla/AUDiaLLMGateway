# Spec-803: Backend Validation and Promotion Gates

**Phase:** 5 — Backend Lifecycle Governance  
**Date:** 2026-04-02  
**Status:** Draft  
**Related specs:** spec-801, spec-802

---

## Executive Summary

This specification defines how backend versions transition from "untested" → "pending validation" → "production" status. It covers:

1. **Benchmark methodology** — standardized runs required for validity
2. **Measurement uncertainty** — how to handle measurement errors and small-sample results
3. **Promotion workflow** — gates and reviews before enabling a variant
4. **Deprecation criteria** — when to mark a variant as deprecated or blocked

**Key principle:** Uncertain measurements do NOT discard backends; they just delay promotion until better data exists.

---

## Problem Statement

The 2026-03-28 to 2026-03-31 benchmarking campaign produced 10+ backend configurations, but several issues prevent reliable decisions:

1. **Cold-start contamination** — The 2026-03-28 session acknowledged "per-run timing not individually captured." The vLLM results included both cold-start (JIT compilation overhead, slow) and warm-start runs without distinguishing them.

2. **Single-run samples** — Some results are from a single run (e.g. Lychee Strix Halo at "Illegal instruction" = instant failure, 0 samples). Cannot assess variance.

3. **No baseline stability check** — If two independent runs show 22.49 tok/s and 21.80 tok/s on "identical" hardware, is the variance expected or did something drift (GPU thermals, OS activity, cache state)? Unknown.

4. **Measurement methodology undocumented** — Batch size, context window, prompt, max_tokens are not standardized per backend. Different backends were tested with different parameters, making cross-backend comparison unreliable.

5. **Confidence not tracked** — The compatibility matrix records results without noting how many runs, whether cold-start was included, whether there was GPU contention. No way to know if a result is "solid" or "sketchy."

**Outcome:** A validation framework that:
- Defines minimal measurement rigor (N ≥ 3 warm runs per session)
- Tracks measurement uncertainty explicitly (`confidence: low | uncertain | validated`)
- Does NOT discard uncertain results, only gates their promotion
- Re-validates existing uncertain data to build confidence

---

## Terminology

| Term | Definition |
|---|---|
| **Session** | A coherent series of benchmark runs conducted on the same day/system state without reboots. |
| **Warm run** | A run after cold-start (JIT, GPU warmup). These are comparable across sessions. |
| **Cold run** | The first run after a fresh binary start. Includes JIT compilation overhead, GPU memory setup. NOT used for throughput comparison. |
| **Median** | The middle value of the warm runs. Reported as the single representative throughput for a session. |
| **Stability check** | Comparing median throughput across ≥2 independent sessions. Within 5% variance = stable. |
| **Smoke test** | Quick functional tests: `--list-devices` shows expected GPUs, `/v1/models` responds, no errors in logs. |
| **Soak test** | 10-minute continuous load (repeated inference requests). No errors or slowdown should occur. |
| **Confidence** | Metadata about result reliability: `low` (1 run or unknown method), `uncertain` (2+ runs, >10% variance), `validated` (3+ runs, <5% variance across sessions). |
| **Promotion** | Moving from `status: pending_validation` to `status: working` in compatibility matrix and enabling the variant in config. |

---

## Smoke Test Profiles

**Phase 5.1 validation uses only smoke tests (functional verification).** Benchmarking with standardized workloads is deferred to Phase 5.2.

### Quick Profile

Minimal validation; useful for CI checks and rapid iteration:

```bash
/app/runtime-root/{runtime_subdir}/active/bin/llama-server --list-devices
```

**Expected outcome:** Shows detected GPU devices (e.g., "Vulkan: Device 0 = RX 7900 XTX").  
**Failure condition:** No devices listed, segfault, or error message.  
**Time required:** <5 seconds.

### Standard Profile

Standard profile: Load a small model and verify API readiness:

```bash
/app/runtime-root/{runtime_subdir}/active/bin/llama-server \
  --port 9999 \
  --model /app/models/gguf/Qwen2.5-0.5B-Instruct-Q4_K_M.gguf \
  --ctx-size 2048 &

sleep 10  # wait for startup

curl http://localhost:9999/v1/models
# Expected: returns JSON with model list
# Example: {"object":"list","data":[{"id":"qwen2.5-0.5B","object":"model"}]}

curl -X POST http://localhost:9999/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-0.5B","messages":[{"role":"user","content":"test"}],"max_tokens":10}'
# Expected: returns JSON chat completion with non-empty response
# If: timeout, 500 error, or empty response → FAIL

pkill -f llama-server  # cleanup
```

**Expected outcome:** Model loads, API responds, single inference succeeds, no errors.  
**Failure condition:** Model load times out, API returns error, response is empty/malformed, or crashes.  
**Time required:** ~15 seconds.

---

## Validation Gates

---

## Promotion Workflow

### Status Taxonomy

Backends transition through these states. Note: `architecture_scoped` and `working_on_small_models` are valid resting states for testing; they do not require further promotion.

```
pending_validation      — New backend, not yet tested on this host
    ↓
working                 — Smoke tests (quick + standard) passed on target model
    ├→ architecture_scoped  — Works but only on specific hardware (e.g. gfx1151 Strix Halo)
    ├→ working_on_small_models  — Smoke test passes only on small models (<1B), not target model
    ↓
blocked                 — Known failure, awaiting upstream fix
    ↓
deprecated             — No longer supported (blocked >60 days or channel abandoned)
```

### Simple Promotion Procedure

**Prerequisite:** Variant is configured with `enabled: false`, `disabled_reason: pending_validation`

**Step 1: Run smoke tests**

```bash
# Quick test
/app/runtime-root/{runtime_subdir}/active/bin/llama-server --list-devices
# Expected: lists GPU devices

# Standard test
/app/runtime-root/{runtime_subdir}/active/bin/llama-server \
  --port 9999 \
  --model /app/models/gguf/Qwen2.5-0.5B-Q4_K_M.gguf \
  --ctx-size 2048 &
sleep 10

curl http://localhost:9999/v1/models
# Expected: returns model list

curl -X POST http://localhost:9999/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-0.5B","messages":[{"role":"user","content":"test"}],"max_tokens":10}'
# Expected: returns non-empty completion response

pkill -f llama-server
```

**Result:** If both tests pass → proceed to Step 2.  
If only quick test passes → set `disabled_reason: working_on_small_models` (useful for testing but not production-ready).  
If both fail → investigate and fix, or set `disabled_reason: boot_failure` / `compat_blocked` as appropriate.

**Step 2: Update compatibility matrix**

```yaml
# In benchmarks/data/backend-benchmarks/compatibility-matrix.yaml:
llama_cpp_vulkan:
  status: working           # changed from pending_validation
  confidence: low           # NEW FIELD: low | uncertain | validated (from benchmark runs, if any)
  notes:
    - "Smoke test passed: --list-devices OK, model loads, /v1/models responsive"
```

**Step 3: Enable variant in config**

```yaml
# In config/project/backend-runtime.base.yaml:
vulkan:
  backend: vulkan
  channel: ggml-org
  pinned_version: b8661
  enabled: true                 # changed from false
  disabled_reason: null         # cleared
```

**Step 4: Provision and verify**

```bash
python -m src.launcher.backend_provisioner provision vulkan

# Verify symlink
ls -la /app/runtime-root/vulkan/active/
# → should point to /app/runtime-root/vulkan/ggml-org/b8661/
```

**Step 5: Commit the promotion**

```bash
git add benchmarks/data/backend-benchmarks/compatibility-matrix.yaml \
        config/project/backend-runtime.base.yaml
git commit -m "backend-lifecycle: enable llama.cpp vulkan b8661

Smoke tests passed:
- --list-devices: OK
- Model load (Qwen2.5-0.5B): OK
- /v1/models: responsive
- Single inference: OK
"
```

---

## Confidence Levels (from Benchmarking, deferred to Phase 5.2)

The `confidence` field in compatibility-matrix.yaml tracks measurement rigor from prior benchmark campaigns. Confidence levels (low/uncertain/validated) are informational only; they do not gate promotion in Phase 5.1.

| Confidence | Meaning |
|---|---|
| `low` | Single run or unknown method; result is indicative but not rigorous |
| `uncertain` | Multiple runs with >10% variance; measured but not stable |
| `validated` | 3+ runs per session, <5% variance; ≥2 sessions with <5% cross-session variance; stable and reproducible |

**Phase 5.2 (future)** will formalize benchmark promotion gates and tie confidence levels to version advancement.

---

## Status Transitions and Blocking

### Valid Resting States

Backends can remain in the following states indefinitely:

| Status | Meaning | Action |
|---|---|---|
| `pending_validation` | New backend, not yet smoke-tested | Run smoke tests when resources available |
| `working` | Smoke tests passed on target model | Ready for use; monitor for regressions |
| `architecture_scoped` | Works but only on specific hardware | Useful for testing; document scope restrictions |
| `working_on_small_models` | Smoke test passes only on small models (<1B) | Useful for development; not production-ready |

### Blocking Criteria (Transitional)

A backend transitions to `status: blocked` if it:

1. **Fails smoke test where it previously passed**
   - Example: Vulkan backend worked on 2026-04-01, fails on 2026-04-05 after system update
   - Action: Investigate root cause; pin to previous working version or disable

2. **Dependency becomes unavailable**
   - Example: Required ROCm 7.2.1 docker image is no longer published
   - Action: Switch to alternative source channel or deprecate

3. **New upstream version introduces regression**
   - Example: vLLM v0.18.0 introduces HIP OOM on gfx1100 (previously working in v0.17.1)
   - Action: Pin to previous working version; file upstream issue

### Deprecation Criteria

A backend transitions to `status: deprecated` if:

1. **Blocked for >60 days with no upstream fix**
   - Example: TGI blocked since 2026-03-30 with "Unsupported model type qwen3_5"
   - If no fix by 2026-06-01 → mark deprecated and remove from configuration

2. **Source channel abandons all GPU target coverage for this host**
   - Example: Lychee-Tech officially discontinues support for gfx1100 (only gfx1151 from now on)
   - Action: Mark as `architecture_scoped: gfx1151 only` (not deprecated, just out-of-scope for this host)

---

## Benchmark Campaign Tracking

Link benchmark runs to config changes:

```bash
# Create campaign entry
cat > benchmarks/data/backend-benchmarks/campaign-20260402.md << 'EOF'
# Campaign: 2026-04-02 Validation Gates

**Goal:** Promote llama.cpp Vulkan b8661 to production, validate new ROCm preview

**Sessions:**
- Session 1 (2026-04-01): llama.cpp Vulkan b8661 [26.32 tok/s, 3 runs, 0.7% variance]
- Session 2 (2026-04-02): llama.cpp Vulkan b8661 recheck [26.33 tok/s, 3 runs, 0.4% variance]
- Session 3 (2026-04-02): ROCm preview gfx1100 [22.49 tok/s, 3 runs, 2.1% variance]

**Promotion decisions:**
- llama.cpp Vulkan b8661 → PROMOTED to working (status=working)
- ROCm preview → PROMOTED to working (status=working)
- vLLM 0.17.1 ROCm → DEFERRED (flagged for re-validation, low confidence from prior run)

**Config changes:**
- Commit: abc123 (backend-lifecycle: promote vulkan b8661 and rocm preview)
- Time: 2026-04-02 15:30 UTC
EOF
```

---

## Related Specifications

- **spec-801** — Backend Version Registry: Defines pinned versions, source channels, integrity checksums
- **spec-802** — Backend Build and Deployment: Provisioning mechanisms, rollback support
- **compatibility-matrix.yaml** — Produced by this spec; filled in via promotion workflow

