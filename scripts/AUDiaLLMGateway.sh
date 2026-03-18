#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ACTION="${1:-help}"
TARGET="${2:-}"

# --- Helper: Ensure Docker Compose is available ---
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

DOCKER_COMPOSE="$(docker_cmd)"

show_usage() {
  cat <<'EOF'
AUDia LLM Gateway - Docker Management Script

Usage:
  ./scripts/AUDiaLLMGateway.sh <action> [target] [args...]

Actions:
  start [stack]     - Start the entire gateway stack (detached)
  stop [stack]      - Stop and remove the gateway containers
  restart [stack]   - Restart the gateway stack
  update [stack]    - Pull latest images and rebuild local backends
  generate [configs]- Force regeneration of all service configurations
  check status      - Show running containers and their status
  check health      - Probe API endpoints for LiteLLM and llama-swap
  check logs [svc]  - View logs (e.g., ./scripts/AUDiaLLMGateway.sh check logs gateway)
  test              - Run end-to-end routing tests
  help              - Show this help message

Examples:
  ./scripts/AUDiaLLMGateway.sh start
  ./scripts/AUDiaLLMGateway.sh update
  ./scripts/AUDiaLLMGateway.sh check health
EOF
}

case "$ACTION" in
  help)
    show_usage
    ;;

  start)
    echo ">>> Starting AUDia LLM Gateway stack..."
    (cd "$ROOT_DIR" && $DOCKER_COMPOSE up -d)
    ;;

  stop)
    echo ">>> Stopping stack..."
    (cd "$ROOT_DIR" && $DOCKER_COMPOSE down)
    ;;

  restart)
    echo ">>> Restarting stack..."
    (cd "$ROOT_DIR" && $DOCKER_COMPOSE restart)
    ;;

  update)
    echo ">>> Pulling latest images from Docker Hub..."
    (cd "$ROOT_DIR" && $DOCKER_COMPOSE pull)
    echo ">>> Rebuilding local backend images..."
    (cd "$ROOT_DIR" && $DOCKER_COMPOSE build --pull)
    echo ">>> Restarting updated stack..."
    (cd "$ROOT_DIR" && $DOCKER_COMPOSE up -d)
    ;;

  generate)
    echo ">>> Manually triggering configuration regeneration..."
    (cd "$ROOT_DIR" && docker exec audia-gateway python3 -m src.launcher.process_manager --root . generate-configs)
    ;;

  check)
    case "${TARGET:-}" in
      status|"")
        (cd "$ROOT_DIR" && $DOCKER_COMPOSE ps)
        ;;
      health)
        echo ">>> Probing internal health endpoints..."
        (cd "$ROOT_DIR" && docker exec audia-gateway python3 -m src.launcher.health --root .)
        ;;
      logs)
        shift 1 # Remove 'check'
        shift 1 # Remove 'logs'
        (cd "$ROOT_DIR" && $DOCKER_COMPOSE logs -f "$@")
        ;;
      *)
        echo "Unsupported check target '$TARGET'. Try: status, health, logs" >&2
        exit 1
        ;;
    esac
    ;;

  test)
    echo ">>> Running routing tests through the gateway..."
    (cd "$ROOT_DIR" && docker exec audia-gateway python3 -m src.launcher.router_test --root . --all-models)
    ;;

  *)
    echo "Unknown action '$ACTION'. Run ./scripts/AUDiaLLMGateway.sh help for usage." >&2
    exit 1
    ;;
esac
