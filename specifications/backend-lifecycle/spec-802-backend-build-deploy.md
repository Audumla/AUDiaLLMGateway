# Spec-802: Backend Build and Deployment Pipeline

**Phase:** 5 — Backend Lifecycle Governance  
**Date:** 2026-04-02  
**Status:** Draft  
**Related specs:** spec-801, spec-803

---

## Executive Summary

This specification defines how backend binaries transition from source or prebuilt release → versioned deployment → active runtime. It covers three provisioning paths (prebuilt download, Docker image pull, hermetic source build), the artifact versioning model, integrity verification, and rollback procedures.

**Key mechanisms:**
- **Versioned artifact storage** — multiple versions coexist; rollback = symlink swap
- **Per-variant symlinks** — each variant maintains its own `/app/runtime-root/{runtime_subdir}/active` symlink
- **Manifest contract** — every deployed binary writes a JSON record of what was deployed and when
- **Smart caching** — avoid re-provisioning if already at the pinned version
- **Floor version enforcement** — prevent startup with out-of-support binaries
- **Rollback support** — keep N-1 version available for immediate fallback

**Vocabulary standardization:** This spec uses `asset_tokens` (list of substrings) for asset matching, replacing the earlier `asset_pattern` (regex) and `asset_match_tokens` terminology. All three systems have been consolidated to use `asset_tokens` as the canonical vocabulary. See spec-801 for details.

---

## Problem Statement

The current provisioning system has several operational gaps:

1. **No versioned artifact storage** — binaries are downloaded to a single directory (`/app/runtime-root/{type}/bin/`). Upgrading overwrites the old binary. There is no easy rollback.

2. **Silent drift after re-provisioning** — if infrastructure is rebuilt and `version: latest` is specified, the new installation may silently pull a different binary than what was running before, with no way to detect this happened.

3. **No integrity verification** — downloaded assets are not checksummed. A corrupted download or MITM attack could introduce a different binary silently.

4. **No deployment metadata** — we don't record what was actually deployed, when, from which source. Debugging issues requires manual inspection of binary timestamps or `strings` output.

5. **Source-build variants are disabled** — `rocm-gfx1100-official-custom` is disabled partly because the build process is not standardised or documented. There is no hermetic build container, no cmake flag matrix, no post-build testing.

---

## Artifact Versioning Model

### Storage Layout

**Per-variant versioned paths:** Each variant (including sub-variants like rocm/gfx1100) has its own versioned storage:

```
/app/runtime-root/
  {runtime_subdir}/
    {channel}/
      {version}/
        bin/
          llama-server
        lib/
          *.so*
        manifest.json              ← metadata record of what's deployed
        
  cpu/
    ggml-org/
      b8583/
        bin/llama-server-cpu
        lib/
        manifest.json
  
  vulkan/
    ggml-org/
      b8583/
        bin/llama-server-vulkan
        lib/libvulkan.so*
        manifest.json
      b8450/                        ← previous version, kept for rollback
        bin/llama-server-vulkan
        lib/libvulkan.so*
        manifest.json
  
  rocm/
    ggml-org/
      b8583/
        bin/llama-server-rocm
        lib/*.so*
        manifest.json
    lemonade-sdk/
      b1224/
        bin/llama-server-rocm
        lib/*.so*
        manifest.json
    rocm-official/
      a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b/   ← git-based builds use full 40-char commit SHA
        bin/llama-server-rocm
        lib/*.so*
        manifest.json
  
  rocm/gfx1100/
    ggml-org/
      b8583/
        bin/llama-server-rocm
        lib/*.so*
        manifest.json
  
  rocm/gfx1030/
    ggml-org/
      b8583/
        bin/llama-server-rocm
        lib/*.so*
        manifest.json
  
  rocm/gfx1100/preview/
    rocm-official/
      a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b/
        bin/llama-server-rocm
        lib/*.so*
        manifest.json
```

### Active Symlink (Per-Variant)

The currently-active binary is accessed via a **per-variant symlink** inside the variant's runtime_subdir:

```
/app/runtime-root/cpu/active                    → /app/runtime-root/cpu/ggml-org/b8583/
/app/runtime-root/vulkan/active                 → /app/runtime-root/vulkan/ggml-org/b8583/
/app/runtime-root/rocm/active                   → /app/runtime-root/rocm/ggml-org/b8583/

/app/runtime-root/rocm/gfx1100/active           → /app/runtime-root/rocm/gfx1100/ggml-org/b8583/
/app/runtime-root/rocm/gfx1030/active           → /app/runtime-root/rocm/gfx1030/ggml-org/b8583/
/app/runtime-root/rocm/gfx1100/preview/active   → /app/runtime-root/rocm/gfx1100/preview/rocm-official/a1b2c3d4.../
```

