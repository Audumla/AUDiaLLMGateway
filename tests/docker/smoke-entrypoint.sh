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
# 3. Verify install stack + components results
# ---------------------------------------------------------------------------
section "install stack + components results"

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
# 4. Verify component install (llama-swap and llama.cpp binaries wired up)
# ---------------------------------------------------------------------------
section "component install results"

STATE_FILE="$INSTALL_DIR/state/install-state.json"
[ -f "$STATE_FILE" ] \
    && ok "install-state.json created" \
    || fail "install-state.json MISSING — install components did not run"

if [ -f "$STATE_FILE" ] && [ -n "$VENV_PYTHON" ]; then
    SWAP_PATH=$("$VENV_PYTHON" -c "
import json, sys
s = json.load(open('$STATE_FILE'))
print(s.get('component_results', {}).get('llama_swap', {}).get('path', ''))
" 2>/dev/null)
    [ -n "$SWAP_PATH" ] \
        && ok "llama-swap path recorded: $SWAP_PATH" \
        || fail "llama-swap path NOT recorded in state"

    LLAMA_PATH=$("$VENV_PYTHON" -c "
import json, sys
s = json.load(open('$STATE_FILE'))
print(s.get('component_results', {}).get('llama_cpp', {}).get('executable_path', ''))
" 2>/dev/null)
    [ -n "$LLAMA_PATH" ] \
        && ok "llama-server path recorded: $LLAMA_PATH" \
        || fail "llama-server path NOT recorded in state"

    # Verify the generated llama-swap config doesn't have Windows paths
    GENERATED_CFG="$INSTALL_DIR/config/generated/llama-swap/llama-swap.generated.yaml"
    if [ -f "$GENERATED_CFG" ]; then
        if grep -q 'C:\\' "$GENERATED_CFG" 2>/dev/null; then
            fail "generated llama-swap config contains Windows paths"
        else
            ok "generated llama-swap config has no Windows paths"
        fi
        # Verify llama-server macro is set to the state path (or a Linux path)
        MACRO_VAL=$(grep 'llama-server:' "$GENERATED_CFG" | head -1 | sed "s/.*llama-server: //; s/'//g; s/\"//g")
        if [ -n "$MACRO_VAL" ]; then
            ok "llama-server macro set: $MACRO_VAL"
        else
            fail "llama-server macro NOT set in generated config"
        fi
    fi
fi

# ---------------------------------------------------------------------------
# 5. Verify generate results
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
# 6. Run generate independently to confirm it uses venv Python
# ---------------------------------------------------------------------------
section "AUDiaLLMGateway.sh generate (standalone)"

if (cd "$INSTALL_DIR" && bash scripts/AUDiaLLMGateway.sh generate 2>&1); then
    ok "generate command succeeded"
else
    fail "generate command FAILED (likely wrong Python — check venv)"
fi

# ---------------------------------------------------------------------------
# 7. Systemd and env file
# ---------------------------------------------------------------------------
section "systemd and env file"

[ -f /etc/systemd/system/audia-gateway.service ] \
    && ok "service file installed" \
    || fail "service file NOT installed at /etc/systemd/system/"

# Service unit must declare EnvironmentFile so LITELLM_MASTER_KEY is picked up
grep -q "EnvironmentFile" /etc/systemd/system/audia-gateway.service 2>/dev/null \
    && ok "service unit has EnvironmentFile directive" \
    || fail "service unit missing EnvironmentFile directive"

# postinstall must have seeded config/local/env
[ -f "$INSTALL_DIR/config/local/env" ] \
    && ok "config/local/env seeded by postinstall" \
    || fail "config/local/env NOT created by postinstall"

# The seeded env file must contain LITELLM_MASTER_KEY
grep -q "LITELLM_MASTER_KEY" "$INSTALL_DIR/config/local/env" 2>/dev/null \
    && ok "LITELLM_MASTER_KEY present in config/local/env" \
    || fail "LITELLM_MASTER_KEY NOT found in config/local/env"

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
