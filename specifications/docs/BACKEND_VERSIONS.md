# Supported llama.cpp Backend Versions

## Overview

The AUDia LLM Gateway supports **8 different llama.cpp backend configurations** across 4 main inference platforms. Of these:
- **4 backends are actively enabled** by default
- **4 specialized variants are available** but disabled to reduce boot time

For the maintained machine-readable source/release catalog, see:

- [benchmarks/data/backend-benchmarks/backend-catalog.yaml](../../benchmarks/data/backend-benchmarks/backend-catalog.yaml)
- [benchmarks/data/backend-benchmarks/engine-version-catalog.yaml](../../benchmarks/data/backend-benchmarks/engine-version-catalog.yaml)
- [benchmarks/docs/backend-catalog.md](../../benchmarks/docs/backend-catalog.md)
- [benchmarks/docs/engine-version-catalog.md](../../benchmarks/docs/engine-version-catalog.md)

---

## Active Backends (Enabled by Default)

These backends are automatically detected and provisioned on first run.

### 1. **CPU Backend**

```yaml
Backend: cpu
Source:  ggml-org/llama.cpp (GitHub releases)
Version: ${LLAMA_VERSION} (default: latest)
Runtime: ubuntu-x64
```

**Use Case:** CPU-only inference (no GPU required)
**Performance:** Slowest but most compatible
**Asset Pattern:** `ubuntu-x64.(tar.gz|zip)`

---

### 2. **CUDA Backend (NVIDIA GPU)**

```yaml
Backend: cuda
Source:  ggml-org/llama.cpp (GitHub releases)
Version: ${LLAMA_VERSION} (default: latest)
Runtime: ubuntu-x64
```

**Use Case:** NVIDIA GPU acceleration
**Performance:** Fast, widely supported
**Requirements:** NVIDIA GPU + CUDA drivers
**Asset Pattern:** `ubuntu-x64.(tar.gz|zip)`

---

### 3. **ROCm Backend (AMD GPU - Standard)**

```yaml
Backend: rocm
Source:  ggml-org/llama.cpp (GitHub releases)
Version: ${LLAMA_VERSION} (default: latest)
Runtime: ubuntu-rocm.*x64
```

**Use Case:** AMD GPU acceleration (generic)
**Performance:** Fast, standard ROCm support
**Requirements:** AMD GPU + ROCm drivers
**Asset Pattern:** `ubuntu-rocm.*x64.(tar.gz|zip)`

The gateway also exposes a selectable `qwen27_fast_rocm_latest` deployment
that points at the versioned `llama-server-rocm-ggml-latest` alias for the
current ggml ROCm lane.

---

### 4. **Vulkan Backend (Cross-Platform GPU)**

```yaml
Backend: vulkan
Source:  ggml-org/llama.cpp (GitHub releases)
Version: ${LLAMA_VERSION} (default: latest)
Runtime: ubuntu-vulkan.*x64
```

**Use Case:** Cross-platform GPU acceleration (AMD, Intel, NVIDIA via Vulkan)
**Performance:** Fast, hardware agnostic
**Requirements:** Vulkan-compatible GPU + drivers
**Asset Pattern:** `ubuntu-vulkan.*x64.(tar.gz|zip)`

**Currently Running:** ✅ Active on gpu-host.example (AMD Radeon)

---

## Specialized Variants (Disabled by Default)

These are custom-built variants for specific GPU architectures. They are **disabled** because they require complex build processes during startup and have caused reliability issues.

### 5. **ROCm GFX1100 Official Current**

```yaml
Backend:      rocm-gfx1100-official-current
Source:       github.com/ROCm/llama.cpp (git clone)
Branch:       main
GPU Targets:  gfx1030, gfx1100
Build:        Custom CMake with GGML_HIPBLAS
Status:       ❌ DISABLED (boot failures)
```

**Why Disabled:** Git clone fails during container startup, blocks service launch

---

### 6. **ROCm GFX1100 Official Preview**

```yaml
Backend:      rocm-gfx1100-official-preview
Source:       github.com/ROCm/llama.cpp (git clone)
Branch:       ${ROCM_LLAMA_CPP_PREVIEW_REF}
Current Ref:  rocm-7.11.0-preview
GPU Targets:  gfx1030, gfx1100
Build:        Custom CMake with GGML_HIPBLAS
Status:       ❌ DISABLED (boot failures)
```

**Why Disabled:** Git clone fails during container startup, blocks service launch

---

### 7. **ROCm GFX1030 Official Current**

```yaml
Backend:      rocm-gfx1030-official-current
Source:       github.com/ROCm/llama.cpp (git clone)
Branch:       main
GPU Targets:  gfx1030, gfx1100
Build:        Custom CMake with GGML_HIPBLAS
Status:       ❌ DISABLED (boot failures)
```

**Why Disabled:** Git clone fails during container startup, blocks service launch

---

### 8. **ROCm GFX1030 Lemonade**

```yaml
Backend:      rocm-gfx1030-lemonade-main
Source:       github.com/lemonade-sdk/llamacpp-rocm (git clone)
Branch:       main
GPU Targets:  gfx1030, gfx1100
Build:        Custom CMake with GGML_HIPBLAS
Status:       ❌ DISABLED (CMake failures)
```

**Why Disabled (historical path):** Repository clone/CMake failures prevented the old
startup path from compiling. The maintained Lemonade nightly channel is tracked in
the benchmark backend catalog.

---

## Version Information

### Minimum Version Requirements

