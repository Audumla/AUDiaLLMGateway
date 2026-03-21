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
BACKEND_RUNTIME_CATALOG_PATH="${BACKEND_RUNTIME_CATALOG_PATH:-/app/config/backend-runtime.catalog.json}"
BACKEND_RUNTIME_CATALOG_WAIT_SECONDS="${BACKEND_RUNTIME_CATALOG_WAIT_SECONDS:-45}"
EFFECTIVE_RUNTIME_CATALOG="/tmp/backend-runtime.catalog.json"

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

default_runtime_catalog_json() {
    local _ver="${LLAMA_VERSION:-latest}"
    cat <<EOF
{
  "schema_version": 1,
  "runtime_root": "/app/runtime-root",
  "variants": [
    {
      "name": "cpu",
      "backend": "cpu",
      "macro": "llama-server-cpu",
      "version": "${_ver}",
      "asset_pattern": "ubuntu-x64\\\\.(tar\\\\.gz|zip)$",
      "repo_owner": "ggml-org",
      "repo_name": "llama.cpp",
      "runtime_subdir": "cpu",
      "enabled": true,
      "always": false
    },
    {
      "name": "cuda",
      "backend": "cuda",
      "macro": "llama-server-cuda",
      "version": "${_ver}",
      "asset_pattern": "ubuntu-x64\\\\.(tar\\\\.gz|zip)$",
      "repo_owner": "ggml-org",
      "repo_name": "llama.cpp",
      "runtime_subdir": "cuda",
      "enabled": true,
      "always": false
    },
    {
      "name": "rocm",
      "backend": "rocm",
      "macro": "llama-server-rocm",
      "version": "${_ver}",
      "asset_pattern": "ubuntu-rocm.*x64\\\\.(tar\\\\.gz|zip)$",
      "repo_owner": "ggml-org",
      "repo_name": "llama.cpp",
      "runtime_subdir": "rocm",
      "enabled": true,
      "always": false
    },
    {
      "name": "vulkan",
      "backend": "vulkan",
      "macro": "llama-server-vulkan",
      "version": "${_ver}",
      "asset_pattern": "ubuntu-vulkan.*x64\\\\.(tar\\\\.gz|zip)$",
      "repo_owner": "ggml-org",
      "repo_name": "llama.cpp",
      "runtime_subdir": "vulkan",
      "enabled": true,
      "always": false
    }
  ]
}
EOF
}

load_runtime_catalog() {
    local _waited=0
    if [ -n "$BACKEND_RUNTIME_CATALOG_PATH" ]; then
        while [ ! -s "$BACKEND_RUNTIME_CATALOG_PATH" ] && [ "$_waited" -lt "$BACKEND_RUNTIME_CATALOG_WAIT_SECONDS" ]; do
            sleep 1
            _waited=$((_waited + 1))
        done
        if [ -s "$BACKEND_RUNTIME_CATALOG_PATH" ] && jq -e . "$BACKEND_RUNTIME_CATALOG_PATH" >/dev/null 2>&1; then
            cp "$BACKEND_RUNTIME_CATALOG_PATH" "$EFFECTIVE_RUNTIME_CATALOG"
            echo "  Using runtime catalog: $BACKEND_RUNTIME_CATALOG_PATH"
            return
        fi
    fi
    echo "  Runtime catalog unavailable or invalid; using built-in defaults"
    default_runtime_catalog_json > "$EFFECTIVE_RUNTIME_CATALOG"
}

release_metadata_path() {
    local _owner="$1"
    local _repo="$2"
    local _version="$3"
    local _safe
    _safe="$(echo "${_owner}_${_repo}_${_version}" | tr '/: ' '___')"
    echo "/tmp/llama-release-${_safe}.json"
}

ensure_release_metadata() {
    local _owner="$1"
    local _repo="$2"
    local _version="$3"
    local _target
    _target="$(release_metadata_path "$_owner" "$_repo" "$_version")"
    if [ ! -s "$_target" ]; then
        local _api_url="https://api.github.com/repos/${_owner}/${_repo}/releases/latest"
        [ "$_version" != "latest" ] && _api_url="https://api.github.com/repos/${_owner}/${_repo}/releases/tags/${_version}"
        curl -fsSL "$_api_url" -o "$_target"
    fi
    echo "$_target"
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

is_backend_available() {
    local _backend="$1"
    case "$_backend" in
        cuda) $HAS_NVIDIA ;;
        rocm) $HAS_AMD ;;
        vulkan) $HAS_VULKAN ;;
        cpu) true ;;
        *) false ;;
    esac
}

should_provision_variant() {
    local _backend="$1"
    local _always="$2"
    if [ -n "$LLAMA_BACKEND" ] && [ "$LLAMA_BACKEND" != "auto" ]; then
        [ "$_backend" = "$LLAMA_BACKEND" ]
        return
    fi
    if ! is_backend_available "$_backend"; then
        return 1
    fi
    if [ "$_backend" = "cpu" ] && [ "$_always" != "true" ] && { $HAS_NVIDIA || $HAS_AMD || $HAS_VULKAN; }; then
        return 1
    fi
    return 0
}

