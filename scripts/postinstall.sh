#!/bin/bash
set -e

# Initialize the stack after installation
cd /opt/AUDiaLLMGateway

# Ensure protected runtime directories exist
mkdir -p state

./scripts/AUDiaLLMGateway.sh install stack
./scripts/AUDiaLLMGateway.sh generate

# Register and enable the systemd service
systemctl daemon-reload
systemctl enable audia-gateway
