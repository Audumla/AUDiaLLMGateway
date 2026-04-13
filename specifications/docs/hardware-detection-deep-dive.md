# Specification: Hardware Detection Deep Dive

This document provides a detailed technical explanation of how AUDiaLLMGateway identifies host hardware (CPU, RAM, GPU) and uses that information to configure LLM backends.

## 1. Overview

Hardware detection is performed in three main contexts:
1.  **Host-side Scripts (`detect-hardware.sh`):** Used for manual or initial setup to populate the `.env` file.
2.  **Docker Setup (`docker-setup.sh`):** Interactive setup for Docker deployments.
3.  **Config Generation (`config_loader.py`):** Dynamically detects hardware during runtime if environment variables are missing.

## 2. Detection Mechanisms by Platform

### 2.1 NVIDIA GPUs (CUDA)
- **Primary Tool:** `nvidia-smi`
- **Logic:**
  - Check for the existence of the `nvidia-smi` executable.
  - Query GPU name and total VRAM using `--query-gpu=name,memory.total --format=csv,noheader`.
  - Also check for `nvcc` (CUDA toolkit) to verify developer headers are available for source builds.
- **Recommended Backend:** `cuda`

### 2.2 AMD GPUs (ROCm)
- **Primary Tools:** `vulkaninfo` (for GFX ID), `rocm-smi` (for fallback/monitoring), `/dev/kfd` (for Linux capability).
- **Architecture Detection (GFX):**
  - We use `vulkaninfo --summary` to extract the **Vendor ID** (`0x1002`) and **Device ID**.
  - The Device ID is mapped to a GFX architecture:
    - `0x744c` -> `gfx1100` (RDNA 3 / RX 7900)
    - `0x1586` -> `gfx1151` (RDNA 3.5/4 / Strix Halo / RX 8000)
    - `0x75a3` -> `gfx950` (CDNA 4 / Instinct MI350)
    - `0x15bf` -> `gfx1103` (Phoenix / Radeon 780M)
  - This is stored as `AUDIA_DETECTED_GFX` in `.env`.
- **ROCm Status:**
  - If `rocm-smi` is found, it is used to identify the product name.
  - If `/dev/kfd` exists (Linux only), we assume ROCm capability even if tools are missing.
- **Recommended Backend:** `rocm` (for Linux native), `rocm-uma-apu` (for APUs), or `vulkan` (cross-platform fallback).
- **APU Optimization:** For Ryzen AI / Phoenix / Strix Halo architectures, we utilize `LLAMA_HIP_UMA=ON` to optimize inference on shared system memory.

### 2.3 macOS GPUs (Metal)
- **Primary Tool:** `system_profiler SPDisplaysDataType`
- **Logic:**
  - Identify the `Chipset Model` (e.g., "Apple M2 Max", "AMD Radeon Pro 5500M").
  - If found on a "Darwin" (macOS) kernel, we assume Metal support.
- **Recommended Backend:** `metal`
- **Note:** Native `llama.cpp` universal binaries for macOS use Metal by default.

### 2.5 Generic GPU (Vulkan)
- **Primary Tool:** `vulkaninfo`
- **Logic:**
  - List all `deviceName` entries from `vulkaninfo --summary`.
  - Fallback: `lspci` (Linux) or generic display adapter checks.
- **Recommended Backend:** `vulkan`

### 2.6 Intel-Specific Backends (Future/Reference)
The Gateway includes profile definitions for Intel-specific acceleration, though these are currently considered "Tier 2" (untested in the primary dev environment):
- **SYCL (Windows):** For Intel Arc and Data Center GPUs.
- **OpenVINO (Linux):** Highly optimized for Intel NPUs and iGPUs (Meteor Lake+).

### 2.7 Distributed Backend (RPC)
- **Mechanism:** `llama.cpp` RPC backend.
- **Use Case:** Pooling VRAM across multiple networked machines to run massive models (e.g., Llama-3 400B).
- **Status:** Profile definitions included for future scaling.

### 2.8 CPU & Memory
- **CPU Name:** Extracted from `/proc/cpuinfo` (Linux), `sysctl` (macOS), or `wmic` (Windows).
- **Core Count:** `nproc` or `sysctl -n hw.ncpu`.
- **RAM:** `free` (Linux) or `sysctl -n hw.memsize` (macOS).

## 3. Environment Variables

The detection logic populates these variables:
- `LLAMA_BACKEND`: The global backend selection (`cuda`, `rocm`, `metal`, `vulkan`, or `cpu`).
- `AUDIA_DETECTED_GFX`: A comma-separated list of detected AMD architectures (e.g., `gfx1100,gfx1030`).
- `AUDIA_VULKAN_SDK_ROOT`: Local path to the Vulkan SDK if bootstrapped.

## 4. Unified Multi-GPU builds (Fat Binary)

When multiple AMD GPUs with different architectures are detected (e.g., RX 7900 and RX 6900), the Gateway automatically optimizes the build process:

1.  **Combined Architecture Targeting:** The system converts the detected GFX list (e.g., `gfx1100,gfx1030`) into a semicolon-separated list for CMake (`gfx1100;gfx1030`).
2.  **Single Fat Binary:** Instead of building separate versions, a single optimized binary is generated. This "fat binary" contains pre-compiled kernels for **every** detected card in the system.
3.  **Simplified Macros:** You no longer need separate macros for different cards. The standard `llama-server-rocm` or the optimized `llama-server-rocm-native` macro will automatically work at full speed on any of your detected GPUs.

### How to use
The Gateway handles this automatically. If you have multiple GPUs, your builds will simply take a few moments longer to compile for all targets, but you gain the ability to run any model on any card without configuration changes.

## 5. Why we don't *require* rocm-smi

While `rocm-smi` is the official AMD monitoring tool, it is not always installed on user machines (especially Windows). We prioritize `vulkaninfo` because:
1.  It is the standard for Vulkan-based cross-vendor applications.
2.  It reliably provides the **Device ID**, which is more accurate for build-time configuration than string-matching the product name.
3.  If `vulkaninfo` is missing, we then fall back to `rocm-smi` to attempt identification.

## 5. Docker Caveats

- **NVIDIA:** Requires the `nvidia-container-toolkit` to pass the GPU into the container.
- **AMD:** Requires passing `/dev/kfd` and `/dev/dri` device nodes into the container.
- **macOS:** Standard Docker containers on macOS do not have direct GPU passthrough to Linux-based containers. Hardware detection on macOS should be used for **native** deployments.
