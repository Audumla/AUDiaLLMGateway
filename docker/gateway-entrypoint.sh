#!/bin/sh
set -e

CONFIG=/app/config
LITELLM_CONFIG_PATH="$CONFIG/generated/litellm/litellm.config.yaml"
LITELLM_CONFIG_WAIT_SECONDS="${LITELLM_CONFIG_WAIT_SECONDS:-30}"
UVICORN_LOG_CONFIG_PATH="/app/config/project/uvicorn.log-config.json"
DATABASE_WAIT_SECONDS="${DATABASE_WAIT_SECONDS:-120}"
DATABASE_WAIT_INTERVAL_SECONDS="${DATABASE_WAIT_INTERVAL_SECONDS:-2}"

warn_if_generated_configs_stale() {
    source_files="
$CONFIG/local/stack.override.yaml
$CONFIG/local/stack.private.yaml
$CONFIG/local/models.override.yaml
$CONFIG/local/models.private.yaml
$CONFIG/local/backend-runtime.override.yaml
$CONFIG/local/backend-runtime.private.yaml
$CONFIG/local/backend-support.override.yaml
$CONFIG/local/backend-support.private.yaml
$CONFIG/local/llama-swap.override.yaml
$CONFIG/local/llama-swap.private.yaml
$CONFIG/local/mcp.override.yaml
$CONFIG/local/mcp.private.yaml
$CONFIG/local/env
$CONFIG/local/env.private
"
    generated_files="
$CONFIG/generated/llama-swap/llama-swap.generated.yaml
$CONFIG/generated/litellm/litellm.config.yaml
$CONFIG/generated/llama-swap/backend-runtime.catalog.json
"

    newest_source=""
    for path in $source_files; do
        [ -f "$path" ] || continue
        if [ -z "$newest_source" ] || [ "$path" -nt "$newest_source" ]; then
            newest_source="$path"
        fi
    done

    newest_generated=""
    for path in $generated_files; do
        [ -f "$path" ] || continue
        if [ -z "$newest_generated" ] || [ "$path" -nt "$newest_generated" ]; then
            newest_generated="$path"
        fi
    done

    if [ -n "$newest_source" ] && { [ -z "$newest_generated" ] || [ "$newest_source" -nt "$newest_generated" ]; }; then
        echo ">>> WARNING: config/local changes are newer than generated gateway configs."
        echo ">>> Run 'python -m src.launcher.process_manager --root . generate-configs' or start the llm-config-watcher service."
        echo ">>> A plain gateway restart will keep using stale generated files until configs are regenerated."
    fi
}

read_env_override() {
    var_name="$1"
    for env_file in "$CONFIG/local/env.private" "$CONFIG/local/env"; do
        [ -f "$env_file" ] || continue
        value="$(grep "^${var_name}=" "$env_file" | tail -n 1 | cut -d= -f2-)"
        if [ -n "$value" ]; then
            printf '%s' "$value"
            return 0
        fi
    done
    return 1
}

# --- Seed config/local/ on first run ---
mkdir -p "$CONFIG/local"

if [ ! -f "$CONFIG/local/env" ]; then
    echo ">>> First run: seeding config/local/env"
    cat > "$CONFIG/local/env" <<'EOF'
# AUDia LLM Gateway — environment overrides.
# Changes take effect on next container restart.
#
# REQUIRED: Set a strong key before exposing the gateway on a network.
LITELLM_MASTER_KEY=sk-local-dev
EOF
fi

if [ -z "${LITELLM_MASTER_KEY:-}" ]; then
    # Reuse the seeded first-run key unless Compose or the host already provided one.
    # env.private wins over env when both exist.
    LITELLM_MASTER_KEY="$(read_env_override LITELLM_MASTER_KEY || true)"
    if [ -n "$LITELLM_MASTER_KEY" ]; then
        export LITELLM_MASTER_KEY
    fi
fi

if [ ! -f "$CONFIG/local/stack.override.yaml" ]; then
    echo ">>> First run: seeding config/local/stack.override.yaml"
    cat > "$CONFIG/local/stack.override.yaml" <<'EOF'
