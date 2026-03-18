#!/usr/bin/env bash
# Run all Docker smoke tests and e2e mock test from the repo root.
# Usage: bash tests/docker/run-smoke-tests.sh [distro...]
# Example: bash tests/docker/run-smoke-tests.sh tumbleweed ubuntu e2e
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
DISTROS=("${@:-tumbleweed ubuntu debian fedora rocky e2e}")

PASS=0
FAIL=0

for distro in "${DISTROS[@]}"; do
    dockerfile="$SCRIPT_DIR/Dockerfile.$distro"
    if [ ! -f "$dockerfile" ]; then
        echo "SKIP: no Dockerfile for $distro"
        continue
    fi

    if [ "$distro" = "e2e" ]; then
        image="audia-e2e"
        label="e2e mock test"
    else
        image="audia-smoke-$distro"
        label="smoke test: $distro"
    fi

    echo
    echo "=========================================="
    echo " Building + running $label"
    echo "=========================================="

    if docker build --network=host -f "$dockerfile" -t "$image" "$ROOT_DIR" && \
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
echo " Summary: $PASS passed, $FAIL failed"
echo "=========================================="

[ "$FAIL" -eq 0 ] || exit 1
