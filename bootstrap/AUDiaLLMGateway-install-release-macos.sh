#!/usr/bin/env bash
set -euo pipefail

exec "$(dirname "$0")/AUDiaLLMGateway-install-release.sh" "$@"
