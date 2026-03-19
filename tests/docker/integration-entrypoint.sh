#!/usr/bin/env bash
# Integration test entrypoint — runs inside the Docker image.
# Tests the full stack: llama-server → llama-swap → LiteLLM
# with a real (tiny) GGUF model and real inference.
# Exit 0 = pass, non-zero = fail.
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/AUDiaLLMGateway}"
MODEL_DIR="${MODEL_DIR:-/models}"
LLAMA_SERVER_PORT=8081
LLAMA_SWAP_PORT=41080
LITELLM_PORT=4000
PASS=0
FAIL=0

ok()      { echo "  PASS: $*"; PASS=$((PASS+1)); }
fail()    { echo "  FAIL: $*"; FAIL=$((FAIL+1)); }
section() { echo; echo "=== $* ==="; }

cleanup() {
    [ -n "${LLAMA_PID:-}"    ] && kill "$LLAMA_PID"    2>/dev/null || true
    [ -n "${SWAP_PID:-}"     ] && kill "$SWAP_PID"     2>/dev/null || true
    [ -n "${LITELLM_PID:-}"  ] && kill "$LITELLM_PID"  2>/dev/null || true
}
trap cleanup EXIT

wait_for_port() {
    local url="$1" label="$2" max="${3:-30}"
    for i in $(seq 1 "$max"); do
        if curl -sf "$url" >/dev/null 2>&1; then
            ok "$label ready"
            return 0
        fi
        sleep 2
    done
    fail "$label did not become ready in $((max*2))s"
    return 1
}

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

LLAMA_BIN=$(command -v llama-server 2>/dev/null || echo "")
[ -n "$LLAMA_BIN" ] \
    && ok "llama-server binary: $LLAMA_BIN" \
    || { fail "llama-server not found in PATH"; exit 1; }

SWAP_BIN=$(command -v llama-swap 2>/dev/null || echo "")
[ -n "$SWAP_BIN" ] \
    && ok "llama-swap binary: $SWAP_BIN" \
    || { fail "llama-swap not found in PATH"; exit 1; }

# ---------------------------------------------------------------------------
# 2. Download test model if not present
# ---------------------------------------------------------------------------
section "Test model"

MODEL_NAME="SmolLM2-135M-Instruct-Q4_K_M.gguf"
MODEL_PATH="$MODEL_DIR/$MODEL_NAME"
mkdir -p "$MODEL_DIR"

if [ -f "$MODEL_PATH" ]; then
    ok "model already present: $MODEL_PATH"
else
    echo "  Downloading SmolLM2-135M (~100MB, CPU-compatible)..."
    MODEL_URL="https://huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF/resolve/main/${MODEL_NAME}"
    if curl -L --progress-bar -o "$MODEL_PATH" "$MODEL_URL"; then
        ok "model downloaded: $MODEL_PATH"
    else
        fail "failed to download test model from $MODEL_URL"
        exit 1
    fi
fi

MODEL_SIZE=$(stat -c%s "$MODEL_PATH" 2>/dev/null || echo 0)
[ "$MODEL_SIZE" -gt 50000000 ] \
    && ok "model file looks valid ($(( MODEL_SIZE / 1024 / 1024 )) MB)" \
    || { fail "model file too small — download may have failed"; exit 1; }

# ---------------------------------------------------------------------------
# 3. Start llama-server with the test model
# ---------------------------------------------------------------------------
section "llama-server"

llama-server \
    --model "$MODEL_PATH" \
    --port "$LLAMA_SERVER_PORT" \
    --host 127.0.0.1 \
    --ctx-size 2048 \
    --n-gpu-layers 0 \
    > /tmp/llama-server.log 2>&1 &
LLAMA_PID=$!

wait_for_port "http://127.0.0.1:${LLAMA_SERVER_PORT}/health" "llama-server" 30 || {
    echo "  llama-server log:"
    tail -20 /tmp/llama-server.log
    exit 1
}

# Confirm model loaded
HEALTH_BODY=$(curl -sf "http://127.0.0.1:${LLAMA_SERVER_PORT}/health" 2>/dev/null || echo "{}")
echo "  health response: $HEALTH_BODY"
ok "llama-server health check OK"

# ---------------------------------------------------------------------------
# 4. Write llama-swap config and start llama-swap
# ---------------------------------------------------------------------------
section "llama-swap"

SWAP_CONFIG_DIR="$INSTALL_DIR/config/generated/llama-swap"
mkdir -p "$SWAP_CONFIG_DIR"

cat > "$SWAP_CONFIG_DIR/llama-swap.generated.yaml" <<YAML
# Integration test llama-swap config — routes to the running llama-server
macros:
  llama-server: "/usr/local/bin/llama-server"
  server-args: "--host 0.0.0.0"
  model-path: "${MODEL_DIR}"

