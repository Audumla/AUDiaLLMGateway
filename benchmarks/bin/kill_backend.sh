#!/usr/bin/env bash
set -euo pipefail

target=${1:-}
if [[ -z "$target" ]]; then
  echo "usage: kill_backend.sh <container_name_or_process_pattern>" >&2
  exit 2
fi

if docker inspect "$target" >/dev/null 2>&1; then
  docker rm -f "$target" >/dev/null 2>&1 || true
else
  pkill -9 -f "$target" >/dev/null 2>&1 || true
fi

echo "killed: $target"

