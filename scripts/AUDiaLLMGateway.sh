#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ACTION="${1:-help}"
TARGET="${2:-}"

# --- Helper: Ensure Docker Compose is available (lazy — only called for Docker actions) ---
docker_cmd() {
  if command -v docker-compose >/dev/null 2>&1; then
    echo "docker-compose"
  elif docker compose version >/dev/null 2>&1; then
    echo "docker compose"
  else
    echo "Error: docker-compose or 'docker compose' not found." >&2
    exit 1
  fi
}

# --- Helper: Resolve Python interpreter (venv preferred, system fallback) ---
python_cmd() {
  local venv_py="$ROOT_DIR/.venv/bin/python3"
  if [ -f "$venv_py" ]; then
    echo "$venv_py"
  elif command -v python3 >/dev/null 2>&1; then
    echo "python3"
  elif command -v python >/dev/null 2>&1; then
    echo "python"
  else
    echo "Error: Python not found. Install Python 3.9+ first." >&2
    exit 1
  fi
}

show_usage() {
  cat <<'EOF'
AUDia LLM Gateway - Management Script

Usage:
  ./scripts/AUDiaLLMGateway.sh <action> [target] [args...]

Native (non-Docker) actions:
  install stack         - Create Python venv and install pip dependencies
  install components    - Download llama-swap and llama.cpp binaries
  install firewall      - Open gateway service ports in the system firewall
  generate              - Generate runtime configs from current stack config
  validate              - Validate project and local config layering
  start                 - Start llama-swap + LiteLLM gateway (native)
  stop                  - Stop gateway and llama-swap (native)
  status                - Show runtime process status (native)

Docker actions:
  docker start [stack]  - Start the entire gateway stack via Docker Compose (detached)
  docker stop [stack]   - Stop and remove the gateway containers
  docker restart        - Restart the gateway stack
  docker update         - Pull latest images and restart
  docker status         - Show running containers and their status
  docker health         - Probe API endpoints for LiteLLM and llama-swap
  docker logs [svc]     - View logs (e.g. ./scripts/AUDiaLLMGateway.sh docker logs gateway)

Shortcuts (Docker):
  start                 - Alias for 'docker start' when Docker Compose is available
  stop                  - Alias for 'docker stop' when Docker Compose is available
  check status          - Show Docker Compose container status
  check health          - Probe gateway health via docker exec
  check logs [svc]      - View logs via Docker Compose

Other:
  help                  - Show this help message

Examples:
  ./scripts/AUDiaLLMGateway.sh install stack
  ./scripts/AUDiaLLMGateway.sh install components
  ./scripts/AUDiaLLMGateway.sh generate
  ./scripts/AUDiaLLMGateway.sh docker start
  ./scripts/AUDiaLLMGateway.sh check health
EOF
}

