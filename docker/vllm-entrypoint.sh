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
    exec "${PYTHON_BIN:-python3}" /app/vllm-mock-server.py "$CONFIG_PATH"
fi

PYTHON_BIN="$(command -v python3 || command -v python || true)"
if [ -z "$PYTHON_BIN" ]; then
    echo "ERROR: neither python3 nor python was found in the vLLM container"
    exit 1
fi

"$PYTHON_BIN" - "$CONFIG_PATH" "$PYTHON_BIN" <<'PY'
import json
import os
import sys

config_path = sys.argv[1]
python_bin = sys.argv[2]
with open(config_path, "r", encoding="utf-8") as handle:
    config = json.load(handle)

startup = config.get("startup", {})
model = startup.get("model") or os.environ.get("VLLM_MODEL")
if not model:
    raise SystemExit("No vLLM model configured")

args = [
    python_bin,
    "-m",
    "vllm.entrypoints.openai.api_server",
    "--host",
    "0.0.0.0",
    "--port",
    str(config.get("service", {}).get("port", 8000)),
    "--model",
    str(model),
    "--gpu-memory-utilization",
    str(startup.get("gpu_memory_utilization", 1.0)),
    "--max-model-len",
    str(startup.get("max_model_len", 4096)),
]
os.execvp(args[0], args)
PY
