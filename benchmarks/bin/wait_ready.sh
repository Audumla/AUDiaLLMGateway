#!/usr/bin/env bash
set -euo pipefail

name=${1:-}
health_url=${2:-}
container_name=${3:-}
timeout=${4:-600}

if [[ -z "$name" || -z "$health_url" || -z "$container_name" ]]; then
  echo "usage: wait_ready.sh <name> <health_url> <container_name> [timeout_seconds]" >&2
  exit 2
fi

start=$(date +%s)
while true; do
  if curl -sf "$health_url" >/dev/null 2>&1; then
    echo "ready: $name"
    exit 0
  fi

  state=$(docker inspect -f '{{.State.Status}}' "$container_name" 2>/dev/null || echo missing)
  if [[ "$state" == "exited" || "$state" == "dead" || "$state" == "missing" ]]; then
    echo "stopped-before-ready: $name ($state)" >&2
    exit 1
  fi

  if (( $(date +%s) - start > timeout )); then
    echo "timeout waiting for $name" >&2
    exit 1
  fi

  sleep 5
done

