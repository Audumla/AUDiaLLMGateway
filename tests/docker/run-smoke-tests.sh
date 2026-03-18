#!/usr/bin/env bash
# Run Docker smoke tests, e2e mock tests, and integration tests from the repo root.
#
# Usage: bash tests/docker/run-smoke-tests.sh [targets...]
# Targets: tumbleweed | ubuntu | debian | fedora | rocky | e2e | integration
#
# Default (no args): runs all except integration (which downloads a real model).
# Integration test:  bash tests/docker/run-smoke-tests.sh integration
# All including integration: bash tests/docker/run-smoke-tests.sh all
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Default set excludes integration (requires model download ~100MB)
DEFAULT_TARGETS=(tumbleweed ubuntu debian fedora rocky e2e)

# Expand 'all' shortcut
TARGETS=()
for arg in "${@:-${DEFAULT_TARGETS[@]}}"; do
    if [ "$arg" = "all" ]; then
        TARGETS+=(tumbleweed ubuntu debian fedora rocky e2e integration)
    else
        TARGETS+=("$arg")
    fi
done

PASS=0
FAIL=0

for target in "${TARGETS[@]}"; do
    dockerfile="$SCRIPT_DIR/Dockerfile.$target"
    if [ ! -f "$dockerfile" ]; then
        echo "SKIP: no Dockerfile for $target"
        continue
    fi

    case "$target" in
        e2e)
            image="audia-e2e"
            label="e2e mock test"
            run_args="--rm"
            ;;
        integration)
            image="audia-integration"
            label="integration test (real inference)"
            # Mount a model cache dir so the model isn't re-downloaded each run
            MODEL_CACHE="${AUDIA_MODEL_CACHE:-$ROOT_DIR/test-work/models}"
            mkdir -p "$MODEL_CACHE"
            run_args="--rm -v ${MODEL_CACHE}:/models -e MODEL_DIR=/models -e LITELLM_MASTER_KEY=sk-test"
            ;;
        *)
            image="audia-smoke-$target"
            label="smoke test: $target"
            run_args="--rm"
            ;;
    esac

    echo
    echo "=========================================="
    echo " Building + running $label"
    echo "=========================================="

    # shellcheck disable=SC2086
    if docker build --network=host -f "$dockerfile" -t "$image" "$ROOT_DIR" && \
       docker run $run_args "$image"; then
        echo "RESULT: $target PASSED"
        PASS=$((PASS+1))
    else
        echo "RESULT: $target FAILED"
        FAIL=$((FAIL+1))
    fi
done

echo
echo "=========================================="
echo " Summary: $PASS passed, $FAIL failed"
echo "=========================================="

[ "$FAIL" -eq 0 ] || exit 1
