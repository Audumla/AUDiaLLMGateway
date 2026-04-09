#!/bin/bash
# provision-runtime.sh
# Downloads and provisions llama.cpp binaries into a persistent runtime directory.
# Runs inside the backend container on first start (or when hardware changes).
# Results are cached under a backend-specific subdirectory to avoid
# re-downloading and to prevent cross-backend runtime drift.
set -e

RUNTIME_ROOT="${RUNTIME_ROOT:-/app/runtime-root}"
BUILD_ROOT="${BUILD_ROOT:-/app/runtime-build-root}"
DEFAULT_SWAP_CONFIG="${LLAMA_SWAP_CONFIG_PATH:-/app/config/llama-swap.generated.yaml}"
DEFAULT_SWAP_ADDR="${LLAMA_SWAP_LISTEN_ADDR:-0.0.0.0:41080}"
DEFAULT_SWAP_WAIT_SECONDS="${LLAMA_SWAP_CONFIG_WAIT_SECONDS:-120}"
BACKEND_RUNTIME_CATALOG_PATH="${BACKEND_RUNTIME_CATALOG_PATH:-/app/config/backend-runtime.catalog.json}"
BACKEND_RUNTIME_CATALOG_WAIT_SECONDS="${BACKEND_RUNTIME_CATALOG_WAIT_SECONDS:-45}"
EFFECTIVE_RUNTIME_CATALOG="/tmp/backend-runtime.catalog.json"

retry_cmd() {
    local _attempts="$1"
    local _sleep_seconds="$2"
    shift 2
    local _try=1
    while true; do
        if "$@"; then
            return 0
        fi
        if [ "$_try" -ge "$_attempts" ]; then
            return 1
        fi
        echo "  Retry $_try/$_attempts failed for: $*"
        sleep "$_sleep_seconds"
        _try=$((_try + 1))
    done
}

retry_git_clone() {
    local _url="$1"
    local _ref="$2"
    local _dest="$3"
    retry_cmd 5 3 git clone --depth 1 --branch "$_ref" "$_url" "$_dest"
}

retry_curl_download() {
    local _url="$1"
    local _output="$2"
    retry_cmd 5 2 curl -fLsS --connect-timeout 10 --retry 3 --retry-delay 2 --retry-all-errors -o "$_output" "$_url"
}

run_configured_command() {
    local _cmd="$1"
    local _env_json="${2:-{}}"
    if [ -z "$_cmd" ]; then
        return 0
    fi
    # Execute command via Python subprocess(shell=False) so unescaped shell metacharacters
    # in arguments (e.g. -DAMDGPU_TARGETS=gfx1030;gfx1100) are treated as plain arg text.
    python3 - "$_cmd" "$_env_json" <<'PY'
import os
import shlex
import subprocess
import sys
import json

cmd = sys.argv[1]
env_json = sys.argv[2] if len(sys.argv) > 2 else "{}"
# Support common build shorthand used in catalog commands.
cmd = cmd.replace("$(nproc)", str(os.cpu_count() or 1))
argv = shlex.split(cmd, posix=True)
if not argv:
    raise SystemExit(0)
env = os.environ.copy()
try:
    extra = json.loads(env_json) if env_json else {}
except Exception:
    extra = {}
if isinstance(extra, dict):
    for key, value in extra.items():
        env[str(key)] = str(value)
subprocess.run(argv, check=True, env=env)
PY
}

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
      "source_type": "github_release",
      "asset_tokens": ["ubuntu", "x64"],
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
      "source_type": "github_release",
      "asset_tokens": ["ubuntu", "cuda", "x64"],
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
      "source_type": "github_release",
      "asset_tokens": ["ubuntu", "rocm-7.2", "x64"],
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
      "source_type": "github_release",
      "asset_tokens": ["ubuntu", "vulkan", "x64"],
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
        if ! retry_curl_download "$_api_url" "$_target"; then
            return 1
        fi
    fi
    echo "$_target"
}

