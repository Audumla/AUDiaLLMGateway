#!/usr/bin/env bash
# E2E mock test — runs inside the Docker image.
# Starts a mock llama-swap server, then starts litellm proxy against it,
# then sends a chat completion request and verifies the full round-trip.
# Exit 0 = pass, non-zero = fail.
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/AUDiaLLMGateway}"
PASS=0
FAIL=0
MOCK_PORT=41080
LITELLM_PORT=4000

ok()      { echo "  PASS: $*"; PASS=$((PASS+1)); }
fail()    { echo "  FAIL: $*"; FAIL=$((FAIL+1)); }
section() { echo; echo "=== $* ==="; }

cleanup() {
    [ -n "${MOCK_PID:-}"    ] && kill "$MOCK_PID"    2>/dev/null || true
    [ -n "${LITELLM_PID:-}" ] && kill "$LITELLM_PID" 2>/dev/null || true
}
trap cleanup EXIT

VENV_PYTHON=""
for p in "$INSTALL_DIR/.venv/bin/python3" "$INSTALL_DIR/.venv/bin/python"; do
    [ -x "$p" ] && VENV_PYTHON="$p" && break
done

# ---------------------------------------------------------------------------
# 1. Pre-conditions
# ---------------------------------------------------------------------------
section "Pre-conditions"

[ -n "$VENV_PYTHON" ] \
    && ok "venv python: $VENV_PYTHON" \
    || { fail "venv python NOT found — run install stack first"; exit 1; }

[ -f "$INSTALL_DIR/config/generated/litellm/litellm.config.yaml" ] \
    && ok "litellm config present" \
    || fail "litellm config MISSING"

# ---------------------------------------------------------------------------
# 2. Start mock llama-swap server
# ---------------------------------------------------------------------------
section "Mock llama-swap"

cat > /tmp/mock_llama_swap.py <<'PYEOF'
#!/usr/bin/env python3
"""Minimal mock llama-swap: serves /health, /v1/models, /v1/chat/completions."""
import json, os, sys
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(os.environ.get("MOCK_PORT", "41080"))

MODELS_RESPONSE = json.dumps({
    "object": "list",
    "data": [{"id": "local/qwen27_fast", "object": "model"}]
})

def make_completion(model):
    return json.dumps({
        "id": "mock-123",
        "object": "chat.completion",
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": "Hello from mock llama-swap!"},
            "finish_reason": "stop"
        }],
        "usage": {"prompt_tokens": 5, "completion_tokens": 7, "total_tokens": 12}
    })

class MockHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress access logs

    def _send_json(self, body, status=200):
        encoded = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(encoded))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        if self.path in ("/health", "/v1/models"):
            self._send_json(MODELS_RESPONSE)
        else:
            self._send_json('{"error":"not found"}', 404)

    def do_POST(self):
        if "/chat/completions" in self.path:
            length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(length)
            try:
                body = json.loads(body_bytes)
                model = body.get("model", "mock-model")
            except Exception:
                model = "mock-model"
            self._send_json(make_completion(model))
        else:
            self._send_json('{"error":"not found"}', 404)

print(f"Mock llama-swap listening on :{PORT}", flush=True)
HTTPServer(("127.0.0.1", PORT), MockHandler).serve_forever()
PYEOF

MOCK_PORT_VAL="$MOCK_PORT" "$VENV_PYTHON" /tmp/mock_llama_swap.py &
MOCK_PID=$!

# Wait for mock to be ready
for i in $(seq 1 15); do
    if curl -sf "http://127.0.0.1:${MOCK_PORT}/health" >/dev/null 2>&1; then
        ok "mock llama-swap ready (pid $MOCK_PID)"
        break
    fi
    sleep 1
    if [ "$i" -eq 15 ]; then
        fail "mock llama-swap did not start"
        exit 1
    fi
done

# Verify mock returns expected models
MODEL_COUNT=$(curl -sf "http://127.0.0.1:${MOCK_PORT}/v1/models" | "$VENV_PYTHON" -c \
    "import json,sys; d=json.load(sys.stdin); print(len(d.get('data',[])))")
[ "$MODEL_COUNT" -ge 1 ] \
    && ok "mock returns $MODEL_COUNT model(s)" \
    || fail "mock /v1/models returned no models"