| Model Family | Minimum Build | Reason |
|--------------|--------------|--------|
| Qwen 3.5 | **b8153** | Model compatibility & optimizations |
| Qwen 2.7 | latest | Standard support |
| Other models | latest | Recommended for best results |

### Version Format

Llama.cpp uses **build numbers** (e.g., `b8153`, `b8429`, `b1217`) instead of semantic versioning.

**Reference:**
- `b8153` - Minimum for Qwen 3.5 models
- `b8429` - rocm-ggml version (currently cached)
- `b1217` - rocm-lemonade version (currently cached)
- `latest` - Auto-selects newest from GitHub releases

### Currently Configured

```
LLAMA_VERSION=latest
LLAMA_BACKEND=vulkan
ROCM_LLAMA_CPP_PREVIEW_REF=rocm-7.11.0-preview
```

---

## Backend Comparison Matrix

| Feature | CPU | CUDA | ROCm | Vulkan |
|---------|-----|------|------|--------|
| **Speed** | ⭐ Slow | ⭐⭐⭐⭐⭐ Fast | ⭐⭐⭐⭐ Fast | ⭐⭐⭐⭐ Fast |
| **GPU Required** | ❌ No | ✅ NVIDIA | ✅ AMD | ✅ Any (AMD/Intel/NVIDIA) |
| **Complexity** | ⭐ Simple | ⭐⭐⭐ Moderate | ⭐⭐ Moderate | ⭐⭐ Moderate |
| **Boot Time** | Fast | Moderate | Moderate | Fast |
| **Compatibility** | ✅ Universal | ✅ NVIDIA only | ✅ AMD only | ✅ Universal (via Vulkan) |
| **Maintenance** | ✅ Easy | ⚠️ Requires CUDA | ⚠️ Requires ROCm | ✅ Easy |
| **Status** | ✅ Active | ✅ Active | ✅ Active | ✅ Active (Currently in use) |

---

## How Backends Are Selected

### Auto-Detection Process (at container startup)

1. **Detection Order:**
   - Check LLAMA_BACKEND environment variable
   - If set to specific backend: use that
   - If set to `auto`: auto-detect based on system

2. **Auto-Detection Checks (for `auto` mode):**
   ```
   Check for: NVIDIA CUDA drivers → Use CUDA backend
   Check for: AMD ROCm drivers → Use ROCm backend
   Check for: Vulkan-capable GPU → Use Vulkan backend
   Fallback: Use CPU backend
   ```

3. **Current Configuration:**
   ```
   LLAMA_BACKEND=vulkan (explicitly set)
   ```
   This forces Vulkan backend regardless of available hardware.

---

## Enabling Disabled Variants

To enable a disabled variant (e.g., for testing):

### Edit `config/local/backend-runtime.override.yaml`:

```yaml
variants:
  rocm-gfx1100-official-current:
    enabled: true  # Change from false to true
```

### Then restart services:

```bash
docker compose down
docker compose up -d
```

**⚠️ Warning:** These variants are disabled for a reason. They may fail during startup if:
- Network connectivity is unavailable (git clone fails)
- Build dependencies are missing
- GPU drivers don't match expectations

---

## Runtime Locations

When a backend is provisioned, it's downloaded/built to:

```
config/data/backend-runtime/
├── cpu/           (CPU binary)
├── cuda/          (CUDA binary)
├── rocm/          (ROCm binary)
├── vulkan/        (Vulkan binary)
└── rocm/
    ├── gfx1030/   (GFX1030 custom builds - if enabled)
    └── gfx1100/   (GFX1100 custom builds - if enabled)
```

---

## Troubleshooting Backend Issues

### Problem: "Backend not found"

**Solution:** Restart services to trigger auto-detection
```bash
docker compose down
docker compose up -d
```

### Problem: "Specific GPU not detected"

**Solution:** Change LLAMA_BACKEND in .env
```
LLAMA_BACKEND=vulkan    # Force Vulkan
LLAMA_BACKEND=rocm      # Force ROCm
LLAMA_BACKEND=cuda      # Force CUDA
LLAMA_BACKEND=cpu       # Force CPU
```

### Problem: "Build failed for custom variant"

**Solution:** Ensure enabled variant has:
1. Network access (for git clone)
2. Build tools installed
3. Correct GPU architecture specified
4. Sufficient disk space

---

## Summary

| Category | Details |
|----------|---------|
| **Total Backends** | 8 (4 active, 4 specialized) |
| **Actively Used** | 4 (CPU, CUDA, ROCm, Vulkan) |
| **Currently Running** | Vulkan (AMD Radeon GPU) |
| **Minimum llama.cpp** | b8153 (for Qwen 3.5 models) |
| **Default Version** | latest (auto-updated from GitHub) |
| **Boot Impact** | Low (4 disabled = faster startup) |
| **Customizable** | ✅ Yes (edit override.yaml) |

---

## Related Documentation

- [SERVER_DIAGNOSTICS.md](SERVER_DIAGNOSTICS.md) - Current server status
- [DOCKER_AUTOSTART.md](DOCKER_AUTOSTART.md) - Configuration guide
- [.env](.env) - Environment variables
- [config/local/backend-runtime.override.yaml](config/local/backend-runtime.override.yaml) - Local overrides
- [config/project/backend-runtime.base.yaml](config/project/backend-runtime.base.yaml) - Base definitions

---

**Last Updated:** 2026-03-25
**Status:** All active backends verified operational
**Server gpu-host.example:** Running Vulkan backend ✅