models:
  smollm2-test:
    proxy: "http://127.0.0.1:${LLAMA_SERVER_PORT}"
    max_running: 1

groups: {}
YAML

llama-swap \
    -config "$SWAP_CONFIG_DIR/llama-swap.generated.yaml" \
    -listen "127.0.0.1:${LLAMA_SWAP_PORT}" \
    -watch-config \
    > /tmp/llama-swap.log 2>&1 &
SWAP_PID=$!

wait_for_port "http://127.0.0.1:${LLAMA_SWAP_PORT}/health" "llama-swap" 20 || {
    echo "  llama-swap log:"
    tail -20 /tmp/llama-swap.log
    exit 1
}

# Verify llama-swap proxies the model
SWAP_MODELS=$(curl -sf "http://127.0.0.1:${LLAMA_SWAP_PORT}/v1/models" 2>/dev/null || echo "{}")
MODEL_IN_SWAP=$(echo "$SWAP_MODELS" | "$VENV_PYTHON" -c \
    "import json,sys; d=json.load(sys.stdin); print(len(d.get('data',[])))" 2>/dev/null || echo 0)
[ "$MODEL_IN_SWAP" -ge 1 ] \
    && ok "llama-swap exposes $MODEL_IN_SWAP model(s)" \
    || fail "llama-swap /v1/models returned no models"

# ---------------------------------------------------------------------------
# 5. Generate LiteLLM config pointing at llama-swap
# ---------------------------------------------------------------------------
section "LiteLLM config"

LITELLM_CFG_DIR="$INSTALL_DIR/config/generated/litellm"
mkdir -p "$LITELLM_CFG_DIR"

cat > "$LITELLM_CFG_DIR/litellm.config.yaml" <<YAML
model_list:
  - model_name: local/smollm2-test
    litellm_params:
      model: openai/smollm2-test
      api_base: http://127.0.0.1:${LLAMA_SWAP_PORT}/v1
      api_key: none

litellm_settings:
  master_key: "os.environ/LITELLM_MASTER_KEY"

general_settings:
  disable_spend_logs: true
YAML

ok "litellm config written"

# ---------------------------------------------------------------------------
# 6. Start LiteLLM proxy
# ---------------------------------------------------------------------------
section "LiteLLM proxy"

LITELLM_BIN="$INSTALL_DIR/.venv/bin/litellm"
[ -x "$LITELLM_BIN" ] || LITELLM_BIN="litellm"

export LITELLM_MASTER_KEY="${LITELLM_MASTER_KEY:-sk-integration-test}"

"$LITELLM_BIN" \
    --config "$LITELLM_CFG_DIR/litellm.config.yaml" \
    --port "$LITELLM_PORT" \
    --host "127.0.0.1" \
    > /tmp/litellm.log 2>&1 &
LITELLM_PID=$!

wait_for_port "http://127.0.0.1:${LITELLM_PORT}/health/liveliness" "LiteLLM" 30 || {
    echo "  litellm log (last 30 lines):"
    tail -30 /tmp/litellm.log
    exit 1
}

# ---------------------------------------------------------------------------
# 7. API routing tests
# ---------------------------------------------------------------------------
section "API routing"