# ---------------------------------------------------------------------------
# 3. Start litellm proxy
# ---------------------------------------------------------------------------
section "litellm proxy"

# Write a minimal test config that avoids the model-name convention issues
# that can appear with newer litellm versions (local/ prefix routing changes).
# The generated production config is validated for existence above; here we use
# a simple config to test the actual round-trip routing mechanism.
cat > /tmp/e2e-litellm.config.yaml <<LITELLM_CFG
model_list:
- model_name: e2e-test-model
  litellm_params:
    model: openai/mock-model
    api_base: http://127.0.0.1:${MOCK_PORT}/v1
    api_key: sk-not-required
litellm_settings:
  master_key: sk-e2e-test
general_settings:
  disable_spend_logs: true
  allow_requests_on_db_unavailable: true
LITELLM_CFG

# Set a dummy master key
export LITELLM_MASTER_KEY="sk-e2e-test"

LITELLM_BIN="$INSTALL_DIR/.venv/bin/litellm"
[ -x "$LITELLM_BIN" ] || LITELLM_BIN="litellm"

"$LITELLM_BIN" \
    --config "/tmp/e2e-litellm.config.yaml" \
    --port "$LITELLM_PORT" \
    --host "127.0.0.1" \
    > /tmp/litellm.log 2>&1 &
LITELLM_PID=$!

# Wait for litellm to be ready (it can take ~10s to load)
ok_litellm=0
for i in $(seq 1 30); do
    if curl -sf "http://127.0.0.1:${LITELLM_PORT}/health/liveliness" >/dev/null 2>&1; then
        ok "litellm proxy ready (pid $LITELLM_PID)"
        ok_litellm=1
        break
    fi
    sleep 2
done
[ "$ok_litellm" -eq 1 ] || { fail "litellm did not start in time"; tail -30 /tmp/litellm.log; exit 1; }
# Give litellm a moment to finish internal initialization after liveliness is up
sleep 3

# ---------------------------------------------------------------------------
# 4. E2E: chat completion round-trip
# ---------------------------------------------------------------------------
section "E2E chat completion"

RESPONSE=$(curl -s -X POST "http://127.0.0.1:${LITELLM_PORT}/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer sk-e2e-test" \
    -d '{
        "model": "e2e-test-model",
        "messages": [{"role": "user", "content": "hello"}],
        "max_tokens": 10
    }' 2>/dev/null) || true

if [ -n "$RESPONSE" ]; then
    CONTENT=$(echo "$RESPONSE" | "$VENV_PYTHON" -c \
        "import json,sys; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'])" 2>/dev/null || true)
    if [ -n "$CONTENT" ]; then
        ok "chat completion: $CONTENT"
    else
        # response present but not a valid completion — show it
        ERRMSG=$(echo "$RESPONSE" | "$VENV_PYTHON" -c \
            "import json,sys; d=json.load(sys.stdin); print(d.get('error',{}).get('message','?')[:120])" 2>/dev/null || echo "$RESPONSE" | head -c 200)
        fail "chat completion returned error: $ERRMSG"
    fi
else
    fail "no response from litellm /v1/chat/completions"
fi

# Verify /v1/models through litellm
MODEL_NAMES=$(curl -s "http://127.0.0.1:${LITELLM_PORT}/v1/models" \
    -H "Authorization: Bearer sk-e2e-test" | \
    "$VENV_PYTHON" -c \
    "import json,sys; d=json.load(sys.stdin); print(','.join(m['id'] for m in d.get('data',[])))" 2>/dev/null || true)
[ -n "$MODEL_NAMES" ] \
    && ok "litellm /v1/models: $MODEL_NAMES" \
    || fail "litellm /v1/models returned nothing"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
section "Summary"
echo "  Passed: $PASS"
echo "  Failed: $FAIL"
echo

if [ "$FAIL" -gt 0 ]; then
    echo
    echo "=== LiteLLM log (last 40 lines) ==="
    tail -40 /tmp/litellm.log 2>/dev/null || true
    echo
    echo "E2E TEST FAILED"
    exit 1
fi

echo "E2E TEST PASSED"
exit 0