# AUDia LLM Gateway — local stack overrides.
# Merged on top of config/project/stack.base.yaml.
# Regenerate configs after editing. If llm-config-watcher is not running, a
# plain gateway restart is not enough on its own.
# Keep tracked values generic; machine-specific settings can live in
# config/local/stack.private.yaml.
#
# --- Common customisations ---
#
# Change published ports:
# network:
#   services:
#     litellm:
#       port: 4000
#     llama_swap:
#       port: 41080
#
# Enable nginx reverse proxy:
# reverse_proxy:
#   nginx:
#     enabled: true
EOF
fi

if [ ! -f "$CONFIG/local/models.override.yaml" ]; then
    echo ">>> First run: seeding config/local/models.override.yaml"
    cat > "$CONFIG/local/models.override.yaml" <<'EOF'
# AUDia LLM Gateway — local model overrides.
# Add entries here to expose local GGUF models through the gateway.
# Model files must be placed in the models/ directory (or MODEL_ROOT).
# Keep tracked values generic; host-only routing belongs in
# config/local/models.private.yaml.
# After editing, regenerate configs. If llm-config-watcher is not running,
# restart the gateway after regeneration so the updated generated files are used.
#
# Example — add a local GGUF model:
# models:
#   - name: my-model
#     model_file: MyModel/my-model-Q4_K_M.gguf
#     context_size: 4096
#     # Optional: pin to a specific backend (see llama-swap.override.yaml)
#     # executable_macro: llama-server-rocm
EOF
fi

warn_if_generated_configs_stale

if [ ! -f "$CONFIG/local/backend-runtime.override.yaml" ]; then
    echo ">>> First run: seeding config/local/backend-runtime.override.yaml"
    cat > "$CONFIG/local/backend-runtime.override.yaml" <<'EOF'
# AUDia LLM Gateway — backend runtime variant overrides.
# Merged on top of config/project/backend-runtime.base.yaml.
# Use this file to add extra backend binaries (alternate tags, repos, direct URLs, git builds).
#
# profiles:
#   build-rocm-gfx1030-gfx1100:
#     backend: rocm
#     configure_command: cmake -S . -B build -DLLAMA_BUILD_SERVER=ON -DGGML_HIPBLAS=ON -DAMDGPU_TARGETS=gfx1030;gfx1100 -DCMAKE_HIP_ARCHITECTURES=gfx1030;gfx1100 -DCMAKE_BUILD_TYPE=Release
#     build_command: cmake --build build --config Release --parallel
#     source_subdir: .
#     build_root_subdir: rocm/gfx1030-gfx1100
#     build_env:
#       CMAKE_BUILD_PARALLEL_LEVEL: "8"
#     pre_configure_command: cmake --version
#     binary_glob: build/bin/llama-server
#     library_glob: build/bin/*.so*
#     apt_packages:
#       - git
#       - cmake
#       - build-essential
#
#   source-rocm-official-preview:
#     source_type: git
#     git_url: https://github.com/ROCm/llama.cpp.git
#     git_ref: rocm-7.11.0-preview
#
#   source-lemonade-rocm:
#     source_type: git
#     git_url: https://github.com/lemonade-sdk/llamacpp-rocm.git
#     git_ref: main
#
# variants:
#   rocm-gfx1100-rocm-preview:
#     profiles:
#       - source-rocm-official-preview
#       - build-rocm-gfx1030-gfx1100
#     macro: llama-server-rocm-gfx1100-rocm-preview
#     runtime_subdir: rocm/gfx1100/rocm-preview
#     enabled: true
#
#   rocm-gfx1030-lemonade:
#     profiles:
#       - source-lemonade-rocm
#       - build-rocm-gfx1030-gfx1100
#     macro: llama-server-rocm-gfx1030-lemonade
#     runtime_subdir: rocm/gfx1030/lemonade
#     enabled: true
EOF
fi

if [ ! -f "$CONFIG/local/llama-swap.override.yaml" ]; then
    echo ">>> First run: seeding config/local/llama-swap.override.yaml"
    cat > "$CONFIG/local/llama-swap.override.yaml" <<'EOF'
