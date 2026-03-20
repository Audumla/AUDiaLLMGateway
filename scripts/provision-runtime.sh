#!/bin/bash
# provision-runtime.sh
# Downloads and provisions llama.cpp binaries into a persistent runtime directory.
# Runs inside the backend container on first start (or when hardware changes).
# Results are cached under a backend-specific subdirectory to avoid
# re-downloading and to prevent cross-backend runtime drift.
set -e

RUNTIME_ROOT="${RUNTIME_ROOT:-/app/runtime-root}"
DEFAULT_SWAP_CONFIG="${LLAMA_SWAP_CONFIG_PATH:-/app/config/llama-swap.generated.yaml}"
DEFAULT_SWAP_ADDR="${LLAMA_SWAP_LISTEN_ADDR:-0.0.0.0:41080}"
DEFAULT_SWAP_WAIT_SECONDS="${LLAMA_SWAP_CONFIG_WAIT_SECONDS:-120}"

sync_backend_plugins() {
    local _bin_dir="$1"
    local _lib_dir="$2"
    # ggml_backend_load_all() scans the executable directory for backend plugins.
    # Re-sync them on every container start, not just after a fresh provision,
    # so persisted runtime volumes stay runnable across image/container changes.
    for _so in "$_lib_dir"/libggml-*.so; do
        [ -f "$_so" ] || continue
        _name=$(basename "$_so")
        case "$_name" in
            libggml.so|libggml-base.so) continue ;;
        esac
        ln -sf "$_so" "$_bin_dir/$_name"
    done
}

