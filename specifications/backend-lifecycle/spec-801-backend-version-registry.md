# Spec-801: Backend Version Registry and Schema

**Phase:** 5 — Backend Lifecycle Governance  
**Date:** 2026-04-02  
**Status:** Draft  
**Related specs:** spec-802, spec-803

---

## Executive Summary

This specification defines the schema and governance model for backend version pinning, source channel management, and version lifecycle tracking. It replaces the ambiguous `version: latest` pattern with explicit, auditable version references and provides a single source of truth for all pinned backend versions.

**Key principles:**
- No `latest` — all versions are explicitly pinned to a specific build or commit
- Source channels are first-class — `ggml-org:b8661` ≠ `lemonade:b1229`
- Asset token matching — replaces fragile regex patterns with explicit substring matching
- Integrity verification — every downloaded artifact has a SHA256 checksum
- Drift policy — each variant declares how it responds when upstream moves forward

---

## Problem Statement

The current system has several version-governance gaps:

1. **"latest" is ambiguous** — ggml-org releases multiple builds per day (b8661+ as of April 2026). A variant configured with `version: latest` will silently pull a different binary on every environment setup, making the system non-reproducible and unauditable.

2. **No per-variant version pinning** — the schema has a single `${LLAMA_VERSION}` env-var that controls all variants simultaneously. There is no way to pin vulkan to b8583 while keeping rocm at b8450.

3. **Source channels are informal** — `lemonade-sdk/llamacpp-rocm` has its own independent build counter (b1229 ≠ ggml-org b1229), daily releases, and RDNA3-specific GPU targeting. You cannot point a variant at a lemonade build in the schema without writing raw `repo_owner`/`repo_name` overrides.

4. **No integrity verification** — downloaded release assets are not checksummed. A Man-in-the-Middle attack or cache corruption could silently introduce a different binary.

5. **Version comparison is impossible** — there is no machine-readable way to know that b8661 is newer than b8660, or that `lemonade:b1224` and `ggml-org:b1224` are different builds.

---

## Terminology

| Term | Definition |
|---|---|
| **Channel** | A named source of backend binaries or source code. Examples: `ggml-org`, `lemonade-sdk`, `rocm-official`, `lychee-tech`. Each channel has its own versioning counter namespace. |
| **Pinned version** | An explicitly specified version identifier. Format depends on channel: `bXXXX` for prebuilt (ggml-org, lemonade-sdk), **40-char commit SHA** for git-based (rocm-official). Never "latest". |
| **Pinned metadata** | For git-based channels only: human-readable branch/date reference (e.g., `master@2026-03-30`) alongside the commit SHA. Used for logging, not for checkout. |
| **Floor version** | The minimum acceptable version for a variant. Deployments with a version older than the floor will be blocked at startup. |
| **Drift** | The difference between the pinned version (declared in config) and the deployed version (running in the system). |
| **Asset token** | A substring that must appear in a release asset filename for it to match a variant's download pattern. Example: `[ubuntu, rocm-7.2, x64]` matches `llama-b8661-bin-ubuntu-rocm-7.2-x64.tar.gz`. |
| **Manifest** | A JSON file created at deployment time (`manifest.json`) that records the channel, pinned version, sha256, and timestamp of a deployed binary. |

---

## Backend Version Registry

The **canonical version registry** is stored in a new file:

```
benchmarks/data/backend-benchmarks/backend-version-registry.yaml
```

This file is the single source of truth for all pinned versions, floor versions, and source channel information.

### Structure

