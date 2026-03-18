#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ACTION="${1:-help}"
TARGET="${2:-}"
if [ $# -gt 0 ]; then
  shift
fi
if [ $# -gt 0 ] && [ -n "$TARGET" ]; then
  shift
fi

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
  ./scripts/AUDiaLLMGateway.sh <action> [target] [args...]

Examples:
  ./scripts/AUDiaLLMGateway.sh install
  ./scripts/AUDiaLLMGateway.sh install stack
  ./scripts/AUDiaLLMGateway.sh install llama_cpp
  ./scripts/AUDiaLLMGateway.sh update
  ./scripts/AUDiaLLMGateway.sh update stack
  ./scripts/AUDiaLLMGateway.sh start
  ./scripts/AUDiaLLMGateway.sh stop gateway
  ./scripts/AUDiaLLMGateway.sh check
  ./scripts/AUDiaLLMGateway.sh validate
  ./scripts/AUDiaLLMGateway.sh test

Actions:
  install [release|stack|<component>]
  update [release|stack|<component>]
  start [stack|gateway|llamaswap]
  stop [stack|gateway|llamaswap]
  check [updates|status|health]
  validate [configs]
  test [routing]
  generate [configs]
  help

Defaults:
  install   -> release
  update    -> release
  start     -> stack
  stop      -> stack
  check     -> updates
  validate  -> configs
  test      -> routing
  generate  -> configs
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
  echo "Virtual environment not found. Run ./scripts/AUDiaLLMGateway.sh install stack first." >&2
  exit 1
}

invoke_install_stack() {
  if [ ! -d "$ROOT_DIR/.venv" ]; then
    "$PYTHON_BIN" -m venv "$ROOT_DIR/.venv"
  fi
  local venv_python
  venv_python="$(ensure_venv_python)"
  (cd "$ROOT_DIR" && "$venv_python" -m pip install --upgrade pip)
  (cd "$ROOT_DIR" && "$venv_python" -m pip install -r requirements.txt)
  (cd "$ROOT_DIR" && "$venv_python" -m src.launcher.process_manager --root "$ROOT_DIR" generate-configs)
}

invoke_update_stack() {
  local venv_python
  venv_python="$(ensure_venv_python)"
  (cd "$ROOT_DIR" && "$venv_python" -m pip install --upgrade pip)
  (cd "$ROOT_DIR" && "$venv_python" -m pip install --upgrade -r requirements.txt)
  (cd "$ROOT_DIR" && "$venv_python" -m src.launcher.process_manager --root "$ROOT_DIR" generate-configs)
}

invoke_release_installer() {
  local subcommand="$1"
  shift
  local venv_python
  venv_python="$(ensure_venv_python)"
  (cd "$ROOT_DIR" && "$venv_python" -m src.installer.release_installer "$subcommand" "$@")
}

invoke_process_manager() {
  local subcommand="$1"
  shift
  local venv_python
  venv_python="$(ensure_venv_python)"
  (cd "$ROOT_DIR" && "$venv_python" -m src.launcher.process_manager --root "$ROOT_DIR" "$subcommand" "$@")
}

case "$ACTION" in
  help)
    show_usage
    ;;
  install)
    case "${TARGET:-}" in
      ""|release)
        invoke_release_installer install-release "$@"
        ;;
      stack)
        invoke_install_stack
        ;;
      components)
        invoke_release_installer install-components --root "$ROOT_DIR" "$@"
        ;;
      firewall|nginx|llama_cpp|llama_swap|models|vllm)
        invoke_release_installer install-components --root "$ROOT_DIR" --component "$TARGET" "$@"
        ;;
      *)
        invoke_release_installer install-release --component "$TARGET" "$@"
        ;;
    esac
    ;;
  update)
    case "${TARGET:-}" in
      ""|release)
        invoke_release_installer update-release --root "$ROOT_DIR" "$@"
        ;;
      stack)
        invoke_update_stack
        ;;
      *)
        invoke_release_installer update-release --root "$ROOT_DIR" --component "$TARGET" "$@"
        ;;
    esac
    ;;
  start)
    case "${TARGET:-}" in
      ""|stack)
        invoke_process_manager start-all "$@"
        ;;
      gateway)
        invoke_process_manager start-gateway "$@"
        ;;
      llamaswap)
        invoke_process_manager start-llama-swap "$@"
        ;;
      *)
        echo "Unsupported start target '$TARGET'." >&2
        exit 1
        ;;
    esac
    ;;
  stop)
    case "${TARGET:-}" in
      ""|stack)
        invoke_process_manager stop-all "$@"
        ;;
      gateway)
        invoke_process_manager stop-gateway "$@"
        ;;
      llamaswap)
        invoke_process_manager stop-llama-swap "$@"
        ;;
      *)
        echo "Unsupported stop target '$TARGET'." >&2
        exit 1
        ;;
    esac
    ;;
  check)
    case "${TARGET:-}" in
      ""|updates)
        invoke_release_installer check-updates --root "$ROOT_DIR" "$@"
        ;;
      status)
        invoke_process_manager status "$@"
        ;;
      health)
        (cd "$ROOT_DIR" && "$(ensure_venv_python)" -m src.launcher.health --root "$ROOT_DIR" "$@")
        ;;
      *)
        echo "Unsupported check target '$TARGET'." >&2
        exit 1
        ;;
    esac
    ;;
  validate)
    case "${TARGET:-}" in
      ""|configs)
        invoke_release_installer validate-configs --root "$ROOT_DIR" "$@"
        ;;
      *)
        echo "Unsupported validate target '$TARGET'." >&2
        exit 1
        ;;
    esac
    ;;
  generate)
    case "${TARGET:-}" in
      ""|configs)
        invoke_process_manager generate-configs "$@"
        ;;
      *)
        echo "Unsupported generate target '$TARGET'." >&2
        exit 1
        ;;
    esac
    ;;
  test)
    case "${TARGET:-}" in
      ""|routing)
        if [[ " $* " == *" --all-models "* ]]; then
          (cd "$ROOT_DIR" && "$(ensure_venv_python)" -m src.launcher.router_test --root "$ROOT_DIR" "$@")
        else
          (cd "$ROOT_DIR" && "$(ensure_venv_python)" -m src.launcher.router_test --root "$ROOT_DIR" --all-models "$@")
        fi
        ;;
      *)
        echo "Unsupported test target '$TARGET'." >&2
        exit 1
        ;;
    esac
    ;;
  *)
    echo "Unknown action '$ACTION'. Run ./scripts/AUDiaLLMGateway.sh help for usage." >&2
    exit 1
    ;;
esac