This allows:
- **Per-variant version management** — each variant (including sub-variants like gfx1100, gfx1030) maintains separate version state
- **Instant rollback** — point symlink to previous version and restart
- **Atomic updates** — create new versioned directory, then swap symlink
- **Multi-version coexistence** — old version stays in place until explicitly cleaned up

### Manifest Contract

Every provisioned binary directory contains a `manifest.json` file:

```json
{
  "version": 1,
  "deployed_at": "2026-04-02T14:30:45Z",
  "channel": "ggml-org",
  "pinned_version": "b8583",
  "deployed_version": "b8583",
  "source_type": "github_release",
  "asset_url": "https://github.com/ggml-org/llama.cpp/releases/download/b8583/llama-b8583-bin-ubuntu-vulkan-x64.tar.gz",
  "asset_filename": "llama-b8583-bin-ubuntu-vulkan-x64.tar.gz",
  "integrity_sha256": "c1a2b3d4e5f6789...",
  "sha256_verified": true,
  "binary_path": "/app/runtime-root/vulkan/ggml-org/b8583/bin/llama-server-vulkan",
  "build_env_hash": "rocm-dev-ubuntu-24.04-7.2.1",  # null for prebuilt
  "drift_policy": "pin",
  "variant_id": "vulkan",
  "backtrace": {
    "provisioner": "spec-802-github-release",
    "provisioner_version": "1.0",
    "system_info": {
      "arch": "x86_64",
      "os": "linux",
      "kernel": "5.15.0-104-generic"
    }
  }
}
```

The manifest is:
- **Authoritative source of deployed version** — used to detect drift
- **Audit trail** — records when, what, and from where
- **Validation proof** — SHA256 verification is recorded in the manifest
- **Provisioning contract** — fields here are used by smart-cache logic

---

## Provisioning Paths

### Path 1: GitHub Release (Prebuilt)

**Trigger:** Variant with `source_build: false`, `channel: ggml-org | lemonade-sdk | lychee-tech`

**Provisioning steps:**

```
INPUT: variant config with channel=ggml-org, pinned_version=b8583, asset_tokens=[ubuntu, vulkan, x64]

1. Resolve release URL
   channel.asset_base_url template with version=b8583
   → "https://github.com/ggml-org/llama.cpp/releases/download/b8583/{asset}"

2. List release assets
   GET /repos/ggml-org/llama.cpp/releases/tags/b8583
   Filter: asset_url matches all tokens in asset_tokens
   Select: first match (should be only one)
   → llama-b8583-bin-ubuntu-vulkan-x64.tar.gz

3. Download asset
   GET https://github.com/ggml-org/llama.cpp/releases/download/b8583/llama-b8583-bin-ubuntu-vulkan-x64.tar.gz
   Save to: /tmp/llama-b8583-bin-ubuntu-vulkan-x64.tar.gz

4. Verify integrity
   Compute: sha256sum(/tmp/llama-...)
   Compare: against integrity_sha256 from backend-version-registry.yaml
   If mismatch: FAIL with error, do not extract

5. Extract to versioned path
   mkdir -p /app/runtime-root/vulkan/ggml-org/b8583/
   tar xzf /tmp/llama-... -C /app/runtime-root/vulkan/ggml-org/b8583/
   rm /tmp/llama-...

6. Create manifest.json
   Write manifest with deployed_version=b8583, deployed_at=NOW, sha256_verified=true

7. Update symlink (atomic)
   ln -sfn /app/runtime-root/vulkan/ggml-org/b8583/ /app/runtime-root/vulkan/active
   (Or use rename-and-swap if filesystem supports atomic rename)

OUTPUT: /app/runtime-root/vulkan/active points to b8583, manifest.json present
```

**Failure modes:**
- Asset not found → error: "no asset matches tokens [ubuntu, vulkan, x64]"
- Checksum mismatch → error: "sha256 verification failed; expected X, got Y"
- Extraction fails → error: "tar extraction failed; corrupted archive?"
- Network error → error: "failed to download from GitHub; check connectivity"

**Smart caching:**
```
if exists(/app/runtime-root/vulkan/ggml-org/b8583/manifest.json):
  if manifest.pinned_version == b8583:
    return SKIP (already at correct version)
  else:
    return PROVISION (version mismatch)
else:
  return PROVISION (not yet deployed)
```

### Path 2: Docker Image Pull

**Trigger:** Variant with `source_build: false`, `channel: docker | vllm-official | ollama-official`

**Provisioning steps:**