```yaml
version: 1
date_updated: 2026-04-02
source_channels:
  ggml-org:
    org: ggml-org
    repo: llama.cpp
    counter_namespace: ggml-org
    versioning_scheme: monotonic-build-number  # bXXXX format
    release_cadence: "multiple per day"
    prebuilt: true
    url: https://github.com/ggml-org/llama.cpp
    asset_base_url: "https://github.com/ggml-org/llama.cpp/releases/download/{version}/{asset}"
    notes:
      - "Primary distribution channel for non-ROCm backends"
      - "Build numbers are not semantic versions; multiple releases per day is normal"
      - "ROCm asset includes version token that changes with ROCm bumps: rocm-7.2, rocm-7.3, etc."
  
  lemonade-sdk:
    org: lemonade-sdk
    repo: llamacpp-rocm
    counter_namespace: lemonade
    versioning_scheme: monotonic-build-number  # independent bXXXX counter, separate from ggml-org
    release_cadence: "daily"
    prebuilt: true
    url: https://github.com/lemonade-sdk/llamacpp-rocm
    asset_base_url: "https://github.com/lemonade-sdk/llamacpp-rocm/releases/download/{version}/{asset}"
    notes:
      - "RDNA3/RDNA4 optimized, bundled ROCm 7 runtime"
      - "Build counter bXXXX is independent of ggml-org; always qualify as lemonade:bXXXX"
      - "Builds all AMD GPU targets (gfx1151, gfx1150, gfx120X, gfx110X, gfx103X) into single asset"
      - "gfx1100 (RDNA3 7900 XTX) is covered by gfx110X target group"
  
  rocm-official:
    org: ROCm
    repo: llama.cpp
    counter_namespace: rocm-official
    versioning_scheme: git-ref-based  # branches/tags, e.g. master@2026-03-30
    release_cadence: "on commit"
    prebuilt: false
    source_build: true
    url: https://github.com/ROCm/llama.cpp
    notes:
      - "AMD's official ROCm-optimized fork"
      - "Source-build only; no prebuilt assets"
      - "Used for hermetic source builds in pinned ROCm container images"
  
  lychee-tech:
    org: Lychee-Technology
    repo: llama-cpp-for-strix-halo
    counter_namespace: lychee
    versioning_scheme: monotonic-build-number  # bXXXX
    release_cadence: "irregular"
    prebuilt: true
    architecture_scoped: true  # gfx1151 (Strix Halo) ONLY
    url: https://github.com/Lychee-Technology/llama-cpp-for-strix-halo
    notes:
      - "Strix Halo (gfx1151) specific"
      - "NOT FOR gfx1100 (RX 7900 XTX) — will fail with Illegal Instruction"
      - "Track separately from RDNA3 desktop lanes"
  
  rocm-7-2-1-runtime:
    org: ROCm
    repo: ROCm
    counter_namespace: rocm-release
    versioning_scheme: semantic  # rocm-7.2.1
    release_cadence: "quarterly"
    prebuilt: true
    url: https://github.com/ROCm/ROCm/releases/tag/rocm-7.2.1
    notes:
      - "ROCm runtime release marker; does not ship llama.cpp binaries directly"
      - "Used as container base image reference: rocm/dev-ubuntu-24.04:7.2.1"

backends:
  llama_cpp_vulkan:
    channel: ggml-org
    pinned_version: b8583
    floor_version: b8153
    asset_tokens: [ubuntu, vulkan, x64]
    integrity_sha256: ""  # TBD: compute from GitHub release assets
    last_benchmarked: 2026-03-31
    benchmark_result_tok_s: 26.28
    benchmark_confidence: validated  # 2 independent sessions within 5%
    notes:
      - "Best performer on dual RX 7900 XTX (gfx1100)"
      - "Last warm-run verification: 2026-03-31"
  
  llama_cpp_rocm_prebuilt:
    channel: ggml-org
    pinned_version: b8583
    floor_version: b8153
    asset_tokens: [ubuntu, rocm-7.2, x64]
    integrity_sha256: ""  # TBD
    last_benchmarked: 2026-03-28
    benchmark_result_tok_s: 21
    benchmark_confidence: low  # single-run, cold-start contamination possible
    notes:
      - "Standard prebuilt from ggml-org"
      - "rocm-7.2 token will need update if ROCm version bumps"
  
  llama_cpp_rocm_lemonade:
    channel: lemonade-sdk
    pinned_version: "b1224"  # NOTE: lemonade build counter, independent from ggml-org
    floor_version: "b1200"
    asset_tokens: [ubuntu, rocm]  # lemonade assets don't encode gfx target in filename; all targets included
    integrity_sha256: ""  # TBD
    last_benchmarked: 2026-03-29
    benchmark_result_tok_s: 21.85
    benchmark_confidence: validated  # 2 sessions within 2% variance
    notes:
      - "Daily updated nightly build with bundled ROCm 7 runtime"
      - "RDNA3 optimized across all GPU targets"
      - "Independent counter: lemonade:b1224 ≠ ggml-org:b1224"
  
  llama_cpp_rocm_preview_gfx1100:
    channel: rocm-official
    pinned_version: "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b"  # full 40-char commit SHA (canonical pin)
    pinned_metadata:
      branch: master
      approx_date: "2026-03-30"         # human reference only, not used for checkout
      commit_summary: "Optimize gfx1100 GEMM kernels"
    floor_version: null  # source builds don't have a meaningful floor
    source_build: true
    build_image: "rocm/dev-ubuntu-24.04:7.2.1"
    cmake_flags: "-DLLAMA_BUILD_SERVER=ON -DGGML_HIPBLAS=ON -DAMDGPU_TARGETS=gfx1100 -DCMAKE_BUILD_TYPE=Release"
    last_benchmarked: 2026-03-30
    benchmark_result_tok_s: 22.49
    benchmark_confidence: validated  # 2 sessions within 3% variance
    notes:
      - "Source-build from AMD's official ROCm fork"
      - "Custom cmake configuration for gfx1100 target"
      - "Best-known ROCm performance for RDNA3"
      - "Pin is full commit SHA; approx_date is for human reference only"
  
  llama_cpp_cpu:
    channel: ggml-org
    pinned_version: b8583
    floor_version: b8000
    asset_tokens: [ubuntu, x64]
    integrity_sha256: ""  # TBD
    last_benchmarked: null
    notes:
      - "CPU-only fallback"
      - "No GPU required; runs on any system"
  
  llama_cpp_cuda:
    channel: ggml-org
    pinned_version: b8583
    floor_version: b8153
    asset_tokens: [ubuntu, cuda, x64]  # does not pick up CUDA sidecar here; spec-802 handles sidecar logic
    integrity_sha256: ""  # TBD
    last_benchmarked: null
    notes:
      - "NVIDIA CUDA support"
      - "Asset pattern matches main cuda asset; spec-802 provisioner also downloads cudart sidecar"
  
  zinc_vulkan:
    channel: null  # source-build only
    source_build: true
    source_url: "https://github.com/zolotukhin/zinc"
    build_image: "vulkan-sdk:1.4.341.1"
    last_benchmarked: null
    status: crashes
    notes:
      - "Vulkan-native AMD inference engine"
      - "Crashes during model load; not production-ready"
      - "Monitor for stability improvements"
```

