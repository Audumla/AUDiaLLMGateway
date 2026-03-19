#!/usr/bin/env bash
# detect-hardware.sh
# Detects GPU and system hardware then recommends (or applies) the optimal
# LLAMA_BACKEND setting for AUDiaLLMGateway.
#
# Usage:
#   ./scripts/detect-hardware.sh           # detect and print recommendations
#   ./scripts/detect-hardware.sh --apply   # also write LLAMA_BACKEND to .env
#
# Run this from the repo root (where .env lives).
set -euo pipefail

APPLY=false
for arg in "$@"; do
    [ "$arg" = "--apply" ] && APPLY=true
done

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# ── Colours ─────────────────────────────────────────────────────────────────
if [ -t 1 ]; then
    BOLD='\033[1m'; RESET='\033[0m'; GREEN='\033[32m'; YELLOW='\033[33m'
    CYAN='\033[36m'; RED='\033[31m'
else
    BOLD=''; RESET=''; GREEN=''; YELLOW=''; CYAN=''; RED=''
fi

header() { echo -e "\n${BOLD}${CYAN}=== $* ===${RESET}"; }
ok()     { echo -e "  ${GREEN}✔${RESET}  $*"; }
warn()   { echo -e "  ${YELLOW}⚠${RESET}  $*"; }
info()   { echo -e "  ${CYAN}→${RESET}  $*"; }
fail()   { echo -e "  ${RED}✘${RESET}  $*"; }

# ── GPU Detection ────────────────────────────────────────────────────────────
header "GPU Detection"

HAS_NVIDIA=false
HAS_AMD=false
HAS_VULKAN=false
HAS_INTEL_GPU=false
GPU_NAMES=()
VRAM_MB=0

# NVIDIA via nvidia-smi
if command -v nvidia-smi >/dev/null 2>&1; then
    NVIDIA_OUT=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo "")
    if [ -n "$NVIDIA_OUT" ]; then
        HAS_NVIDIA=true
        while IFS=',' read -r gpu_name vram; do
            gpu_name="${gpu_name# }"; vram="${vram# }"
            ok "NVIDIA GPU: $gpu_name ($vram VRAM)"
            GPU_NAMES+=("$gpu_name")
            # Parse VRAM (e.g. "8192 MiB" or "24576 MiB")
            vram_num=$(echo "$vram" | grep -oP '^\d+' || echo "0")
            [ "$vram_num" -gt "$VRAM_MB" ] && VRAM_MB=$vram_num
        done <<< "$NVIDIA_OUT"
        # Check CUDA runtime available
        if command -v nvcc >/dev/null 2>&1; then
            CUDA_VER=$(nvcc --version 2>/dev/null | grep release | grep -oP '[\d.]+' | head -1)
            ok "CUDA toolkit: $CUDA_VER"
        else
            warn "CUDA toolkit (nvcc) not in PATH — runtime will still work via Container Toolkit"
        fi
    fi
fi

# AMD via rocm-smi or /dev/kfd
if command -v rocm-smi >/dev/null 2>&1; then
    AMD_OUT=$(rocm-smi --showproductname --csv 2>/dev/null | grep -v "^Device\|^=\|^$" || echo "")
    if [ -n "$AMD_OUT" ]; then
        HAS_AMD=true
        while IFS=',' read -r _ gpu_name; do
            gpu_name="${gpu_name# }"
            ok "AMD GPU (ROCm): $gpu_name"
            GPU_NAMES+=("$gpu_name")
        done <<< "$AMD_OUT"
    fi
elif [ -e /dev/kfd ]; then
    HAS_AMD=true
    AMD_PCI=$(lspci 2>/dev/null | grep -iE 'AMD|Radeon' || echo "")
    if [ -n "$AMD_PCI" ]; then
        gpu_name=$(echo "$AMD_PCI" | head -1 | sed 's/.*: //')
        ok "AMD GPU (via /dev/kfd): $gpu_name"
        GPU_NAMES+=("$gpu_name")
    else
        ok "AMD GPU (via /dev/kfd — name unknown)"
    fi
fi

# Vulkan via vulkaninfo
if command -v vulkaninfo >/dev/null 2>&1; then
    VULKAN_GPUS=$(vulkaninfo --summary 2>/dev/null | grep -i "deviceName" | sed 's/.*= //' || echo "")
    if [ -n "$VULKAN_GPUS" ]; then
        HAS_VULKAN=true
        while IFS= read -r vk_gpu; do
            ok "Vulkan device: $vk_gpu"
        done <<< "$VULKAN_GPUS"
    fi
elif lspci 2>/dev/null | grep -qiE 'vga|display|3d'; then
    # Any display adapter detected — Vulkan likely works even without vulkaninfo installed
    OTHER_GPU=$(lspci 2>/dev/null | grep -iE 'vga|display|3d' | head -1 | sed 's/.*: //')
    if ! $HAS_NVIDIA && ! $HAS_AMD; then
        HAS_VULKAN=true
        ok "GPU via lspci (Vulkan candidate): $OTHER_GPU"
        [[ "$OTHER_GPU" == *"Intel"* ]] && HAS_INTEL_GPU=true
    else
        info "Vulkan available on existing GPU: $OTHER_GPU"
        HAS_VULKAN=true
    fi
fi

if ! $HAS_NVIDIA && ! $HAS_AMD && ! $HAS_VULKAN; then
    warn "No GPU detected — will run on CPU"
fi