case "$ACTION" in
  help)
    show_usage
    ;;

  # ---------------------------------------------------------------------------
  # Native install commands
  # ---------------------------------------------------------------------------
  install)
    PYTHON="$(python_cmd)"
    case "${TARGET:-}" in
      stack)
        echo ">>> Installing Python venv and dependencies..."
        # Bootstrap: create venv and install deps without importing project code
        # (project modules are not importable until after pip install completes)
        "$PYTHON" -m venv "$ROOT_DIR/.venv"
        "$ROOT_DIR/.venv/bin/pip" install --upgrade pip
        "$ROOT_DIR/.venv/bin/pip" install -r "$ROOT_DIR/requirements.txt"
        ;;
      components)
        echo ">>> Downloading llama-swap and llama.cpp binaries..."
        (cd "$ROOT_DIR" && "$PYTHON" -m src.installer.release_installer install-components --root .)
        ;;
      firewall)
        echo ">>> Opening firewall ports..."
        (cd "$ROOT_DIR" && "$PYTHON" -m src.installer.release_installer install-firewall --root .)
        ;;
      *)
        echo "Unknown install target '${TARGET:-}'. Use: stack, components, firewall" >&2
        exit 1
        ;;
    esac
    ;;

  # ---------------------------------------------------------------------------
  # Config generation and validation (native Python, no Docker required)
  # ---------------------------------------------------------------------------
  generate)
    echo ">>> Generating runtime configurations..."
    PYTHON="$(python_cmd)"
    (cd "$ROOT_DIR" && "$PYTHON" -m src.launcher.process_manager --root . generate-configs)
    ;;

  validate)
    echo ">>> Validating config layering..."
    PYTHON="$(python_cmd)"
    (cd "$ROOT_DIR" && "$PYTHON" -m src.installer.release_installer validate-configs --root .)
    ;;

  # ---------------------------------------------------------------------------
  # Native process management
  # ---------------------------------------------------------------------------
  start)
    PYTHON="$(python_cmd)"
    (cd "$ROOT_DIR" && "$PYTHON" -m src.launcher.process_manager --root . start-all)
    ;;

  stop)
    PYTHON="$(python_cmd)"
    (cd "$ROOT_DIR" && "$PYTHON" -m src.launcher.process_manager --root . stop-all)
    ;;

  status)
    PYTHON="$(python_cmd)"
    (cd "$ROOT_DIR" && "$PYTHON" -m src.launcher.process_manager --root . status)
    ;;

  # ---------------------------------------------------------------------------
  # Docker management commands (docker_cmd() called lazily here)
  # ---------------------------------------------------------------------------
  docker)
    DOCKER_COMPOSE="$(docker_cmd)"
    case "${TARGET:-}" in
      start)
        echo ">>> Starting AUDia LLM Gateway stack (Docker)..."
        (cd "$ROOT_DIR" && $DOCKER_COMPOSE up -d)
        ;;
      stop)
        echo ">>> Stopping stack (Docker)..."
        (cd "$ROOT_DIR" && $DOCKER_COMPOSE down)
        ;;
      restart)
        echo ">>> Restarting stack (Docker)..."
        (cd "$ROOT_DIR" && $DOCKER_COMPOSE restart)
        ;;
      update)
        echo ">>> Pulling latest images from Docker Hub..."
        (cd "$ROOT_DIR" && $DOCKER_COMPOSE pull)
        echo ">>> Restarting updated stack..."
        (cd "$ROOT_DIR" && $DOCKER_COMPOSE up -d)
        ;;
      status|"")
        (cd "$ROOT_DIR" && $DOCKER_COMPOSE ps)
        ;;
      health)
        echo ">>> Probing internal health endpoints..."
        (cd "$ROOT_DIR" && docker exec audia-gateway python3 -m src.launcher.health --root .)
        ;;
      logs)
        shift 2
        (cd "$ROOT_DIR" && $DOCKER_COMPOSE logs -f "$@")
        ;;
      *)
        echo "Unknown docker target '${TARGET:-}'. Use: start, stop, restart, update, status, health, logs" >&2
        exit 1
        ;;
    esac
    ;;

  # ---------------------------------------------------------------------------
  # Legacy 'check' alias (Docker)
  # ---------------------------------------------------------------------------
  check)
    DOCKER_COMPOSE="$(docker_cmd)"
    case "${TARGET:-}" in
      status|"")
        (cd "$ROOT_DIR" && $DOCKER_COMPOSE ps)
        ;;
      health)
        echo ">>> Probing internal health endpoints..."
        (cd "$ROOT_DIR" && docker exec audia-gateway python3 -m src.launcher.health --root .)
        ;;
      logs)
        shift 1
        shift 1
        (cd "$ROOT_DIR" && $DOCKER_COMPOSE logs -f "$@")
        ;;
      *)
        echo "Unsupported check target '$TARGET'. Try: status, health, logs" >&2
        exit 1
        ;;
    esac
    ;;

  # ---------------------------------------------------------------------------
  # Test (Docker exec)
  # ---------------------------------------------------------------------------
  test)
    echo ">>> Running routing tests through the gateway..."
    (cd "$ROOT_DIR" && docker exec audia-gateway python3 -m src.launcher.router_test --root . --all-models)
    ;;

  update)
    DOCKER_COMPOSE="$(docker_cmd)"
    echo ">>> Pulling latest images from Docker Hub..."
    (cd "$ROOT_DIR" && $DOCKER_COMPOSE pull)
    echo ">>> Rebuilding local backend images..."
    (cd "$ROOT_DIR" && $DOCKER_COMPOSE build --pull)
    echo ">>> Restarting updated stack..."
    (cd "$ROOT_DIR" && $DOCKER_COMPOSE up -d)
    ;;

  *)
    echo "Unknown action '$ACTION'. Run ./scripts/AUDiaLLMGateway.sh help for usage." >&2
    exit 1
    ;;
esac
