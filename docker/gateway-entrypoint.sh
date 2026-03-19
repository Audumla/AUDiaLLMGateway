#!/bin/sh
set -e

CONFIG=/app/config

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

if [ ! -f "$CONFIG/local/stack.override.yaml" ]; then
    echo ">>> First run: seeding config/local/stack.override.yaml"
    cat > "$CONFIG/local/stack.override.yaml" <<'EOF'
# AUDia LLM Gateway — local stack overrides.
# Merged on top of config/project/stack.base.yaml.
# Regenerated configs take effect on next gateway restart.
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
#
# Example:
# models:
#   - name: my-model
#     model_file: MyModel/my-model-Q4_K_M.gguf
#     context_size: 4096
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

exec litellm --config "$CONFIG/generated/litellm/litellm.config.yaml" --port 4000