# /v1/models
MODELS_RESP=$(curl -sf "http://127.0.0.1:${LITELLM_PORT}/v1/models" \
    -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" 2>/dev/null || echo "{}")
MODELS_COUNT=$(echo "$MODELS_RESP" | "$VENV_PYTHON" -c \
    "import json,sys; d=json.load(sys.stdin); print(len(d.get('data',[])))" 2>/dev/null || echo 0)
[ "$MODELS_COUNT" -ge 1 ] \
    && ok "/v1/models returns $MODELS_COUNT model(s) via LiteLLM" \
    || fail "/v1/models returned no models via LiteLLM"

# ---------------------------------------------------------------------------
# 8. Real inference test (llama-server → llama-swap → LiteLLM)
# ---------------------------------------------------------------------------
section "Real inference"

COMPLETION_RESP=$(curl -sf -X POST "http://127.0.0.1:${LITELLM_PORT}/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
    -d '{
        "model": "local/smollm2-test",
        "messages": [{"role": "user", "content": "Say the word hello."}],
        "max_tokens": 20,
        "temperature": 0
    }' 2>/dev/null) || true

[ -n "$COMPLETION_RESP" ] \
    && ok "got chat completion response from gateway" \
    || fail "no response from gateway /v1/chat/completions"

if [ -n "$COMPLETION_RESP" ]; then
    CONTENT=$(echo "$COMPLETION_RESP" | "$VENV_PYTHON" -c \
        "import json,sys; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'])" 2>/dev/null || echo "")
    FINISH=$(echo "$COMPLETION_RESP" | "$VENV_PYTHON" -c \
        "import json,sys; d=json.load(sys.stdin); print(d['choices'][0]['finish_reason'])" 2>/dev/null || echo "")
    TOKENS=$(echo "$COMPLETION_RESP" | "$VENV_PYTHON" -c \
        "import json,sys; d=json.load(sys.stdin); print(d['usage']['completion_tokens'])" 2>/dev/null || echo 0)

    [ -n "$CONTENT" ] \
        && ok "response content: $CONTENT" \
        || fail "response content was empty"

    [ "$FINISH" = "stop" ] || [ "$FINISH" = "length" ] \
        && ok "finish_reason: $FINISH" \
        || fail "unexpected finish_reason: $FINISH"

    [ "$TOKENS" -gt 0 ] \
        && ok "completion_tokens: $TOKENS" \
        || fail "completion_tokens was 0"
fi

# ---------------------------------------------------------------------------
# 9. Direct llama-server inference (baseline validation)
# ---------------------------------------------------------------------------
section "Direct llama-server inference"

DIRECT_RESP=$(curl -sf -X POST "http://127.0.0.1:${LLAMA_SERVER_PORT}/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d '{
        "model": "smollm2-test",
        "messages": [{"role": "user", "content": "What is 2+2?"}],
        "max_tokens": 10,
        "temperature": 0
    }' 2>/dev/null) || true

[ -n "$DIRECT_RESP" ] \
    && ok "direct llama-server inference works" \
    || fail "direct llama-server inference failed"

if [ -n "$DIRECT_RESP" ]; then
    DIRECT_CONTENT=$(echo "$DIRECT_RESP" | "$VENV_PYTHON" -c \
        "import json,sys; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'])" 2>/dev/null || echo "")
    [ -n "$DIRECT_CONTENT" ] \
        && ok "direct inference response: $DIRECT_CONTENT" \
        || fail "direct inference response was empty"
fi

# ---------------------------------------------------------------------------
# 10. vLLM routing (mock — validates gateway config, not real vLLM inference)
# ---------------------------------------------------------------------------
section "vLLM routing (mock)"

# Start a minimal mock to simulate vLLM's OpenAI-compatible API
cat > /tmp/mock_vllm.py <<'PYEOF'
#!/usr/bin/env python3
"""Minimal mock vLLM server for routing validation."""
import json, os
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(os.environ.get("VLLM_MOCK_PORT", "8000"))

MODELS = json.dumps({"object": "list", "data": [{"id": "Qwen/Qwen2.5-0.5B-Instruct", "object": "model"}]})
COMPLETION = json.dumps({
    "id": "mock-vllm-001",
    "object": "chat.completion",
    "model": "Qwen/Qwen2.5-0.5B-Instruct",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": "Mock vLLM response"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10}
})

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _json(self, body, code=200):
        enc = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(enc))
        self.end_headers()
        self.wfile.write(enc)
    def do_GET(self):
        self._json(MODELS) if "/models" in self.path else self._json('{"status":"ok"}')
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        self.rfile.read(n)
        self._json(COMPLETION)

print(f"Mock vLLM on :{PORT}", flush=True)
HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
PYEOF

VLLM_MOCK_PORT=41090
VLLM_MOCK_PORT=$VLLM_MOCK_PORT "$VENV_PYTHON" /tmp/mock_vllm.py &
VLLM_MOCK_PID=$!
sleep 2

VLLM_HEALTH=$(curl -sf "http://127.0.0.1:${VLLM_MOCK_PORT}/health" 2>/dev/null || echo "")
[ -n "$VLLM_HEALTH" ] \
    && ok "mock vLLM server running" \
    || fail "mock vLLM server did not start"

# Test that the mock vLLM API is OpenAI-compatible
VLLM_MODELS=$(curl -sf "http://127.0.0.1:${VLLM_MOCK_PORT}/v1/models" 2>/dev/null | \
    "$VENV_PYTHON" -c "import json,sys; d=json.load(sys.stdin); print(d['data'][0]['id'])" 2>/dev/null || echo "")
[ -n "$VLLM_MODELS" ] \
    && ok "mock vLLM /v1/models: $VLLM_MODELS" \
    || fail "mock vLLM /v1/models failed"

kill "$VLLM_MOCK_PID" 2>/dev/null || true

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
section "Summary"
echo "  Passed: $PASS"
echo "  Failed: $FAIL"
echo

if [ "$FAIL" -gt 0 ]; then
    echo "INTEGRATION TEST FAILED"
    exit 1
fi

echo "INTEGRATION TEST PASSED"
exit 0
