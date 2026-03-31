#!/usr/bin/env bash
set -euo pipefail

backend=${1:-}
model=${2:-}
elapsed=${3:-}
prompt_tokens=${4:-}
completion_tokens=${5:-}
eval_tok_s=${6:-}
gpu_map=${7:-}
status=${8:-ok}

if [[ -z "$backend" || -z "$model" ]]; then
  echo "usage: collect_metrics.sh <backend> <model> [elapsed] [prompt_tokens] [completion_tokens] [eval_tok_s] [gpu_map] [status]" >&2
  exit 2
fi

python3 - <<'PY' "$backend" "$model" "$elapsed" "$prompt_tokens" "$completion_tokens" "$eval_tok_s" "$gpu_map" "$status"
import json
import sys

backend, model, elapsed, prompt_tokens, completion_tokens, eval_tok_s, gpu_map, status = sys.argv[1:]
record = {
    "backend": backend,
    "model": model,
    "elapsed_s": float(elapsed) if elapsed else None,
    "prompt_tokens": int(prompt_tokens) if prompt_tokens else None,
    "completion_tokens": int(completion_tokens) if completion_tokens else None,
    "eval_tok_s": float(eval_tok_s) if eval_tok_s else None,
    "gpu_map": gpu_map or None,
    "status": status,
}
print(json.dumps(record))
PY

