#!/bin/bash
set -e

# Initialize the stack after installation
cd /opt/AUDiaLLMGateway

# Ensure scripts are executable (fix for RPM packaging)
chmod +x scripts/*.sh scripts/*.ps1 scripts/*.cmd 2>/dev/null || true

# Ensure protected runtime directories exist
mkdir -p state

./scripts/AUDiaLLMGateway.sh install stack
./scripts/AUDiaLLMGateway.sh install components
./scripts/AUDiaLLMGateway.sh generate

# Register and enable the systemd service
systemctl daemon-reload
systemctl enable audia-gateway
