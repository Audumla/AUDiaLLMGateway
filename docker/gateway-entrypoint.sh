#!/bin/sh
set -e
python -m src.launcher.process_manager --root . generate-configs
exec litellm --config /app/config/generated/litellm/litellm.config.yaml --port 4000
