#!/bin/bash
# provision-runtime.sh
# Downloads and provisions llama.cpp binaries into a persistent runtime volume.
# Runs inside the backend container on first start (or when hardware changes).
# Results are cached in the backend-runtime volume to avoid re-downloading.
set -e

RUNTIME_DIR="/app/runtime"
BIN_DIR="$RUNTIME_DIR/bin"
LIB_DIR="$RUNTIME_DIR/lib"
STATE_FILE="$RUNTIME_DIR/.hw_signature"

mkdir -p "$BIN_DIR" "$LIB_DIR"

# ---------------------------------------------------------------------------
# 1. Hardware Detection
#    LLAMA_BACKEND env var overrides auto-detection (set by compose profiles).
#    Values: auto | cuda | rocm | vulkan | cpu
# ---------------------------------------------------------------------------
if [ -n "$LLAMA_BACKEND" ] && [ "$LLAMA_BACKEND" != "auto" ]; then
    echo "--- Backend forced by LLAMA_BACKEND=$LLAMA_BACKEND ---"
    HAS_NVIDIA=false
    HAS_AMD=false
    case "$LLAMA_BACKEND" in
        cuda)   HAS_NVIDIA=true ;;
        rocm)   HAS_AMD=true ;;
    esac
else
    echo "--- Auto-detecting GPU hardware ---"
    # nvidia-smi is injected by the NVIDIA Container Toolkit
    NVIDIA_SMI=$(command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L 2>/dev/null || echo "")
    # /dev/kfd is the AMD ROCm compute interface — reliable in Docker with device passthrough
    HAS_NVIDIA=false
    HAS_AMD=false
    [[ "$NVIDIA_SMI" == *"GPU"* ]] && HAS_NVIDIA=true
    [ -e /dev/kfd ] && HAS_AMD=true
    # Fallback: try lspci if pciutils is installed
    if ! $HAS_AMD && ! $HAS_NVIDIA; then
        GPU_PCI=$(lspci 2>/dev/null | grep -i 'vga\|display' || echo "")
        [[ "$GPU_PCI" == *"NVIDIA"* ]] && HAS_NVIDIA=true
        [[ "$GPU_PCI" == *"AMD"* ]] && HAS_AMD=true
    fi
    echo "  NVIDIA detected: $HAS_NVIDIA"
    echo "  AMD detected:    $HAS_AMD"
fi

CURRENT_SIG="VERSION=${LLAMA_VERSION:-latest}|NV=$HAS_NVIDIA|AMD=$HAS_AMD|BACKEND=${LLAMA_BACKEND:-auto}"

# ---------------------------------------------------------------------------
# 2. Provisioning (skipped if signature matches cached state)
# ---------------------------------------------------------------------------
if [ ! -f "$STATE_FILE" ] || [ "$(cat "$STATE_FILE")" != "$CURRENT_SIG" ]; then
    echo "--- Provisioning llama.cpp runtime ---"
    rm -rf "$BIN_DIR"/* "$LIB_DIR"/*

    # Always install Vulkan libraries (required for Vulkan/AMD Vulkan path)
    apt-get update -qq && apt-get install -y --no-install-recommends \
        libvulkan1 mesa-vulkan-drivers \
        && rm -rf /var/lib/apt/lists/*

    BACKENDS=()
    $HAS_NVIDIA && BACKENDS+=("cuda")
    $HAS_AMD    && BACKENDS+=("rocm")
    [ ${#BACKENDS[@]} -eq 0 ] && BACKENDS+=("cpu")

    echo "  Backends to provision: ${BACKENDS[*]}"

    # Fetch release metadata once
    VERSION_TAG=${LLAMA_VERSION:-latest}
    API_URL="https://api.github.com/repos/ggml-org/llama.cpp/releases/latest"
    [ "$VERSION_TAG" != "latest" ] && API_URL="https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/$VERSION_TAG"
    RELEASE_DATA=$(curl -sL "$API_URL")

    for BE in "${BACKENDS[@]}"; do
        echo ">>> Provisioning $BE backend..."
        case $BE in
            rocm)
                PATTERN="ubuntu-rocm.*x64\.(tar\.gz|zip)$"
                # Install ROCm HIP runtime (lazy — only when AMD hardware is detected)
                wget -qO - https://repo.radeon.com/rocm/rocm.gpg.key | gpg --dearmor -o /etc/apt/keyrings/rocm.gpg
                echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/rocm.gpg] https://repo.radeon.com/rocm/apt/6.0 jammy main" \
                    > /etc/apt/sources.list.d/rocm.list
                apt-get update -qq && apt-get install -y --no-install-recommends rocm-hip-runtime \
                    && rm -rf /var/lib/apt/lists/*
                SUFFIX="rocm"
                ;;
            cuda)
                PATTERN="ubuntu-x64\.(tar\.gz|zip)$"
                SUFFIX="cuda"
                ;;
            *)
                PATTERN="ubuntu-x64\.(tar\.gz|zip)$"
                SUFFIX="cpu"
                ;;
        esac

        DL_URL=$(echo "$RELEASE_DATA" | jq -r --arg p "$PATTERN" \
            '.assets[] | select(.name | test($p)) | .browser_download_url' | head -1)

        if [ -z "$DL_URL" ]; then
            echo "  WARNING: no asset found for pattern $PATTERN — skipping $BE"
            continue
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
        echo "  $BE provisioned: $BIN_DIR/llama-server-$SUFFIX"
    done

    # Symlink the primary backend as the default llama-server
    PRIMARY="${BACKENDS[0]}"
    ln -sf "$BIN_DIR/llama-server-$PRIMARY" "$BIN_DIR/llama-server"
    echo "  Default: llama-server -> llama-server-$PRIMARY"

    echo "$CURRENT_SIG" > "$STATE_FILE"
    echo "--- Provisioning complete ---"
else
    echo "--- Runtime up to date (signature matches), skipping provisioning ---"
fi

# ---------------------------------------------------------------------------
# 3. Launch
# ---------------------------------------------------------------------------
echo "$LIB_DIR" > /etc/ld.so.conf.d/llama-runtime.conf
ldconfig
export PATH="$BIN_DIR:$PATH"

if [ "$#" -eq 0 ]; then
    echo "--- Standby mode: binaries available at $BIN_DIR ---"
    exec sleep infinity
fi

exec "$@"
