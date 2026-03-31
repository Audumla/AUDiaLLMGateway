#!/usr/bin/env bash
set -euo pipefail

gateway_container=${1:-audia-llama-cpp}

if docker inspect "$gateway_container" >/dev/null 2>&1; then
  docker restart "$gateway_container" >/dev/null
  echo "restarted: $gateway_container"
else
  echo "gateway container not found: $gateway_container" >&2
  exit 1
fi

