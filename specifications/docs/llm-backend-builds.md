# Specification: LLM Backend Build Strategy

This document defines the strategy for acquiring and building LLM backend binaries (specifically `llama.cpp` and its variants) for the AUDiaLLMGateway.

## 1. Multi-Tier Backend Strategy

The Gateway supports a three-tier strategy for backend binaries:

1.  **Managed Releases (Primary):** The installer downloads pre-built binaries from GitHub releases (e.g., `ggml-org/llama.cpp`). These are tested and stable.
2.  **Source-Built Variants (Secondary):** For specialized hardware or forks (like TurboQuant), the Gateway supports building from source using local toolchains (CMake, GCC/MSVC, Vulkan SDK).
3.  **Local Overrides (User-Managed):** Users can provide their own binaries by setting the `executable` path in `config/local/stack.override.yaml` or `config/local/backend-runtime.override.yaml`.

## 2. Automatic Hardware Detection

To optimize native builds and selection, the Gateway performs automatic hardware detection during setup and configuration generation. For a detailed technical explanation of the detection logic, see the [Hardware Detection Deep Dive](hardware-detection-deep-dive.md).

### 2.1 AMD GFX Detection (`AUDIA_DETECTED_GFX`)

For AMD GPUs, the GFX architecture (e.g., `gfx1100` for RX 7900 GRE) is detected and stored in the `.env` file as `AUDIA_DETECTED_GFX`. This is used to drive the `-DAMDGPU_TARGETS` and `-DCMAKE_HIP_ARCHITECTURES` flags during CMake configuration.

**Detection Logic:**
1.  **Vulkan Device ID:** Parse `vulkaninfo --summary` for Vendor ID `0x1002` (AMD) and map the `deviceID` to a GFX string.
2.  **ROCm Product Name (Fallback):** Parse `rocm-smi --showproductname` for common product series (e.g., "7900" -> `gfx1100`).

### 2.2 Global Backend Selection (`LLAMA_BACKEND`)

The `LLAMA_BACKEND` variable in `.env` determines the primary acceleration path:
- `cuda`: NVIDIA GPUs.
- `rocm`: AMD GPUs via ROCm.
- `vulkan`: Cross-vendor GPU acceleration.
- `cpu`: Fallback CPU execution.

## 3. Backend Runtime Catalog

The `config/project/backend-runtime.base.yaml` file defines the catalog of available sources and build profiles.

### 3.1 Build Profiles

Build profiles define the CMake flags and dependencies needed for specific backends. For example, the `rocm-gfx` profile uses the detected GFX version:

```yaml
builds:
  rocm-gfx:
    backend: rocm
    configure_command: cmake -S . -B build ... -DAMDGPU_TARGETS=${AUDIA_DETECTED_GFX:-gfx1030;gfx1100} ...
```

### 3.2 Runtime Variants

Variants combine a **source** (GitHub release or Git repo) with a **build profile** (for source builds) or an **asset pattern** (for releases).

## 4. Integration with Setup Scripts

- **`scripts/detect-hardware.sh`:** Standalone detection script. Updates `.env` with recommended backend and detected GFX.
- **`scripts/docker-setup.sh`:** Interactive setup for Docker deployments. Populates `.env` with detected hardware settings.
- **`src/launcher/config_loader.py`:** Dynamically detects GFX during configuration generation if it's not already in the environment.

## 5. Build Requirements

- **Vulkan:** Requires the Vulkan SDK (can be bootstrapped via `scripts/bootstrap_vulkan_sdk.py`).
- **ROCm:** Requires the ROCm runtime and development headers (on Linux) or appropriate HIP/HIPBLAS libraries (on Windows). If a valid ROCm install already exists, the benchmark/build flow can seed a workspace-local cache automatically.
- **CUDA:** Requires the CUDA Toolkit.