```
INPUT: variant config with image_ref="vllm/vllm-openai-rocm:v0.18.1" (never "latest")

1. Pull image
   docker pull vllm/vllm-openai-rocm:v0.18.1
   Capture: pulled image digest SHA256:abc123...

2. Extract to versioned path
   docker run --rm -v /app/runtime-root/vllm/official/v0.18.1:/out
     vllm/vllm-openai-rocm:v0.18.1 cp -r /usr/local/lib/python3.* /out/
   (or: create Docker container, export filesystem to tarball, extract)

3. Create manifest.json
   Write manifest with deployed_version=v0.18.1, docker_image_digest=SHA256:abc123...

4. Update symlink
   ln -sfn /app/runtime-root/vllm/official/v0.18.1/ /app/runtime-root/vllm/active

OUTPUT: /app/runtime-root/vllm/active points to v0.18.1
```

**Smart caching:**
```
if image_digest in manifest.json == currently_pulled_digest:
  return SKIP
else:
  return PROVISION
```

### Path 3: Hermetic Source Build

**Trigger:** Variant with `source_build: true`, `build_image`, `cmake_flags`

**Provisioning steps:**

```
INPUT: variant config with:
  channel=rocm-official
  pinned_version=a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b  # full 40-char commit SHA
  build_image=rocm/dev-ubuntu-24.04:7.2.1
  cmake_flags=-DLLAMA_BUILD_SERVER=ON -DGGML_HIPBLAS=ON -DAMDGPU_TARGETS=gfx1100 ...

1. Prepare build script
   Create: /tmp/build_llama_rocm.sh
   Content:
     #!/bin/bash
     set -e
     git clone https://github.com/ROCm/llama.cpp.git /build/llama
     cd /build/llama
     git checkout a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b  # exact commit SHA (reproducible, immutable)
     mkdir build && cd build
     cmake .. {cmake_flags}
     cmake --build . --config Release --parallel $(nproc)
     cp bin/llama-server /output/llama-server
     cp bin/*.so* /output/  # copy shared libraries

2. Run build in hermetic container
   docker run --rm -v /tmp/build_llama_rocm.sh:/build.sh \
     -v /app/runtime-root/rocm/gfx1100/rocm-official/a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b/:/output \
     rocm/dev-ubuntu-24.04:7.2.1 \
     bash /build.sh

3. Record build environment hash
   Compute: sha256(rocm/dev-ubuntu-24.04:7.2.1 digest + cmake_flags string)
   Store in manifest as build_env_hash

4. Create manifest.json
   deployed_version=a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b  # commit SHA
   source_type=git
   source_url=https://github.com/ROCm/llama.cpp.git
   build_image_digest=rocm/dev:7.2.1-SHA256:...
   cmake_flags=<the full cmake invocation used>

5. Post-build smoke test
   /app/runtime-root/rocm/gfx1100/rocm-official/a1b2c3d4.../bin/llama-server --list-devices
   If fails: remove versioned directory, report error

6. Update symlink
   ln -sfn /app/runtime-root/rocm/gfx1100/rocm-official/a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b/ \
           /app/runtime-root/rocm/gfx1100/preview/active

OUTPUT: /app/runtime-root/rocm/gfx1100/preview/active points to source-built binary
```

**Failure modes:**
- Git checkout fails (commit not found) → error: "commit at 2026-03-30 not found in rocm/llama.cpp"
- CMake configuration fails → error: "cmake config failed; check cmake_flags"
- Build fails → error: "cmake build failed; review build log"
- Binary doesn't exist post-build → error: "llama-server not found in /output/"
- Smoke test fails → error: "llama-server --list-devices failed; binary corrupted or missing deps"

---

## Floor Version Enforcement

At startup, before any model loads:

```
if manifest.deployed_version < floor_version:
  LOG ERROR: "Deployed version {deployed} is below floor {floor}. Refusing to start."
  EXIT(1)
```

Example:
```yaml
vulkan:
  pinned_version: b8583
  floor_version: b8153
```

If somehow b8150 is deployed, the system will refuse to start with a clear error.

---

## Drift Detection

Periodically (or on-demand), compare deployed version against pinned version:

```
deployed_version = manifest.deployed_version (from active/manifest.json)
pinned_version = backend-runtime config
deployed_channel = manifest.channel
pinned_channel = backend-runtime config

if deployed_channel != pinned_channel:
  DRIFT: "Deployed from {deployed_channel}, expected {pinned_channel}"

if deployed_version != pinned_version:
  DRIFT: "Deployed version {deployed_version}, expected {pinned_version}"

if drift_policy == "pin":
  LOG ERROR: DRIFT; suggest manual intervention or explicit override
if drift_policy == "track":
  LOG WARN: DRIFT; re-provision to current pinned version
if drift_policy == "notify":
  LOG INFO: DRIFT; continue running (development mode)
```

---

## Rollback Procedure

To roll back to a previous version:

