#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"

if [ -t 1 ]; then
    BOLD='\033[1m'; RESET='\033[0m'; GREEN='\033[32m'; YELLOW='\033[33m'; CYAN='\033[36m'
else
    BOLD=''; RESET=''; GREEN=''; YELLOW=''; CYAN=''
fi

header() { echo -e "\n${BOLD}${CYAN}=== $* ===${RESET}"; }
ok()     { echo -e "  ${GREEN}✔${RESET}  $*"; }
warn()   { echo -e "  ${YELLOW}⚠${RESET}  $*"; }

prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local value
    read -r -p "$prompt [$default]: " value || true
    if [ -z "${value:-}" ]; then
        printf '%s\n' "$default"
    else
        printf '%s\n' "$value"
    fi
}

prompt_yes_no() {
    local prompt="$1"
    local default="$2"
    local raw answer
    if [ "$default" = "true" ]; then
        raw="Y/n"
    else
        raw="y/N"
    fi
    read -r -p "$prompt [$raw]: " answer || true
    answer="${answer:-}"
    case "$(printf '%s' "$answer" | tr '[:upper:]' '[:lower:]')" in
        y|yes) printf 'true\n' ;;
        n|no) printf 'false\n' ;;
        "") printf '%s\n' "$default" ;;
        *) printf '%s\n' "$default" ;;
    esac
}

set_env_value() {
    local key="$1"
    local value="$2"
    if [ ! -f "$ENV_FILE" ]; then
        cp "$ROOT_DIR/config/env.example" "$ENV_FILE"
    fi
    if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
        sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
    else
        printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
    fi
}

mkdir -p "$ROOT_DIR/config/data/backend-runtime" "$ROOT_DIR/models" "$ROOT_DIR/models-hf"

header "Hardware Detection"

HAS_NVIDIA=false
HAS_AMD=false
HAS_VULKAN=false

if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
    HAS_NVIDIA=true
    ok "NVIDIA GPU detected"
fi

if command -v rocm-smi >/dev/null 2>&1 && rocm-smi --showproductname >/dev/null 2>&1; then
    HAS_AMD=true
    ok "AMD GPU detected via rocm-smi"
elif [ -e /dev/kfd ]; then
    HAS_AMD=true
    ok "AMD GPU detected via /dev/kfd"
fi

if command -v vulkaninfo >/dev/null 2>&1 && vulkaninfo --summary >/dev/null 2>&1; then
    HAS_VULKAN=true
    ok "Vulkan runtime detected"
elif lspci 2>/dev/null | grep -qiE 'vga|display|3d'; then
    HAS_VULKAN=true
    ok "Display adapter detected; Vulkan may be available"
fi

DEFAULT_BACKEND="cpu"
DEFAULT_ENABLE_VLLM="false"
DEFAULT_VLLM_IMAGE="audumla/audia-llm-gateway-vllm:latest"
DEFAULT_LLAMA_VERSION="latest"

if $HAS_NVIDIA; then
    DEFAULT_BACKEND="cuda"
    DEFAULT_ENABLE_VLLM="true"
elif $HAS_AMD; then
    DEFAULT_BACKEND="vulkan"
    DEFAULT_ENABLE_VLLM="true"
    DEFAULT_VLLM_IMAGE="vllm/vllm-openai-rocm:latest"
    DEFAULT_LLAMA_VERSION="b8429"
elif $HAS_VULKAN; then
    DEFAULT_BACKEND="vulkan"
fi

header "Docker Setup"

BACKEND=$(prompt_with_default "Primary llama.cpp backend (cpu/cuda/rocm/vulkan/auto)" "$DEFAULT_BACKEND")
ENABLE_VLLM=$(prompt_yes_no "Enable vLLM profile support now" "$DEFAULT_ENABLE_VLLM")
MODEL_ROOT=$(prompt_with_default "GGUF model root" "./models")
MODEL_HF_ROOT=$(prompt_with_default "vLLM Hugging Face cache root" "./models-hf")
BACKEND_RUNTIME_ROOT=$(prompt_with_default "Visible llama.cpp runtime base root" "./config/data/backend-runtime")
LLAMA_VERSION=$(prompt_with_default "llama.cpp release tag" "$DEFAULT_LLAMA_VERSION")
GATEWAY_PORT=$(prompt_with_default "LiteLLM gateway port" "4000")
NGINX_PORT=$(prompt_with_default "nginx port" "8080")
VLLM_PORT=$(prompt_with_default "vLLM port" "41090")
LITELLM_MASTER_KEY=$(prompt_with_default "LiteLLM master key" "sk-local-dev")

VLLM_MODEL_DEFAULT="Qwen/Qwen3-0.6B"
if [ "$ENABLE_VLLM" != "true" ]; then
    VLLM_IMAGE="$DEFAULT_VLLM_IMAGE"
else
    VLLM_IMAGE=$(prompt_with_default "vLLM image" "$DEFAULT_VLLM_IMAGE")
fi
VLLM_MODEL=$(prompt_with_default "Default vLLM model" "$VLLM_MODEL_DEFAULT")

header "Writing .env"

set_env_value "LITELLM_MASTER_KEY" "$LITELLM_MASTER_KEY"
set_env_value "MODEL_ROOT" "$MODEL_ROOT"
set_env_value "MODEL_HF_ROOT" "$MODEL_HF_ROOT"
set_env_value "BACKEND_RUNTIME_ROOT" "$BACKEND_RUNTIME_ROOT"
set_env_value "LLAMA_BACKEND" "$BACKEND"
set_env_value "LLAMA_VERSION" "$LLAMA_VERSION"
set_env_value "AUDIA_ENABLE_VLLM" "$ENABLE_VLLM"
set_env_value "VLLM_IMAGE" "$VLLM_IMAGE"
set_env_value "VLLM_MODEL" "$VLLM_MODEL"
set_env_value "VLLM_GPU_MEM" "1.0"
set_env_value "VLLM_MAX_LEN" "4096"
set_env_value "GATEWAY_PORT" "$GATEWAY_PORT"
set_env_value "NGINX_PORT" "$NGINX_PORT"
set_env_value "VLLM_PORT" "$VLLM_PORT"

mkdir -p \
    "$ROOT_DIR/${MODEL_ROOT#./}" \
    "$ROOT_DIR/${MODEL_HF_ROOT#./}" \
    "$ROOT_DIR/${BACKEND_RUNTIME_ROOT#./}"

ok "Wrote $ENV_FILE"
ok "Created visible runtime/cache/model directories if missing"

header "Summary"
echo "  Compose services: llm-gateway, llm-server-llamacpp, llm-server-vllm, llm-config-watcher"
echo "  llama.cpp backend: $BACKEND"
echo "  llama.cpp runtime base: $BACKEND_RUNTIME_ROOT"
echo "  vLLM enabled: $ENABLE_VLLM"
echo "  vLLM image: $VLLM_IMAGE"

echo
echo "Next steps:"
echo "  docker compose pull"
echo "  docker compose up -d"
echo
echo "If you want to force a fresh runtime reprovision later:"
echo "  rm -rf ${BACKEND_RUNTIME_ROOT%/}/*"