provision_variant() {
    local NAME="$1"
    local BE="$2"
    local VERSION="$3"
    local PATTERN="$4"
    local OWNER="$5"
    local REPO="$6"
    local RUNTIME_SUBDIR="$7"
    local SUFFIX="$BE"
    [ "$SUFFIX" = "cpu" ] && SUFFIX="cpu"
    local CURRENT_SIG="${CURRENT_SIG_PREFIX}|VARIANT=${NAME}|BACKEND=${BE}|VERSION=${VERSION}|REPO=${OWNER}/${REPO}|PATTERN=${PATTERN}|SUBDIR=${RUNTIME_SUBDIR}"
    local RUNTIME_DIR="$RUNTIME_ROOT/$RUNTIME_SUBDIR"
    local BIN_DIR="$RUNTIME_DIR/bin"
    local LIB_DIR="$RUNTIME_DIR/lib"
    local STATE_FILE="$RUNTIME_DIR/.hw_signature"
    local RELEASE_META=""
    local DL_URL=""

    mkdir -p "$BIN_DIR" "$LIB_DIR"

    if [ ! -f "$STATE_FILE" ] || [ "$(cat "$STATE_FILE")" != "$CURRENT_SIG" ]; then
        echo ">>> Provisioning ${NAME} (${BE}@${VERSION}) into $RUNTIME_DIR..."
        rm -rf "$BIN_DIR"/* "$LIB_DIR"/*

        if ! RELEASE_META="$(ensure_release_metadata "$OWNER" "$REPO" "$VERSION")"; then
            echo "  WARNING: failed to fetch release metadata for ${OWNER}/${REPO}@${VERSION} — skipping ${NAME}"
            return
        fi
        DL_URL=$(jq -r --arg p "$PATTERN" '.assets[] | select(.name | test($p)) | .browser_download_url' "$RELEASE_META" 2>/dev/null | head -1 || true)

        if [ -z "$DL_URL" ]; then
            echo "  WARNING: no asset found for pattern $PATTERN in ${OWNER}/${REPO}@${VERSION} — skipping ${NAME}"
            return
        fi

        echo "  Downloading from $DL_URL..."
        local _archive="/tmp/llama_${NAME}.archive"
        local _extract="/tmp/extract_${NAME}"
        curl -L -o "$_archive" "$DL_URL"
        mkdir -p "$_extract"
        if echo "$DL_URL" | grep -q "\.zip$"; then
            unzip "$_archive" -d "$_extract"
        else
            tar -xzf "$_archive" -C "$_extract"
        fi
        find "$_extract" -name "llama-server" -exec cp {} "$BIN_DIR/llama-server-$SUFFIX" \;
        find "$_extract" -name "*.so*" -exec cp {} "$LIB_DIR/" \;
        rm -rf "$_archive" "$_extract"

        sync_backend_plugins "$BIN_DIR" "$LIB_DIR"
        echo "$CURRENT_SIG" > "$STATE_FILE"
        echo "  ${NAME} provisioned: $BIN_DIR/llama-server-$SUFFIX"
    else
        echo ">>> Runtime up to date for ${NAME} ($RUNTIME_DIR), skipping provisioning"
        sync_backend_plugins "$BIN_DIR" "$LIB_DIR"
    fi
}

# ---------------------------------------------------------------------------
# 2. Provisioning (skipped if signature matches cached state)
# ---------------------------------------------------------------------------
echo "--- Provisioning llama.cpp runtime ---"
load_runtime_catalog
echo "  Runtime catalog variants:"
jq -r '.variants[]? | "    - " + (.name // "<unnamed>") + " [" + (.backend // "?") + "@" + (.version // "latest") + "]"' "$EFFECTIVE_RUNTIME_CATALOG" || true

mapfile -t VARIANT_ROWS < <(jq -c '.variants[]? | select((.enabled // true) == true)' "$EFFECTIVE_RUNTIME_CATALOG")

PROVISIONED_COUNT=0
for ROW in "${VARIANT_ROWS[@]}"; do
    NAME="$(echo "$ROW" | jq -r '.name // ""')"
    BACKEND="$(echo "$ROW" | jq -r '.backend // ""' | tr '[:upper:]' '[:lower:]')"
    VERSION="$(echo "$ROW" | jq -r '.version // "latest"')"
    PATTERN="$(echo "$ROW" | jq -r '.asset_pattern // ""')"
    OWNER="$(echo "$ROW" | jq -r '.repo_owner // "ggml-org"')"
    REPO="$(echo "$ROW" | jq -r '.repo_name // "llama.cpp"')"
    RUNTIME_SUBDIR="$(echo "$ROW" | jq -r '.runtime_subdir // ""')"
    ALWAYS="$(echo "$ROW" | jq -r '.always // false')"

    [ -z "$BACKEND" ] && continue
    [ -z "$NAME" ] && NAME="$BACKEND"
    [ -z "$RUNTIME_SUBDIR" ] && RUNTIME_SUBDIR="$BACKEND"
    if [ -z "$PATTERN" ]; then
        case "$BACKEND" in
            rocm) PATTERN="ubuntu-rocm.*x64\\.(tar\\.gz|zip)$" ;;
            vulkan) PATTERN="ubuntu-vulkan.*x64\\.(tar\\.gz|zip)$" ;;
            cuda) PATTERN="ubuntu-x64\\.(tar\\.gz|zip)$" ;;
            *) PATTERN="ubuntu-x64\\.(tar\\.gz|zip)$" ;;
        esac
    fi

    if should_provision_variant "$BACKEND" "$ALWAYS"; then
        provision_variant "$NAME" "$BACKEND" "$VERSION" "$PATTERN" "$OWNER" "$REPO" "$RUNTIME_SUBDIR"
        PROVISIONED_COUNT=$((PROVISIONED_COUNT + 1))
    fi
done

if [ "$PROVISIONED_COUNT" -eq 0 ]; then
    echo "  No runtime variants selected from catalog; provisioning cpu fallback"
    provision_variant "cpu" "cpu" "${LLAMA_VERSION:-latest}" "ubuntu-x64\\.(tar\\.gz|zip)$" "ggml-org" "llama.cpp" "cpu"
fi

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
