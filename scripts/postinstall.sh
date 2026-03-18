#!/bin/bash
# Initialize the stack after installation.
# Intentionally no "set -e" — component download failures are non-fatal;
# critical steps use explicit || exit 1.

cd /opt/AUDiaLLMGateway

# Ensure scripts are executable (fix for RPM packaging)
chmod +x scripts/*.sh scripts/*.ps1 scripts/*.cmd 2>/dev/null || true

# Ensure runtime directories exist
mkdir -p state config/local

# config/local/ is a protected path — updates never overwrite it.
# Make it and its files editable by all local users (home-lab default).
chmod 777 config/local

# Seed the service environment file (contains the LiteLLM master key).
# Keep it root-readable only since it holds credentials.
if [ ! -f config/local/env ]; then
    cat > config/local/env <<'EOF'
# AUDia LLM Gateway — service environment overrides.
# Loaded by the systemd unit (EnvironmentFile). Changes take effect on
# the next 'systemctl restart audia-gateway'.
LITELLM_MASTER_KEY=sk-local-dev
EOF
    chmod 600 config/local/env
fi

# Seed a base stack override file so users can customise ports and hosts
# without editing the project-managed defaults. World-writable so any
# local user can edit it without sudo.
if [ ! -f config/local/stack.override.yaml ]; then
    cat > config/local/stack.override.yaml <<'EOF'
# AUDia LLM Gateway — local stack overrides.
# Values here are merged on top of config/project/stack.base.yaml.
# This file is preserved across updates. Edit freely.
# After editing run: ./scripts/AUDiaLLMGateway.sh generate
#                then: systemctl restart audia-gateway
#
# --- Common customisations ---
#
# Change the LiteLLM gateway port and bind address:
# network:
#   public_host: 0.0.0.0
#   services:
#     litellm:
#       host: 0.0.0.0
#       port: 4000
#
# Change the llama-swap internal port:
# network:
#   services:
#     llama_swap:
#       port: 41080
#
# Enable nginx reverse proxy:
# reverse_proxy:
#   nginx:
#     enabled: true
EOF
    chmod 666 config/local/stack.override.yaml
fi

# Install Python venv and pip dependencies (hard failure — nothing works without this)
./scripts/AUDiaLLMGateway.sh install stack \
    || { echo "[error] Python stack install failed"; exit 1; }

# Download llama-swap and llama.cpp binaries (soft failure — user can retry with
# './scripts/AUDiaLLMGateway.sh install components')
./scripts/AUDiaLLMGateway.sh install components \
    || echo "[warn] Component install had errors — run 'AUDiaLLMGateway.sh install components' to retry"

# Generate runtime configs from installed state (hard failure)
./scripts/AUDiaLLMGateway.sh generate \
    || { echo "[error] Config generation failed"; exit 1; }

# Register and enable the systemd service
systemctl daemon-reload
systemctl enable audia-gateway

# Start the service now so the install is immediately operational.
# A start failure here does not abort the package install — the user can
# investigate with 'systemctl status audia-gateway'.
systemctl start audia-gateway \
    || echo "[warn] Service start failed — check 'systemctl status audia-gateway'"