default_git_configure_command() {
    local _backend="$1"
    case "$_backend" in
        rocm) echo "cmake -S . -B build -DLLAMA_BUILD_SERVER=ON -DGGML_HIPBLAS=ON -DCMAKE_BUILD_TYPE=Release" ;;
        vulkan) echo "cmake -S . -B build -DLLAMA_BUILD_SERVER=ON -DGGML_VULKAN=ON -DCMAKE_BUILD_TYPE=Release" ;;
        cuda) echo "cmake -S . -B build -DLLAMA_BUILD_SERVER=ON -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release" ;;
        *) echo "cmake -S . -B build -DLLAMA_BUILD_SERVER=ON -DCMAKE_BUILD_TYPE=Release" ;;
    esac
}

default_git_build_command() {
    echo "cmake --build build --config Release -j$(nproc)"
}

default_binary_glob() {
    echo "build/bin/llama-server"
}

default_library_glob() {
    echo "build/bin/*.so*"
}

detect_archive_type() {
    local _url="$1"
    local _hint="$2"
    if [ -n "$_hint" ]; then
        echo "$_hint"
        return
    fi
    case "$_url" in
        *.tar.gz|*.tgz) echo "tar.gz" ;;
        *.tar.xz) echo "tar.xz" ;;
        *.zip) echo "zip" ;;
        *) echo "auto" ;;
    esac
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
mkdir -p "$BUILD_ROOT"

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
    local ASSET_TOKENS_JSON="$5"
    local OWNER="$6"
    local REPO="$7"
    local RUNTIME_SUBDIR="$8"
    local SOURCE_TYPE="$9"
    local DOWNLOAD_URL="${10}"
    local ARCHIVE_TYPE="${11}"
    local GIT_URL="${12}"
    local GIT_REF="${13}"
    local CONFIGURE_COMMAND="${14}"
    local BUILD_COMMAND="${15}"
    local BINARY_GLOB="${16}"
    local LIBRARY_GLOB="${17}"
    local APT_PACKAGES="${18}"
    local SOURCE_SUBDIR="${19}"
    local BUILD_ROOT_SUBDIR="${20}"
    local BUILD_ENV_JSON="${21}"
    local PRE_CONFIGURE_COMMAND="${22}"
    local SUFFIX="$BE"
    [ "$SUFFIX" = "cpu" ] && SUFFIX="cpu"
    local CURRENT_SIG="${CURRENT_SIG_PREFIX}|VARIANT=${NAME}|BACKEND=${BE}|VERSION=${VERSION}|SOURCE=${SOURCE_TYPE}|REPO=${OWNER}/${REPO}|PATTERN=${PATTERN}|TOKENS=${ASSET_TOKENS_JSON}|URL=${DOWNLOAD_URL}|GIT=${GIT_URL}@${GIT_REF}|SUBDIR=${RUNTIME_SUBDIR}|SRC_SUBDIR=${SOURCE_SUBDIR}|BUILD_SUBDIR=${BUILD_ROOT_SUBDIR}|BUILD_ENV=${BUILD_ENV_JSON}|PRE_CFG=${PRE_CONFIGURE_COMMAND}|CFG=${CONFIGURE_COMMAND}|BUILD=${BUILD_COMMAND}|BIN_GLOB=${BINARY_GLOB}|LIB_GLOB=${LIBRARY_GLOB}|APT=${APT_PACKAGES}"
    local RUNTIME_DIR="$RUNTIME_ROOT/$RUNTIME_SUBDIR"
    local BIN_DIR="$RUNTIME_DIR/bin"
    local LIB_DIR="$RUNTIME_DIR/lib"
    local STATE_FILE="$RUNTIME_DIR/.hw_signature"
    local RELEASE_META=""
    local DL_URL=""
    local _archive_type=""
    local EXPECTED_BIN="$BIN_DIR/llama-server-$SUFFIX"

    mkdir -p "$BIN_DIR" "$LIB_DIR"

    if [ ! -f "$STATE_FILE" ] || [ "$(cat "$STATE_FILE")" != "$CURRENT_SIG" ] || [ ! -x "$EXPECTED_BIN" ]; then
        echo ">>> Provisioning ${NAME} (${BE}@${VERSION}, source=${SOURCE_TYPE}) into $RUNTIME_DIR..."
        rm -rf "$BIN_DIR"/* "$LIB_DIR"/*

        [ -n "$APT_PACKAGES" ] && ensure_apt_packages $APT_PACKAGES

        case "$SOURCE_TYPE" in
            github_release|"")
                if ! RELEASE_META="$(ensure_release_metadata "$OWNER" "$REPO" "$VERSION")"; then
                    echo "  WARNING: failed to fetch release metadata for ${OWNER}/${REPO}@${VERSION} — skipping ${NAME}"
                    return
                fi
                if [ -n "$ASSET_TOKENS_JSON" ] && [ "$ASSET_TOKENS_JSON" != "[]" ]; then
                    DL_URL=$(jq -r --argjson tokens "$ASSET_TOKENS_JSON" '.assets[] | select((.name | ascii_downcase) as $n | reduce $tokens[] as $t (true; . and ($n | contains(($t | tostring | ascii_downcase))))) | .browser_download_url' "$RELEASE_META" 2>/dev/null | head -1 || true)
                else
                    DL_URL=$(jq -r --arg p "$PATTERN" '.assets[] | select(.name | test($p)) | .browser_download_url' "$RELEASE_META" 2>/dev/null | head -1 || true)
                fi
                if [ -z "$DL_URL" ]; then
                    if [ -n "$ASSET_TOKENS_JSON" ] && [ "$ASSET_TOKENS_JSON" != "[]" ]; then
                        echo "  WARNING: no asset found for tokens $ASSET_TOKENS_JSON in ${OWNER}/${REPO}@${VERSION} — skipping ${NAME}"
                    else
                        echo "  WARNING: no asset found for pattern $PATTERN in ${OWNER}/${REPO}@${VERSION} — skipping ${NAME}"
                    fi
                    return
                fi
                ;;
            direct_url)
                DL_URL="$DOWNLOAD_URL"
                if [ -z "$DL_URL" ]; then
                    echo "  WARNING: direct_url variant '${NAME}' missing download_url — skipping"
                    return
                fi
                ;;
            git)
                if [ -z "$GIT_URL" ]; then
                    echo "  WARNING: git variant '${NAME}' missing git_url — skipping"
                    return
                fi
                [ -z "$GIT_REF" ] && GIT_REF="master"
                [ -z "$CONFIGURE_COMMAND" ] && CONFIGURE_COMMAND="$(default_git_configure_command "$BE")"
                [ -z "$BUILD_COMMAND" ] && BUILD_COMMAND="$(default_git_build_command)"
                [ -z "$BINARY_GLOB" ] && BINARY_GLOB="$(default_binary_glob)"
                [ -z "$LIBRARY_GLOB" ] && LIBRARY_GLOB="$(default_library_glob)"
                ensure_apt_packages git cmake build-essential pkg-config libcurl4-openssl-dev
                [ -z "$SOURCE_SUBDIR" ] && SOURCE_SUBDIR="."
                [ -z "$BUILD_ROOT_SUBDIR" ] && BUILD_ROOT_SUBDIR="$NAME"

                local _git_build="${BUILD_ROOT}/${BUILD_ROOT_SUBDIR}"
                rm -rf "$_git_build"
                mkdir -p "$_git_build"
                echo "  Cloning $GIT_URL @ $GIT_REF"
                if ! retry_git_clone "$GIT_URL" "$GIT_REF" "$_git_build/src"; then
                    echo "  WARNING: git clone failed for ${NAME} after retries (URL=$GIT_URL REF=$GIT_REF) — skipping"
                    rm -rf "$_git_build"
                    return
                fi
                local _workdir="$_git_build/src/$SOURCE_SUBDIR"
                if [ ! -d "$_workdir" ]; then
                    echo "  WARNING: source_subdir '$SOURCE_SUBDIR' not found for ${NAME} — skipping"
                    rm -rf "$_git_build"
                    return
                fi
                if ! (
                    cd "$_workdir"
                    run_configured_command "$PRE_CONFIGURE_COMMAND" "$BUILD_ENV_JSON"
                    run_configured_command "$CONFIGURE_COMMAND" "$BUILD_ENV_JSON"
                    run_configured_command "$BUILD_COMMAND" "$BUILD_ENV_JSON"
                ); then
                    echo "  WARNING: git build failed for ${NAME}; skipping this variant"
                    rm -rf "$_git_build"
                    return
                fi
                local _binary_path=""
                _binary_path=$(compgen -G "$_workdir/$BINARY_GLOB" | head -1 || true)
                if [ -z "$_binary_path" ]; then
                    echo "  WARNING: git build did not produce binary matching '$BINARY_GLOB' — skipping ${NAME}"
                    rm -rf "$_git_build"
                    return
                fi
                cp "$_binary_path" "$BIN_DIR/llama-server-$SUFFIX"
                chmod +x "$BIN_DIR/llama-server-$SUFFIX"
                if compgen -G "$_workdir/$LIBRARY_GLOB" >/dev/null 2>&1; then
                    cp $_workdir/$LIBRARY_GLOB "$LIB_DIR/" 2>/dev/null || true
                fi
                rm -rf "$_git_build"
                sync_backend_plugins "$BIN_DIR" "$LIB_DIR"
                echo "$CURRENT_SIG" > "$STATE_FILE"
                echo "  ${NAME} provisioned: $BIN_DIR/llama-server-$SUFFIX"
                return
                ;;
            *)
                echo "  WARNING: unknown source_type '$SOURCE_TYPE' for variant '${NAME}' — skipping"
                return
                ;;
        esac

        if [ -z "$DL_URL" ]; then
            echo "  WARNING: no download URL resolved for ${NAME}; skipping"
            return
        fi

        echo "  Downloading from $DL_URL..."
        local _archive="/tmp/llama_${NAME}.archive"
        local _extract="/tmp/extract_${NAME}"
        if ! retry_curl_download "$DL_URL" "$_archive"; then
            echo "  WARNING: failed to download runtime asset for ${NAME} after retries — skipping"
            rm -rf "$_archive" "$_extract"
            return
        fi
        mkdir -p "$_extract"
        _archive_type="$(detect_archive_type "$DL_URL" "$ARCHIVE_TYPE")"
        case "$_archive_type" in
            zip)
                unzip "$_archive" -d "$_extract"
                ;;
            tar.gz|tgz|auto)
                tar -xzf "$_archive" -C "$_extract"
                ;;
            tar.xz)
                tar -xJf "$_archive" -C "$_extract"
                ;;
            none|raw|binary)
                cp "$_archive" "$BIN_DIR/llama-server-$SUFFIX"
                chmod +x "$BIN_DIR/llama-server-$SUFFIX"
                rm -rf "$_archive" "$_extract"
                sync_backend_plugins "$BIN_DIR" "$LIB_DIR"
                echo "$CURRENT_SIG" > "$STATE_FILE"
                echo "  ${NAME} provisioned: $BIN_DIR/llama-server-$SUFFIX"
                return
                ;;
            *)
                echo "  WARNING: unsupported archive_type '$_archive_type' for ${NAME} — skipping"
                rm -rf "$_archive" "$_extract"
                return
                ;;
        esac
        if [ -n "$BINARY_GLOB" ]; then
            local _binary_path=""
            _binary_path=$(compgen -G "$_extract/$BINARY_GLOB" | head -1 || true)
            if [ -n "$_binary_path" ]; then
                cp "$_binary_path" "$BIN_DIR/llama-server-$SUFFIX"
                chmod +x "$BIN_DIR/llama-server-$SUFFIX"
            fi
        else
            find "$_extract" -name "llama-server" -exec cp {} "$BIN_DIR/llama-server-$SUFFIX" \;
            if [ -f "$BIN_DIR/llama-server-$SUFFIX" ]; then
                chmod +x "$BIN_DIR/llama-server-$SUFFIX"
            fi
        fi
        if [ -n "$LIBRARY_GLOB" ]; then
            if compgen -G "$_extract/$LIBRARY_GLOB" >/dev/null 2>&1; then
                cp $_extract/$LIBRARY_GLOB "$LIB_DIR/" 2>/dev/null || true
            fi
        else
            find "$_extract" -name "*.so*" -exec cp {} "$LIB_DIR/" \;
        fi
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
jq -r '.variants[]? | "    - " + (.name // "<unnamed>") + " [" + (.backend // "?") + "@" + (.version // "latest") + ", source=" + (.source_type // "github_release") + "]"' "$EFFECTIVE_RUNTIME_CATALOG" || true

mapfile -t VARIANT_ROWS < <(jq -c '.variants[]? | select((.enabled // true) == true)' "$EFFECTIVE_RUNTIME_CATALOG")

PROVISIONED_COUNT=0
for ROW in "${VARIANT_ROWS[@]}"; do
    NAME="$(echo "$ROW" | jq -r '.name // ""')"
    BACKEND="$(echo "$ROW" | jq -r '.backend // ""' | tr '[:upper:]' '[:lower:]')"
    VERSION="$(echo "$ROW" | jq -r '.version // "latest"')"
    PATTERN="$(echo "$ROW" | jq -r '.asset_pattern // ""')"
    ASSET_TOKENS_JSON="$(echo "$ROW" | jq -c '.asset_tokens // []')"
    OWNER="$(echo "$ROW" | jq -r '.repo_owner // "ggml-org"')"
    REPO="$(echo "$ROW" | jq -r '.repo_name // "llama.cpp"')"
    RUNTIME_SUBDIR="$(echo "$ROW" | jq -r '.runtime_subdir // ""')"
    ALWAYS="$(echo "$ROW" | jq -r '.always // false')"
    SOURCE_TYPE="$(echo "$ROW" | jq -r '.source_type // "github_release"' | tr '[:upper:]' '[:lower:]')"
    DOWNLOAD_URL="$(echo "$ROW" | jq -r '.download_url // ""')"
    ARCHIVE_TYPE="$(echo "$ROW" | jq -r '.archive_type // ""')"
    GIT_URL="$(echo "$ROW" | jq -r '.git_url // ""')"
    GIT_REF="$(echo "$ROW" | jq -r '.git_ref // ""')"
    CONFIGURE_COMMAND="$(echo "$ROW" | jq -r '.configure_command // ""')"
    BUILD_COMMAND="$(echo "$ROW" | jq -r '.build_command // ""')"
    BINARY_GLOB="$(echo "$ROW" | jq -r '.binary_glob // ""')"
    LIBRARY_GLOB="$(echo "$ROW" | jq -r '.library_glob // ""')"
    APT_PACKAGES="$(echo "$ROW" | jq -r '.apt_packages // [] | map(tostring) | join(" ")')"
    SOURCE_SUBDIR="$(echo "$ROW" | jq -r '.source_subdir // "."')"
    BUILD_ROOT_SUBDIR="$(echo "$ROW" | jq -r '.build_root_subdir // ""')"
    BUILD_ENV_JSON="$(echo "$ROW" | jq -c '.build_env // {}')"
    PRE_CONFIGURE_COMMAND="$(echo "$ROW" | jq -r '.pre_configure_command // ""')"

    [ -z "$BACKEND" ] && continue
    [ -z "$NAME" ] && NAME="$BACKEND"
    [ -z "$RUNTIME_SUBDIR" ] && RUNTIME_SUBDIR="$BACKEND"
    if [ "$ASSET_TOKENS_JSON" = "[]" ] && [ -z "$PATTERN" ]; then
        case "$BACKEND" in
            rocm) ASSET_TOKENS_JSON='["ubuntu","rocm-7.2","x64"]' ;;
            vulkan) ASSET_TOKENS_JSON='["ubuntu","vulkan","x64"]' ;;
            cuda) ASSET_TOKENS_JSON='["ubuntu","cuda","x64"]' ;;
            *) ASSET_TOKENS_JSON='["ubuntu","x64"]' ;;
        esac
    fi

    if should_provision_variant "$BACKEND" "$ALWAYS"; then
        provision_variant \
            "$NAME" "$BACKEND" "$VERSION" "$PATTERN" "$ASSET_TOKENS_JSON" "$OWNER" "$REPO" "$RUNTIME_SUBDIR" \
            "$SOURCE_TYPE" "$DOWNLOAD_URL" "$ARCHIVE_TYPE" "$GIT_URL" "$GIT_REF" \
            "$CONFIGURE_COMMAND" "$BUILD_COMMAND" "$BINARY_GLOB" "$LIBRARY_GLOB" "$APT_PACKAGES" \
            "$SOURCE_SUBDIR" "$BUILD_ROOT_SUBDIR" "$BUILD_ENV_JSON" "$PRE_CONFIGURE_COMMAND"
        PROVISIONED_COUNT=$((PROVISIONED_COUNT + 1))
    fi
done

if [ "$PROVISIONED_COUNT" -eq 0 ]; then
    echo "  No runtime variants selected from catalog; provisioning cpu fallback"
    provision_variant "cpu" "cpu" "${LLAMA_VERSION:-latest}" "" '["ubuntu","x64"]' "ggml-org" "llama.cpp" "cpu" "github_release" "" "" "" "" "" "" "" "" "" "" "" ""
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