ensure_apt_packages() {
    if [ "$#" -eq 0 ]; then
        return
    fi

    MISSING_PACKAGES=""
    for _pkg in "$@"; do
        if ! dpkg -s "$_pkg" >/dev/null 2>&1; then
            MISSING_PACKAGES="$MISSING_PACKAGES $_pkg"
        fi
    done

    if [ -n "$MISSING_PACKAGES" ]; then
        echo "  Installing runtime packages:$MISSING_PACKAGES"
        apt-get update -qq
        # shellcheck disable=SC2086
        apt-get install -y --no-install-recommends $MISSING_PACKAGES
        rm -rf /var/lib/apt/lists/*
    fi
}

# ---------------------------------------------------------------------------
# 1. Hardware Detection
#    LLAMA_BACKEND env var overrides auto-detection.
#    Values: auto | cuda | rocm | vulkan | cpu
# ---------------------------------------------------------------------------
HAS_NVIDIA=false
HAS_AMD=false
HAS_VULKAN=false

if [ -n "$LLAMA_BACKEND" ] && [ "$LLAMA_BACKEND" != "auto" ]; then
    echo "--- Backend forced by LLAMA_BACKEND=$LLAMA_BACKEND ---"
    case "$LLAMA_BACKEND" in
        cuda)   HAS_NVIDIA=true ;;
        rocm)   HAS_AMD=true ;;
        vulkan) HAS_VULKAN=true ;;
        cpu)    ;;
    esac
else
    echo "--- Auto-detecting GPU hardware ---"
    # nvidia-smi is injected by the NVIDIA Container Toolkit
    NVIDIA_SMI=$(command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L 2>/dev/null || echo "")
    # /dev/kfd is the AMD ROCm compute interface — reliable in Docker with device passthrough
    [[ "$NVIDIA_SMI" == *"GPU"* ]] && HAS_NVIDIA=true
    [ -e /dev/kfd ] && HAS_AMD=true

    # Fallback: lspci if pciutils is installed
    if ! $HAS_NVIDIA && ! $HAS_AMD; then
        GPU_PCI=$(lspci 2>/dev/null | grep -iE 'vga|display|3d' || echo "")
        if [ -n "$GPU_PCI" ]; then
            [[ "$GPU_PCI" == *"NVIDIA"* ]] && HAS_NVIDIA=true
            [[ "$GPU_PCI" == *"AMD"* ]] || [[ "$GPU_PCI" == *"Radeon"* ]] && HAS_AMD=true
            # Any GPU detected but no specific runtime available — try Vulkan
            # Vulkan works on NVIDIA, AMD, Intel, and most discrete GPUs without CUDA/ROCm
            if ! $HAS_NVIDIA && ! $HAS_AMD && [ -n "$GPU_PCI" ]; then
                echo "  GPU detected via lspci but no CUDA/ROCm runtime — trying Vulkan"
                HAS_VULKAN=true
            fi
        fi
    fi

    # Always provision Vulkan if any GPU is visible — allows switching between
    # backends (e.g. ROCm + Vulkan on AMD) without reprovisioning
    $HAS_NVIDIA && HAS_VULKAN=true
    $HAS_AMD    && HAS_VULKAN=true

    echo "  NVIDIA (CUDA) detected: $HAS_NVIDIA"
    echo "  AMD (ROCm) detected:    $HAS_AMD"
    echo "  Vulkan:                 $HAS_VULKAN"
fi

CURRENT_SIG_PREFIX="VERSION=${LLAMA_VERSION:-latest}|NV=$HAS_NVIDIA|AMD=$HAS_AMD|VK=$HAS_VULKAN"

# ---------------------------------------------------------------------------
# 1a. Ensure container-level runtime packages are present on every start.
#     These live in the image/container filesystem, not the persisted runtime
#     volume, so a container recreate must re-check them even when the runtime
#     signature matches and provisioning is skipped.
# ---------------------------------------------------------------------------
RUNTIME_PACKAGES=()
$HAS_AMD    && RUNTIME_PACKAGES+=(libnuma1)
$HAS_VULKAN && RUNTIME_PACKAGES+=(libvulkan1 mesa-vulkan-drivers vulkan-tools)
ensure_apt_packages "${RUNTIME_PACKAGES[@]}"

mkdir -p "$RUNTIME_ROOT"

provision_backend() {
    local BE="$1"
    local PATTERN=""
    local SUFFIX="$BE"
    local CURRENT_SIG="${CURRENT_SIG_PREFIX}|BACKEND=${BE}"
    local RUNTIME_DIR="$RUNTIME_ROOT/$BE"
    local BIN_DIR="$RUNTIME_DIR/bin"
    local LIB_DIR="$RUNTIME_DIR/lib"
    local STATE_FILE="$RUNTIME_DIR/.hw_signature"

    mkdir -p "$BIN_DIR" "$LIB_DIR"

    case "$BE" in
        rocm)
            PATTERN="ubuntu-rocm.*x64\.(tar\.gz|zip)$"
            ;;
        cuda)
            PATTERN="ubuntu-x64\.(tar\.gz|zip)$"
            ;;
        vulkan)
            PATTERN="ubuntu-vulkan.*x64\.(tar\.gz|zip)$"
            ;;
        *)
            PATTERN="ubuntu-x64\.(tar\.gz|zip)$"
            SUFFIX="cpu"
            ;;
    esac

    if [ ! -f "$STATE_FILE" ] || [ "$(cat "$STATE_FILE")" != "$CURRENT_SIG" ]; then
        echo ">>> Provisioning $BE backend into $RUNTIME_DIR..."
        rm -rf "$BIN_DIR"/* "$LIB_DIR"/*

        DL_URL=$(echo "$RELEASE_DATA" | jq -r --arg p "$PATTERN" \
            '.assets[] | select(.name | test($p)) | .browser_download_url' | head -1)

        if [ -z "$DL_URL" ]; then
            echo "  WARNING: no asset found for pattern $PATTERN — skipping $BE"
            return
        fi

        echo "  Downloading from $DL_URL..."
        curl -L -o "/tmp/llama_${BE}.archive" "$DL_URL"
        mkdir -p "/tmp/extract_$BE"
        if echo "$DL_URL" | grep -q "\.zip$"; then
            unzip "/tmp/llama_${BE}.archive" -d "/tmp/extract_$BE"
        else
            tar -xzf "/tmp/llama_${BE}.archive" -C "/tmp/extract_$BE"
        fi
        find "/tmp/extract_$BE" -name "llama-server" -exec cp {} "$BIN_DIR/llama-server-$SUFFIX" \;
        find "/tmp/extract_$BE" -name "*.so*" -exec cp {} "$LIB_DIR/" \;
        rm -rf "/tmp/llama_${BE}.archive" "/tmp/extract_$BE"

        sync_backend_plugins "$BIN_DIR" "$LIB_DIR"
        echo "$CURRENT_SIG" > "$STATE_FILE"
        echo "  $BE provisioned: $BIN_DIR/llama-server-$SUFFIX"
    else
        echo ">>> Runtime up to date for $BE ($RUNTIME_DIR), skipping provisioning"
        sync_backend_plugins "$BIN_DIR" "$LIB_DIR"
    fi
}

# ---------------------------------------------------------------------------
# 2. Provisioning (skipped if signature matches cached state)
# ---------------------------------------------------------------------------
echo "--- Provisioning llama.cpp runtime ---"

# Build list of backend-specific runtime directories to manage.
BACKENDS=()
if [ -n "$LLAMA_BACKEND" ] && [ "$LLAMA_BACKEND" != "auto" ]; then
    BACKENDS+=("$LLAMA_BACKEND")
else
    $HAS_NVIDIA  && BACKENDS+=("cuda")
    $HAS_AMD     && BACKENDS+=("rocm")
    $HAS_VULKAN  && BACKENDS+=("vulkan")
    [ ${#BACKENDS[@]} -eq 0 ] && BACKENDS+=("cpu")
fi

echo "  Backend directories: ${BACKENDS[*]}"

VERSION_TAG=${LLAMA_VERSION:-latest}
API_URL="https://api.github.com/repos/ggml-org/llama.cpp/releases/latest"
[ "$VERSION_TAG" != "latest" ] && API_URL="https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/$VERSION_TAG"
RELEASE_DATA=$(curl -sL "$API_URL")

for BE in "${BACKENDS[@]}"; do
    provision_backend "$BE"
done

# ---------------------------------------------------------------------------
# 3. Launch
# ---------------------------------------------------------------------------
printf "%s\n" "/opt/rocm/lib" > /etc/ld.so.conf.d/llama-runtime.conf
ldconfig
export LD_LIBRARY_PATH="/opt/rocm/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export ROCBLAS_TENSILE_LIBPATH="${ROCBLAS_TENSILE_LIBPATH:-/opt/rocm/lib/rocblas/library}"

# When VK_ICD_FILENAMES is not already set, restrict Vulkan to the AMD RADV ICD
# if this is an AMD GPU system. Without this, all ICDs (intel, gfxstream, nouveau,
# lvp, etc.) are loaded and the AMD GPU may not enumerate correctly.
if [ -z "${VK_ICD_FILENAMES:-}" ] && $HAS_AMD; then
    _RADEON_ICD="/usr/share/vulkan/icd.d/radeon_icd.json"
    if [ -f "$_RADEON_ICD" ]; then
        export VK_ICD_FILENAMES="$_RADEON_ICD"
        echo "  AMD Vulkan: restricting to RADV ICD ($VK_ICD_FILENAMES)"
    fi
fi

if [ "$#" -eq 0 ]; then
    if ! command -v llama-swap >/dev/null 2>&1; then
        echo "ERROR: llama-swap binary not found in PATH"
        exit 1
    fi

    echo "--- Waiting for generated llama-swap config at $DEFAULT_SWAP_CONFIG ---"
    waited=0
    while [ ! -s "$DEFAULT_SWAP_CONFIG" ]; do
        if [ "$waited" -ge "$DEFAULT_SWAP_WAIT_SECONDS" ]; then
            echo "ERROR: timed out waiting for llama-swap config at $DEFAULT_SWAP_CONFIG"
            exit 1
        fi
        sleep 1
        waited=$((waited + 1))
    done

    echo "--- Starting llama-swap on $DEFAULT_SWAP_ADDR using $DEFAULT_SWAP_CONFIG ---"
    exec llama-swap -config "$DEFAULT_SWAP_CONFIG" -listen "$DEFAULT_SWAP_ADDR" -watch-config
fi

exec "$@"
