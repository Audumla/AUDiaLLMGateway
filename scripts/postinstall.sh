#!/bin/bash
set -e

# Initialize the stack after installation
cd /opt/AUDiaLLMGateway
./scripts/AUDiaLLMGateway.sh install stack
./scripts/AUDiaLLMGateway.sh generate

# Reload systemd to recognize the new service
systemctl daemon-reload
