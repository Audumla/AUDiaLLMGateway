#!/bin/bash
set -e

RUNTIME_DIR="/app/runtime"
BIN_DIR="$RUNTIME_DIR/bin"
LIB_DIR="$RUNTIME_DIR/lib"
STATE_FILE="$RUNTIME_DIR/.hw_signature"

mkdir -p "$BIN_DIR" "$LIB_DIR"

# --- 1. Comprehensive Hardware Detection ---
GPU_PCI=$(lspci | grep -i 'vga\|display' || echo "")
NVIDIA_SMI=$(command -v nvidia-smi && nvidia-smi -L || echo "")

HAS_NVIDIA=false
HAS_AMD=false
[[ "$NVIDIA_SMI" == *"GPU"* ]] && HAS_NVIDIA=true
[[ "$GPU_PCI" == *"AMD"* ]] && HAS_AMD=true

CURRENT_SIG="VERSION=${LLAMA_VERSION:-latest}|NV=$HAS_NVIDIA|AMD=$HAS_AMD"

# --- 2. Multi-Backend Provisioning ---
if [ ! -f "$STATE_FILE" ] || [ "$(cat "$STATE_FILE")" != "$CURRENT_SIG" ]; then
    echo "--- Provisioning Multi-GPU Environment ---"
    rm -rf "$BIN_DIR"/* "$LIB_DIR"/*

    # Always install Vulkan & JQ for the system
    apt-get update && apt-get install -y --no-install-recommends libvulkan1 mesa-vulkan-drivers vulkan-tools jq curl wget

    BACKENDS=()
    [ "$HAS_NVIDIA" = "true" ] && BACKENDS+=("cuda")
    [ "$HAS_AMD" = "true" ] && BACKENDS+=("rocm")
    [ ${#BACKENDS[@]} -eq 0 ] && BACKENDS+=("cpu") # Fallback

    echo "Detected Backends to provision: ${BACKENDS[*]}"

    # Fetch Release metadata once
    VERSION_TAG=${LLAMA_VERSION:-latest}
    API_URL="https://api.github.com/repos/ggml-org/llama.cpp/releases/latest"
    [ "$VERSION_TAG" != "latest" ] && API_URL="https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/$VERSION_TAG"
    RELEASE_DATA=$(curl -sL "$API_URL")

    for BE in "${BACKENDS[@]}"; do
        echo ">>> Processing $BE backend..."
        
        case $BE in
            "rocm")
                PATTERN="ubuntu-rocm.*x64\.(tar\.gz|zip)$"
                # Install AMD System libs
                wget -qO - https://repo.radeon.com/rocm/rocm.gpg.key | gpg --dearmor -o /etc/apt/keyrings/rocm.gpg
                echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/rocm.gpg] https://repo.radeon.com/rocm/apt/6.0 jammy main" > /etc/apt/sources.list.d/rocm.list
                apt-get update && apt-get install -y --no-install-recommends rocm-hip-runtime
                SUFFIX="rocm"
                ;;
            "cuda")
                PATTERN="ubuntu-x64\.(tar\.gz|zip)$" # Standard binary uses host CUDA
                SUFFIX="cuda"
                ;;
            "vulkan")
                PATTERN="ubuntu-vulkan-x64\.(tar\.gz|zip)$"
                SUFFIX="vulkan"
                ;;
            *)
                PATTERN="ubuntu-x64\.(tar\.gz|zip)$"
                SUFFIX="cpu"
                ;;
        esac

        # Download and Extract
        DL_URL=$(echo "$RELEASE_DATA" | jq -r --arg PATTERN "$PATTERN" '.assets[] | select(.name | test($PATTERN)) | .browser_download_url')
        echo "Downloading $BE from $DL_URL..."
        curl -L -o "/tmp/llama_$BE.archive" "$DL_URL"
        mkdir -p "/tmp/extract_$BE"
        if echo "$DL_URL" | grep -q "\.zip$"; then unzip "/tmp/llama_$BE.archive" -d "/tmp/extract_$BE"; else tar -xzf "/tmp/llama_$BE.archive" -C "/tmp/extract_$BE"; fi
        
        # Save specialized binaries (e.g., llama-server-rocm)
        find "/tmp/extract_$BE" -name "llama-server" -exec cp {} "$BIN_DIR/llama-server-$SUFFIX" \;
        find "/tmp/extract_$BE" -name "*.so*" -exec cp {} "$LIB_DIR/" \;
        
        rm -rf "/tmp/llama_$BE.archive" "/tmp/extract_$BE"
    done

    # Create a universal symlink to the "primary" backend
    ln -sf "$BIN_DIR/llama-server-${BACKENDS[0]}" "$BIN_DIR/llama-server"

    echo "$CURRENT_SIG" > "$STATE_FILE"
    echo "--- Multi-GPU Provisioning Complete ---"
fi

# --- 3. Execution ---
echo "$LIB_DIR" > /etc/ld.so.conf.d/llama-runtime.conf
ldconfig
export PATH="$BIN_DIR:$PATH"

if [ "$#" -eq 0 ]; then
  echo "--- Standby Mode: Runtimes available in $BIN_DIR ---"
  exec sleep infinity
fi

exec "$@"