```
USAGE: rollback_variant vulkan

1. Check manifest for previous version
   /app/runtime-root/vulkan/active/manifest.json reads deployed_version=b8583
   Look for /app/runtime-root/vulkan/ggml-org/b8450/manifest.json (N-1 version)

2. Verify previous version is healthy
   /app/runtime-root/vulkan/ggml-org/b8450/bin/llama-server --list-devices
   If fails: abort rollback

3. Swap symlink
   ln -sfn /app/runtime-root/vulkan/ggml-org/b8450/ /app/runtime-root/vulkan/active

4. Restart service
   systemctl restart llama-swap  (or docker restart)

5. Verify
   curl http://localhost:41080/v1/models
   If responsive: rollback successful

OUTPUT: System running b8450 instead of b8583
```

To keep N-1 versions:
```
# Cleanup: remove versions older than N-1
for version in /app/runtime-root/vulkan/ggml-org/*/; do
  if [[ $version != /app/runtime-root/vulkan/ggml-org/b8583/ && \
        $version != /app/runtime-root/vulkan/ggml-org/b8450/ ]]; then
    rm -rf $version
  fi
done
```

---

## Provisioning Orchestration

The provisioning system is invoked via the existing `process_manager.py` or new `backend_provisioner.py`:

```python
# Pseudocode
def provision_backends(backend_runtime_config, backend_version_registry):
  """
  Main entry point for provisioning all backends.
  Called during: installation, infrastructure setup, version bump, manual provision command
  """
  
  for variant_name, variant_config in backend_runtime_config.variants.items():
    if not variant_config.enabled:
      continue
    
    manifest = read_manifest(variant_config.runtime_subdir)
    
    # Smart cache: skip if already at correct version
    if manifest and manifest.pinned_version == variant_config.pinned_version:
      log.info(f"{variant_name}: already at {variant_config.pinned_version}, skipping")
      continue
    
    # Determine provisioning path
    if variant_config.source_build:
      provision_source_build(variant_name, variant_config, backend_version_registry)
    elif variant_config.channel in ["vllm-official", "ollama-official"]:
      provision_docker_image(variant_name, variant_config)
    else:
      provision_github_release(variant_name, variant_config, backend_version_registry)
    
    # Update symlink
    symlink_to_active(variant_name, variant_config)
    
    log.info(f"{variant_name}: provisioned {variant_config.pinned_version}")

def startup_checks():
  """
  Called at service startup.
  """
  for variant_name, variant_config in backend_runtime_config.variants.items():
    if not variant_config.enabled:
      continue
    
    manifest = read_manifest(variant_config.runtime_subdir)
    
    # Floor version check
    if manifest.deployed_version < variant_config.floor_version:
      log.error(f"{variant_name}: deployed version {manifest.deployed_version} is below floor {variant_config.floor_version}")
      exit(1)
    
    # Drift detection
    if manifest.deployed_version != variant_config.pinned_version:
      if variant_config.drift_policy == "pin":
        log.error(f"{variant_name}: drift detected (deployed={manifest.deployed_version}, pinned={variant_config.pinned_version}). Policy is 'pin', refusing to start.")
        exit(1)
      elif variant_config.drift_policy == "notify":
        log.warn(f"{variant_name}: drift detected (deployed={manifest.deployed_version}, pinned={variant_config.pinned_version}). Policy is 'notify', continuing anyway.")
```

---

## Manifest Schema (benchmark-result-schema.yaml)

See spec-803 for the full manifest.json schema and validation rules.

---

## Related Specifications

- **spec-801** — Backend Version Registry: Defines the version registry, pinned versions, integrity checksums, drift policies
- **spec-803** — Validation and Promotion Gates: How new versions are validated before being promoted to production

---

## Appendix: CMake Build Matrix

### rocm-gfx1100-official

```bash
cmake .. \
  -DLLAMA_BUILD_SERVER=ON \
  -DGGML_HIPBLAS=ON \
  -DAMDGPU_TARGETS=gfx1100 \
  -DCMAKE_HIP_ARCHITECTURES=gfx1100 \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=/app/runtime-root/rocm/rocm-official/gfx1100/master@DATE/
```

### rocm-gfx1030-official

```bash
cmake .. \
  -DLLAMA_BUILD_SERVER=ON \
  -DGGML_HIPBLAS=ON \
  -DAMDGPU_TARGETS=gfx1030;gfx1100 \
  -DCMAKE_HIP_ARCHITECTURES=gfx1030;gfx1100 \
  -DCMAKE_BUILD_TYPE=Release
```

### zinc-vulkan (Zig-based)

```bash
# Zinc uses Zig build system, not CMake
# See: https://github.com/zolotukhin/zinc
cd /build/zinc
zig build -Doptimize=ReleaseFast -Dtarget=x86_64-linux
cp zig-cache/bin/zinc /output/zinc
```