# AUDia LLM Gateway — llama-swap substrate overrides.
# Merged on top of config/project/llama-swap.base.yaml.
# After editing, restart the gateway: docker compose restart gateway
#
# --- Global settings ---
#
# healthCheckTimeout: 300   # seconds to wait for llama-server to start
# logLevel: info            # debug | info | warn | error
#
# --- Backend binary macros ---
# By default all macros resolve to the auto-detected default 'llama-server'
# binary. Override to run different backends per model simultaneously.
# Binaries are provisioned by provision-runtime.sh at container start.
#
# macros:
#   llama-server-cpu:    "/app/runtime-root/cpu/bin/llama-server-cpu"
#   llama-server-cuda:   "/app/runtime-root/cuda/bin/llama-server-cuda"
#   llama-server-rocm:   "env LD_LIBRARY_PATH=/app/runtime-root/rocm/lib:/opt/rocm/lib /app/runtime-root/rocm/bin/llama-server-rocm"
#   llama-server-vulkan: "env VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.json LD_LIBRARY_PATH=/app/runtime-root/vulkan/lib /app/runtime-root/vulkan/bin/llama-server-vulkan"
#   model-path:          "--model /app/models/gguf"
#   mmproj-path:         "--mmproj /app/models/gguf"
#
# --- Running multiple backends simultaneously ---
# Keep LLAMA_BACKEND=auto so the runtime provisions separate ROCm and Vulkan
# directories, then set
# executable_macro per model in
# models.override.yaml to route each model to a specific backend:
#
#   executable_macro: llama-server-rocm     # run this model on ROCm
#   executable_macro: llama-server-vulkan   # run this model on Vulkan
#
# For versioned backend binaries, add entries in
# config/local/backend-runtime.override.yaml. The gateway generates
# /app/config/generated/llama-swap/backend-runtime.catalog.json, and
# provision-runtime.sh will download those variants and expose matching macros.
#
# llama-swap manages each as an independent process — backends are loaded
# and unloaded on demand as requests arrive.
EOF
fi

# --- Seed detect-hardware.sh into config/ for discoverability ---
if [ ! -f "$CONFIG/detect-hardware.sh" ]; then
    if [ -f /app/scripts/detect-hardware.sh ]; then
        cp /app/scripts/detect-hardware.sh "$CONFIG/detect-hardware.sh"
        chmod +x "$CONFIG/detect-hardware.sh"
        echo ">>> First run: seeded config/detect-hardware.sh (run from repo root to detect GPU)"
    fi
fi

# --- Generate all service configs from layered config ---
python -m src.launcher.process_manager --root . generate-configs

echo ">>> Waiting for generated LiteLLM config at $LITELLM_CONFIG_PATH"
waited=0
while [ ! -s "$LITELLM_CONFIG_PATH" ]; do
    if [ "$waited" -ge "$LITELLM_CONFIG_WAIT_SECONDS" ]; then
        echo "ERROR: timed out waiting for LiteLLM config at $LITELLM_CONFIG_PATH"
        exit 1
    fi
    sleep 1
    waited=$((waited + 1))
done

if [ -n "${DATABASE_URL:-}" ]; then
    echo ">>> Waiting for database connectivity from DATABASE_URL"
    python - "$DATABASE_URL" "$DATABASE_WAIT_SECONDS" "$DATABASE_WAIT_INTERVAL_SECONDS" <<'PY'
import socket
import sys
import time
from urllib.parse import urlparse

database_url = sys.argv[1]
timeout_seconds = float(sys.argv[2])
interval_seconds = float(sys.argv[3])
deadline = time.time() + timeout_seconds

parsed = urlparse(database_url)
host = parsed.hostname
port = parsed.port or 5432

if not host:
    print("ERROR: DATABASE_URL does not contain a hostname", flush=True)
    sys.exit(1)

last_error = "unknown error"
attempt = 0
while time.time() < deadline:
    attempt += 1
    try:
        with socket.create_connection((host, port), timeout=5):
            print(
                f">>> Database is reachable at {host}:{port} after {attempt} attempt(s)",
                flush=True,
            )
            sys.exit(0)
    except OSError as exc:
        last_error = str(exc)
        print(
            f">>> Database not reachable yet at {host}:{port} "
            f"(attempt {attempt}): {last_error}",
            flush=True,
        )
        time.sleep(interval_seconds)

print(
    f"ERROR: timed out waiting for database at {host}:{port}: {last_error}",
    flush=True,
)
sys.exit(1)
PY
fi

exec litellm \
    --config "$LITELLM_CONFIG_PATH" \
    --port 4000 \
    --log_config "$UVICORN_LOG_CONFIG_PATH" \
    --enforce_prisma_migration_check