---

## Extended Backend-Runtime Schema

The `config/project/backend-runtime.base.yaml` schema is extended with these new fields per variant:

```yaml
variants:
  vulkan:
    backend: vulkan
    macro: llama-server-vulkan
    runtime_subdir: vulkan
    
    # NEW FIELDS (Phase 5):
    channel: ggml-org                    # Identifies source channel
    pinned_version: b8583                # Explicit version pin (never "latest")
    floor_version: b8153                 # Minimum acceptable version
    rollback_version: b8450              # Previous version to fall back to (managed by provisioner)
    asset_tokens:                        # Token list for asset matching (replaces asset_pattern regex)
      - ubuntu
      - vulkan
      - x64
    integrity_sha256: ""                 # SHA256 checksum for integrity verification
    drift_policy: pin                    # One of: pin | track | notify
    disabled_reason: null                # Enum: boot_failure | build_failure | compat_blocked | arch_scoped | pending_validation
    drift_check_interval_hours: 0        # 0 = never auto-check; >0 means check upstream every N hours
    
    enabled: true
    always: false                        # smart cache: skip if manifest.json matches
    profile_names: []
```

### Field Definitions

| Field | Type | Required | Description |
|---|---|---|---|
| `channel` | string | yes | Source channel ID (e.g. `ggml-org`, `lemonade-sdk`, `rocm-official`) |
| `pinned_version` | string | yes | Explicit version identifier. **For prebuilt channels (ggml-org, lemonade-sdk):** `bXXXX` format (monotonic build number). **For git-based channels (rocm-official):** 40-char commit SHA (immutable, reproducible checkout). Never "latest". |
| `pinned_metadata` | object | for git-based | Optional metadata for git-based channels: `{branch, approx_date, commit_summary}`. Used for logging only; not used for checkout. |
| `floor_version` | string | no | Minimum acceptable version. If deployed version is older, startup is blocked. Null for source-build variants. |
| `rollback_version` | string | no | Previous version to fall back to if current version fails. Managed by provisioning system. |
| `asset_tokens` | array of strings | for prebuilts | Tokens that must all appear in the asset filename. Replaces fragile regex patterns. Order-independent. |
| `integrity_sha256` | string | no | SHA256 checksum of the asset. If provided, integrity is verified after download. |
| `drift_policy` | enum | yes | One of: `pin` (error if deployed ≠ pinned), `track` (auto-upgrade), `notify` (log and continue). Default: `pin`. |
| `disabled_reason` | enum | no | If variant is disabled, the machine-readable reason. Values: `boot_failure`, `build_failure`, `compat_blocked`, `arch_scoped`, `pending_validation`, `deprecated`. |
| `drift_check_interval_hours` | integer | no | How often to check if upstream has moved. 0 = never. Default: 0. |

