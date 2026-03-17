#!/usr/bin/env bash
# Run all Docker smoke tests from the repo root.
# Usage: bash tests/docker/run-smoke-tests.sh [distro...]
# Example: bash tests/docker/run-smoke-tests.sh tumbleweed ubuntu
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
DISTROS=("${@:-tumbleweed ubuntu debian fedora rocky}")

PASS=0
FAIL=0

for distro in "${DISTROS[@]}"; do
    dockerfile="$SCRIPT_DIR/Dockerfile.$distro"
    if [ ! -f "$dockerfile" ]; then
        echo "SKIP: no Dockerfile for $distro"
        continue
    fi

    image="audia-smoke-$distro"
    echo
    echo "=========================================="
    echo " Building + running smoke test: $distro"
    echo "=========================================="

    if docker build -f "$dockerfile" -t "$image" "$ROOT_DIR" && \
       docker run --rm "$image"; then
        echo "RESULT: $distro PASSED"
        PASS=$((PASS+1))
    else
        echo "RESULT: $distro FAILED"
        FAIL=$((FAIL+1))
    fi
done

echo
echo "=========================================="
echo " Smoke test summary: $PASS passed, $FAIL failed"
echo "=========================================="

[ "$FAIL" -eq 0 ] || exit 1
