#!/usr/bin/env bash
set -euo pipefail

backend_name=${1:-}
container_name=${2:-}
health_url=${3:-}

if [[ -z "$backend_name" || -z "$container_name" || -z "$health_url" ]]; then
  echo "usage: preflight.sh <backend_name> <container_name> <health_url>" >&2
  exit 2
fi

command -v docker >/dev/null 2>&1 || {
  echo "docker not available" >&2
  exit 1
}

if docker inspect "$container_name" >/dev/null 2>&1; then
  state=$(docker inspect -f '{{.State.Status}}' "$container_name" 2>/dev/null || echo missing)
  if [[ "$state" != "exited" && "$state" != "dead" && "$state" != "missing" ]]; then
    echo "backend $backend_name is already running in $container_name ($state)" >&2
    exit 1
  fi
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl not available" >&2
  exit 1
fi

echo "preflight ok: $backend_name -> $container_name -> $health_url"

