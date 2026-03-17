#!/usr/bin/env bash
# Smoke test entrypoint — run inside each Docker image.
# Simulates an RPM/DEB post-install on a clean system.
# Exit code 0 = pass, non-zero = fail.
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/AUDiaLLMGateway}"
PASS=0
FAIL=0

ok()   { echo "  PASS: $*"; PASS=$((PASS+1)); }
fail() { echo "  FAIL: $*"; FAIL=$((FAIL+1)); }

section() { echo; echo "=== $* ==="; }

# ---------------------------------------------------------------------------
# Stub systemctl so postinstall.sh doesn't error in a Docker container
# ---------------------------------------------------------------------------
mkdir -p /usr/local/bin
cat > /usr/local/bin/systemctl <<'STUB'
#!/bin/sh
echo "[stub] systemctl $*"
exit 0
STUB
chmod +x /usr/local/bin/systemctl

# ---------------------------------------------------------------------------
# 1. Pre-conditions
# ---------------------------------------------------------------------------
section "Pre-conditions"

[ -f "$INSTALL_DIR/scripts/postinstall.sh" ] \
    && ok "postinstall.sh present" \
    || fail "postinstall.sh MISSING"

[ -f "$INSTALL_DIR/scripts/AUDiaLLMGateway.sh" ] \
    && ok "AUDiaLLMGateway.sh present" \
    || fail "AUDiaLLMGateway.sh MISSING"

[ -x "$INSTALL_DIR/scripts/AUDiaLLMGateway.sh" ] \
    && ok "AUDiaLLMGateway.sh is executable" \
    || fail "AUDiaLLMGateway.sh NOT executable"

[ -f "$INSTALL_DIR/requirements.txt" ] \
    && ok "requirements.txt present" \
    || fail "requirements.txt MISSING"

[ -f "$INSTALL_DIR/config/project/stack.base.yaml" ] \
    && ok "stack.base.yaml present" \
    || fail "stack.base.yaml MISSING"

# ---------------------------------------------------------------------------
# 2. Run postinstall.sh
# ---------------------------------------------------------------------------
section "postinstall.sh"

if bash "$INSTALL_DIR/scripts/postinstall.sh" 2>&1; then
    ok "postinstall.sh exited 0"
else
    fail "postinstall.sh exited non-zero (exit $?)"
fi

# ---------------------------------------------------------------------------
# 3. Verify install stack results
# ---------------------------------------------------------------------------
section "install stack results"

[ -d "$INSTALL_DIR/.venv" ] \
    && ok ".venv created" \
    || fail ".venv NOT created"

VENV_PYTHON=""
for p in "$INSTALL_DIR/.venv/bin/python3" "$INSTALL_DIR/.venv/bin/python"; do
    [ -x "$p" ] && VENV_PYTHON="$p" && break
done

[ -n "$VENV_PYTHON" ] \
    && ok "venv python found: $VENV_PYTHON" \
    || fail "venv python NOT found"

if [ -n "$VENV_PYTHON" ]; then
    "$VENV_PYTHON" -c "import yaml" 2>&1 \
        && ok "yaml importable from venv" \
        || fail "yaml NOT importable from venv"

    (cd "$INSTALL_DIR" && "$VENV_PYTHON" -c "from src.launcher.process_manager import main") 2>/dev/null \
        && ok "process_manager importable" \
        || fail "process_manager NOT importable"

    (cd "$INSTALL_DIR" && "$VENV_PYTHON" -c "from src.installer.release_installer import main") 2>/dev/null \
        && ok "release_installer importable" \
        || fail "release_installer NOT importable"
fi

# ---------------------------------------------------------------------------
# 4. Verify generate results
# ---------------------------------------------------------------------------
section "generate results"

for f in \
    "$INSTALL_DIR/config/generated/llama-swap/llama-swap.generated.yaml" \
    "$INSTALL_DIR/config/generated/litellm/litellm.config.yaml" \
    "$INSTALL_DIR/config/generated/nginx/nginx.conf"
do
    [ -f "$f" ] \
        && ok "generated: $(basename $f)" \
        || fail "NOT generated: $f"
done

# ---------------------------------------------------------------------------
# 5. Run generate independently to confirm it uses venv Python
# ---------------------------------------------------------------------------
section "AUDiaLLMGateway.sh generate (standalone)"

if (cd "$INSTALL_DIR" && bash scripts/AUDiaLLMGateway.sh generate 2>&1); then
    ok "generate command succeeded"
else
    fail "generate command FAILED (likely wrong Python — check venv)"
fi

# ---------------------------------------------------------------------------
# 6. Systemd stubs were called
# ---------------------------------------------------------------------------
section "systemd"

[ -f /etc/systemd/system/audia-gateway.service ] \
    && ok "service file installed" \
    || fail "service file NOT installed at /etc/systemd/system/"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
section "Summary"
echo "  Passed: $PASS"
echo "  Failed: $FAIL"
echo

if [ "$FAIL" -gt 0 ]; then
    echo "SMOKE TEST FAILED"
    exit 1
fi

echo "SMOKE TEST PASSED"
exit 0
