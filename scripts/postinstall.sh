#!/bin/bash
# Initialize the stack after installation.
# Intentionally no "set -e" — component download failures are non-fatal;
# critical steps use explicit || exit 1.

cd /opt/AUDiaLLMGateway

# Ensure scripts are executable (fix for RPM packaging)
chmod +x scripts/*.sh scripts/*.ps1 scripts/*.cmd 2>/dev/null || true

# Ensure runtime directories exist
mkdir -p state config/local

# Seed a default env file for the systemd service if none exists.
# config/local/ is a protected path — updates never overwrite it.
if [ ! -f config/local/env ]; then
    cat > config/local/env <<'EOF'
# AUDia LLM Gateway — local environment overrides.
# This file is loaded by the systemd service unit (EnvironmentFile).
# Edit to set your own master key before starting the service.
LITELLM_MASTER_KEY=sk-local-dev
EOF
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
