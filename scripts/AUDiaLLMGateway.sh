#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMMAND="${1:-help}"
shift || true

python_cmd() {
  if command -v python3 >/dev/null 2>&1; then
    echo python3
    return
  fi
  if command -v python >/dev/null 2>&1; then
    echo python
    return
  fi
  echo "Python was not found in PATH." >&2
  exit 1
}

show_usage() {
  cat <<'EOF'
Usage:
  ./scripts/AUDiaLLMGateway.sh <command> [args...]

Commands:
  install-release  Install from a GitHub release archive
  update-release   Update this installation from GitHub releases
  check-updates    Check upstream release availability
  validate-configs Validate layered project/local config
  install-stack    Create .venv, install Python deps, and generate configs
  update-stack     Upgrade Python deps and refresh generated configs
  generate-configs Generate llama-swap, LiteLLM, and MCP client configs
  start-stack      Start llama-swap and LiteLLM
  stop-stack       Stop llama-swap and LiteLLM
  start-gateway    Start LiteLLM only
  stop-gateway     Stop LiteLLM only
  start-llamaswap  Start llama-swap only
  stop-llamaswap   Stop llama-swap only
  status           Show runtime process status
  healthcheck      Run health checks
  test-routing     Run end-to-end routing tests
  help             Show this message
EOF
}

PYTHON_BIN="$(python_cmd)"

run_python_module() {
  "$PYTHON_BIN" -m "$@"
}

ensure_venv_python() {
  if [ -x "$ROOT_DIR/.venv/bin/python3" ]; then
    echo "$ROOT_DIR/.venv/bin/python3"
    return
  fi
  if [ -x "$ROOT_DIR/.venv/bin/python" ]; then
    echo "$ROOT_DIR/.venv/bin/python"
    return
  fi
  echo "Virtual environment not found. Run ./scripts/AUDiaLLMGateway.sh install-stack first." >&2
  exit 1
}

case "$COMMAND" in
  help)
    show_usage
    ;;
  install-release)
    (cd "$ROOT_DIR" && run_python_module src.installer.release_installer install-release "$@")
    ;;
  update-release)
    (cd "$ROOT_DIR" && run_python_module src.installer.release_installer update-release --root "$ROOT_DIR" "$@")
    ;;
  check-updates)
    (cd "$ROOT_DIR" && run_python_module src.installer.release_installer check-updates --root "$ROOT_DIR" "$@")
    ;;
  validate-configs)
    (cd "$ROOT_DIR" && run_python_module src.installer.release_installer validate-configs --root "$ROOT_DIR" "$@")
    ;;
  install-stack)
    if [ ! -d "$ROOT_DIR/.venv" ]; then
      "$PYTHON_BIN" -m venv "$ROOT_DIR/.venv"
    fi
    VENV_PYTHON="$(ensure_venv_python)"
    (cd "$ROOT_DIR" && "$VENV_PYTHON" -m pip install --upgrade pip)
    (cd "$ROOT_DIR" && "$VENV_PYTHON" -m pip install -r requirements.txt)
    (cd "$ROOT_DIR" && "$VENV_PYTHON" -m src.launcher.process_manager --root "$ROOT_DIR" generate-configs)
    ;;
  update-stack)
    VENV_PYTHON="$(ensure_venv_python)"
    (cd "$ROOT_DIR" && "$VENV_PYTHON" -m pip install --upgrade pip)
    (cd "$ROOT_DIR" && "$VENV_PYTHON" -m pip install --upgrade -r requirements.txt)
    (cd "$ROOT_DIR" && "$VENV_PYTHON" -m src.launcher.process_manager --root "$ROOT_DIR" generate-configs)
    ;;
  generate-configs)
    (cd "$ROOT_DIR" && run_python_module src.launcher.process_manager --root "$ROOT_DIR" generate-configs "$@")
    ;;
  start-stack)
    (cd "$ROOT_DIR" && run_python_module src.launcher.process_manager --root "$ROOT_DIR" start-all "$@")
    ;;
  stop-stack)
    (cd "$ROOT_DIR" && run_python_module src.launcher.process_manager --root "$ROOT_DIR" stop-all "$@")
    ;;
  start-gateway)
    (cd "$ROOT_DIR" && run_python_module src.launcher.process_manager --root "$ROOT_DIR" start-gateway "$@")
    ;;
  stop-gateway)
    (cd "$ROOT_DIR" && run_python_module src.launcher.process_manager --root "$ROOT_DIR" stop-gateway "$@")
    ;;
  start-llamaswap)
    (cd "$ROOT_DIR" && run_python_module src.launcher.process_manager --root "$ROOT_DIR" start-llama-swap "$@")
    ;;
  stop-llamaswap)
    (cd "$ROOT_DIR" && run_python_module src.launcher.process_manager --root "$ROOT_DIR" stop-llama-swap "$@")
    ;;
  status)
    (cd "$ROOT_DIR" && run_python_module src.launcher.process_manager --root "$ROOT_DIR" status "$@")
    ;;
  healthcheck)
    (cd "$ROOT_DIR" && run_python_module src.launcher.health --root "$ROOT_DIR" "$@")
    ;;
  test-routing)
    if [[ " $* " == *" --all-models "* ]]; then
      (cd "$ROOT_DIR" && run_python_module src.launcher.router_test --root "$ROOT_DIR" "$@")
    else
      (cd "$ROOT_DIR" && run_python_module src.launcher.router_test --root "$ROOT_DIR" --all-models "$@")
    fi
    ;;
  *)
    echo "Unknown command '$COMMAND'. Run ./scripts/AUDiaLLMGateway.sh help for usage." >&2
    exit 1
    ;;
esac