---

## Asset Token Matching

Instead of error-prone regex patterns like `ubuntu-rocm.*x64\.(tar\.gz|zip)$`, tokens are explicit substrings:

**Example: matching ggml-org Vulkan asset**
```
Filename: llama-b8661-bin-ubuntu-vulkan-x64.tar.gz
Tokens:   [ubuntu, vulkan, x64]
Match:    ubuntu ✓, vulkan ✓, x64 ✓ → MATCH
```

**Example: matching ggml-org ROCm asset**
```
Filename: llama-b8661-bin-ubuntu-rocm-7.2-x64.tar.gz
Tokens:   [ubuntu, rocm-7.2, x64]
Match:    ubuntu ✓, rocm-7.2 ✓, x64 ✓ → MATCH

# If ROCm bumps to 7.3:
Filename: llama-b8700-bin-ubuntu-rocm-7.3-x64.tar.gz
Tokens:   [ubuntu, rocm-7.2, x64]   # ← OUT OF DATE TOKEN
Match:    ubuntu ✓, rocm-7.2 ✗, x64 ✓ → NO MATCH
# Spec-802 provisioner will fail with clear error: "rocm-7.2 token not found in any release asset"
```

**Token matching logic:**
```
asset_matches = all(token in asset_filename for token in asset_tokens)
```

Tokens are case-insensitive, order-independent, and match the first occurrence in the filename.

---

## Drift Policy Explained

Each variant declares how it handles upstream movement:

| Policy | Behavior | Use Case |
|---|---|---|
| `pin` | Error if `deployed_version ≠ pinned_version`. Requires manual version bump. | Production variants. Changes are reviewed before rolling out. |
| `track` | Auto-upgrade within channel if a newer version is available. | Nightly/canary deployments. New versions are tested in staging before production bump. |
| `notify` | Log a warning if deployed ≠ pinned, but continue running. | Development only. Warnings can be ignored in local testing. |

---

## Disabled Reason Enum

```
boot_failure       — Variant was disabled because it failed to start (e.g. "no backends are loaded")
build_failure      — Variant was disabled because the build failed (CMake error, linker error)
compat_blocked     — Variant fails on this hardware (HIP OOM, unsupported GPU, library missing)
arch_scoped        — Variant is only for specific hardware (e.g. gfx1151 Strix Halo, not gfx1100)
pending_validation — Variant benchmarked but not yet promoted (awaiting promotion gate)
deprecated         — Variant is no longer supported (upstream abandoned, significant regression)
```

Using an enum instead of free-form comments makes it possible to:
- Count how many variants are blocked per reason
- Automatically re-enable variants if blocking reason is fixed (e.g. new vLLM release fixes HIP OOM)
- Report inventory of what's failing and why

---

## Version Comparison

For variants within the same channel, version comparison is defined:

- **ggml-org**: `bXXXX` are monotonically increasing integers. `b8661 > b8660 > b8450`.
- **lemonade-sdk**: Independent counter, also monotonic. `lemonade:b1224 > lemonade:b1223`. Not comparable to ggml-org builds.
- **rocm-official**: Git-based. Canonical pin is the **full 40-char commit SHA** (immutable). Comparisons use commit dates from metadata, but checkout is always exact SHA. `a1b2c3d4e5f6... (2026-04-02)` vs `x9y8z7w6v5u4... (2026-03-30)`.

