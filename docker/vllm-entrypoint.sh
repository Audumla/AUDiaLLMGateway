#!/bin/sh
set -e

CONFIG_PATH="${VLLM_GENERATED_CONFIG_PATH:-/app/config/generated/vllm/vllm.config.json}"
CONFIG_WAIT_SECONDS="${VLLM_CONFIG_WAIT_SECONDS:-30}"

echo ">>> Waiting for generated vLLM config at $CONFIG_PATH"
waited=0
while [ ! -s "$CONFIG_PATH" ]; do
    if [ "$waited" -ge "$CONFIG_WAIT_SECONDS" ]; then
        echo "ERROR: timed out waiting for vLLM config at $CONFIG_PATH"
        exit 1
    fi
    sleep 1
    waited=$((waited + 1))
done

if [ "${VLLM_MOCK_MODE:-false}" = "true" ]; then
    exec python /app/vllm-mock-server.py "$CONFIG_PATH"
fi

python - "$CONFIG_PATH" <<'PY'
import json
import os
import sys

config_path = sys.argv[1]
with open(config_path, "r", encoding="utf-8") as handle:
    config = json.load(handle)

startup = config.get("startup", {})
model = startup.get("model") or os.environ.get("VLLM_MODEL")
if not model:
    raise SystemExit("No vLLM model configured")

args = [
    "python",
    "-m",
    "vllm.entrypoints.openai.api_server",
    "--host",
    "0.0.0.0",
    "--port",
    str(config.get("service", {}).get("port", 8000)),
    "--model",
    str(model),
    "--gpu-memory-utilization",
    str(startup.get("gpu_memory_utilization", 0.85)),
    "--max-model-len",
    str(startup.get("max_model_len", 4096)),
]
os.execvp(args[0], args)
PY