# ── CPU & Memory ─────────────────────────────────────────────────────────────
header "CPU & Memory"

CPU_MODEL=$(grep -m1 'model name' /proc/cpuinfo 2>/dev/null | sed 's/.*: //' || sysctl -n machdep.cpu.brand_string 2>/dev/null || echo "Unknown")
CPU_CORES=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo "?")
ok "CPU: $CPU_MODEL ($CPU_CORES cores)"

if command -v free >/dev/null 2>&1; then
    RAM_TOTAL=$(free -h | awk '/^Mem:/ {print $2}')
    RAM_AVAIL=$(free -h | awk '/^Mem:/ {print $7}')
    ok "RAM: ${RAM_TOTAL} total, ${RAM_AVAIL} available"
elif command -v sysctl >/dev/null 2>&1; then
    RAM_BYTES=$(sysctl -n hw.memsize 2>/dev/null || echo "0")
    RAM_GB=$(( RAM_BYTES / 1024 / 1024 / 1024 ))
    ok "RAM: ${RAM_GB}GB total"
fi

# ── Disk Space ───────────────────────────────────────────────────────────────
header "Disk Space"

MODEL_DIR="${MODEL_ROOT:-$ROOT_DIR/models}"
if [ -d "$MODEL_DIR" ]; then
    DISK_AVAIL=$(df -h "$MODEL_DIR" | awk 'NR==2 {print $4}')
    ok "Models dir ($MODEL_DIR): $DISK_AVAIL available"
else
    warn "Models directory not found: $MODEL_DIR"
fi

# ── Recommendation ───────────────────────────────────────────────────────────
header "Recommended Configuration"

if $HAS_NVIDIA; then
    RECOMMENDED_BACKEND="cuda"
    info "Primary backend: ${BOLD}cuda${RESET} — NVIDIA GPU detected"
    info "Also available:  ${BOLD}vulkan${RESET} — set LLAMA_BACKEND=vulkan in .env to switch"
    if [ "$VRAM_MB" -gt 0 ]; then
        if [ "$VRAM_MB" -ge 16384 ]; then
            info "VRAM ${VRAM_MB}MB — can run large models (13B+ Q4, 7B Q8)"
        elif [ "$VRAM_MB" -ge 8192 ]; then
            info "VRAM ${VRAM_MB}MB — suited for 7B Q4-Q6 or 3B Q8 models"
        else
            info "VRAM ${VRAM_MB}MB — suited for 3B Q4 or smaller models"
        fi
    fi
elif $HAS_AMD; then
    RECOMMENDED_BACKEND="rocm"
    info "Primary backend: ${BOLD}rocm${RESET} — AMD GPU with ROCm detected"
    info "Also available:  ${BOLD}vulkan${RESET} — set LLAMA_BACKEND=vulkan in .env to switch"
elif $HAS_VULKAN; then
    RECOMMENDED_BACKEND="vulkan"
    info "Primary backend: ${BOLD}vulkan${RESET} — GPU detected, no CUDA/ROCm runtime"
    if $HAS_INTEL_GPU; then
        info "Intel GPU — Vulkan inference supported (may be slower than discrete GPU)"
    fi
else
    RECOMMENDED_BACKEND="cpu"
    info "Primary backend: ${BOLD}cpu${RESET} — no GPU detected"
    info "Recommended threads: $CPU_CORES (set llama_swap.n_threads in stack.override.yaml)"
fi

# ── Current .env state ───────────────────────────────────────────────────────
header "Current Settings"

ENV_FILE="$ROOT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    CURRENT_BACKEND=$(grep -E '^LLAMA_BACKEND=' "$ENV_FILE" 2>/dev/null | cut -d= -f2 || echo "(not set)")
    if [ "$CURRENT_BACKEND" = "(not set)" ]; then
        warn "LLAMA_BACKEND not set in .env — defaults to auto-detection in container"
    elif [ "$CURRENT_BACKEND" = "$RECOMMENDED_BACKEND" ]; then
        ok "LLAMA_BACKEND=$CURRENT_BACKEND (matches recommendation)"
    else
        warn "LLAMA_BACKEND=$CURRENT_BACKEND (recommendation: $RECOMMENDED_BACKEND)"
    fi
else
    warn ".env not found at $ENV_FILE"
fi

# ── Apply ────────────────────────────────────────────────────────────────────
if $APPLY; then
    header "Applying"
    if [ ! -f "$ENV_FILE" ]; then
        cp "$ROOT_DIR/config/env.example" "$ENV_FILE" 2>/dev/null || touch "$ENV_FILE"
        info "Created $ENV_FILE from template"
    fi
    if grep -q '^LLAMA_BACKEND=' "$ENV_FILE" 2>/dev/null; then
        sed -i "s|^LLAMA_BACKEND=.*|LLAMA_BACKEND=$RECOMMENDED_BACKEND|" "$ENV_FILE"
    else
        echo "LLAMA_BACKEND=$RECOMMENDED_BACKEND" >> "$ENV_FILE"
    fi
    ok "Written LLAMA_BACKEND=$RECOMMENDED_BACKEND to .env"
    info "Restart the stack to apply: docker compose up -d"
else
    echo
    echo -e "  To apply: ${BOLD}./scripts/detect-hardware.sh --apply${RESET}"
    echo -e "  Or set manually in .env: ${BOLD}LLAMA_BACKEND=$RECOMMENDED_BACKEND${RESET}"
fi

echo