**Git-based provisioning (rocm-official):**
```bash
git clone https://github.com/ROCm/llama.cpp.git /build/src
git checkout a1b2c3d4e5f6...  # exact SHA, not date or branch
# This is reproducible, immutable, and unambiguous
```

**Drift detection logic:**
```
if current_channel != pinned_channel:
  # Channel mismatch (e.g. vulkan built from ggml, rocm built from lemonade)
  # Different channels can coexist; no drift if built from intended channel
  return no_drift

if current_version == pinned_version and current_channel == pinned_channel:
  return no_drift

# Drift exists if version or channel differs
return drift
```

---

## Integrity Verification

Every asset is accompanied by its SHA256 checksum:

```yaml
vulkan:
  pinned_version: b8583
  integrity_sha256: "abc123def456..."  # computed from: sha256sum(llama-b8583-bin-ubuntu-vulkan-x64.tar.gz)
```

The provisioner (spec-802) will:
1. Download the asset
2. Compute SHA256
3. Compare against declared checksum
4. If mismatch, fail with error and do not extract

---

## Updating the Version Registry

When a new version is benchmarked and validated (per spec-803), update the registry:

1. Run benchmarks (≥2 sessions)
2. Compute sha256 of the asset
3. Update `pinned_version` and `integrity_sha256` in registry
4. Update `last_benchmarked`, `benchmark_result_tok_s`, `benchmark_confidence`
5. Commit the change with message: `"backend-lifecycle: pin llama.cpp vulkan to b8661 (26.5 tok/s, validated)"`

---

## Backward Compatibility

Existing `config/project/backend-runtime.base.yaml` variants without these new fields will:
- Inherit defaults from `defaults:` section
- Be treated as `drift_policy: pin` (safest default)
- Still work with spec-802 provisioner (which checks for the new fields but doesn't require them)

A gradual migration path is provided: old-style variants can be converted to new-style by adding the new fields.

---

## Examples

### Example 1: Pinning Vulkan to b8583

```yaml
# In config/project/backend-runtime.base.yaml:
vulkan:
  backend: vulkan
  macro: llama-server-vulkan
  channel: ggml-org
  pinned_version: b8583
  floor_version: b8153
  asset_tokens: [ubuntu, vulkan, x64]
  integrity_sha256: "c1a2b3d4e5f6..."
  drift_policy: pin
  enabled: true
```

Any installed binary with version != b8583 will be flagged as drifted.

### Example 2: Tracking Lemonade ROCm

```yaml
rocm-lemonade:
  backend: rocm
  channel: lemonade-sdk
  pinned_version: "b1224"    # Note the quotes: lemonade uses string version IDs
  floor_version: "b1200"
  asset_tokens: [ubuntu, rocm]
  integrity_sha256: "..."
  drift_policy: notify       # Auto-upgrade within lemonade channel, but log warnings
  enabled: true
```

New lemonade builds will auto-download and deploy with logged notifications.

### Example 3: Source Build from ROCm Official

```yaml
rocm-gfx1100-official:
  backend: rocm
  channel: rocm-official
  pinned_version: "master@2026-03-30"
  source_build: true
  build_image: "rocm/dev-ubuntu-24.04:7.2.1"
  cmake_flags: "-DLLAMA_BUILD_SERVER=ON -DGGML_HIPBLAS=ON -DAMDGPU_TARGETS=gfx1100 -DCMAKE_BUILD_TYPE=Release"
  drift_policy: pin
  enabled: false             # disabled until manual validation
  disabled_reason: pending_validation
```

The provisioner will:
1. Spin up rocm/dev image at tag 7.2.1
2. Git clone rocm/llama.cpp at commit master (which was at 2026-03-30 when pinned)
3. Run cmake with specified flags
4. Build and place binary in versioned path
5. Create manifest.json

---

## Related Specifications

- **spec-802** — Build and Deployment Pipeline: How versions are provisioned, how manifests are created, how rollback works
- **spec-803** — Validation and Promotion Gates: How benchmarks flow into version registry, promotion criteria, measurement uncertainty handling

