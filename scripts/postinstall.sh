#!/bin/bash
# Initialize the stack after installation.
# Intentionally no "set -e" — component download failures are non-fatal;
# critical steps use explicit || exit 1.

cd /opt/AUDiaLLMGateway

# Ensure scripts are executable (fix for RPM packaging)
chmod +x scripts/*.sh scripts/*.ps1 scripts/*.cmd 2>/dev/null || true

# Ensure runtime directories exist
mkdir -p state config/local config/data/backend-runtime config/data/backend-build

# config/local/ is a protected path — updates never overwrite it.
# Make it and its files editable by all local users (home-lab default).
chmod 777 config/local

# Seed the service environment file (contains the LiteLLM master key).
# Keep it root-readable only since it holds credentials.
if [ ! -f config/local/env ]; then
    cat > config/local/env <<'EOF'
# AUDia LLM Gateway — service environment overrides.
# Loaded by the systemd unit (EnvironmentFile). Changes take effect on
# the next 'systemctl restart audia-gateway'.
LITELLM_MASTER_KEY=sk-local-dev
EOF
    chmod 600 config/local/env
fi

# Seed a base stack override file so users can customise ports and hosts
# without editing the project-managed defaults. World-writable so any
# local user can edit it without sudo.
if [ ! -f config/local/stack.override.yaml ]; then
    cat > config/local/stack.override.yaml <<'EOF'
# AUDia LLM Gateway — local stack overrides.
# Values here are merged on top of config/project/stack.base.yaml.
# This file is preserved across updates. Edit freely.
# After editing run: ./scripts/AUDiaLLMGateway.sh generate
#                then: systemctl restart audia-gateway
#
# --- Common customisations ---
#
# Change the LiteLLM gateway port and bind address:
# network:
#   public_host: 0.0.0.0
#   services:
#     litellm:
#       host: 0.0.0.0
#       port: 4000
#
# Change the llama-swap internal port:
# network:
#   services:
#     llama_swap:
#       port: 41080
#
# Enable nginx reverse proxy:
# reverse_proxy:
#   nginx:
#     enabled: true
EOF
    chmod 666 config/local/stack.override.yaml
fi

# Seed llama-swap substrate overrides
if [ ! -f config/local/llama-swap.override.yaml ]; then
    cat > config/local/llama-swap.override.yaml <<'EOF'
# AUDia LLM Gateway — llama-swap substrate overrides.
# Merged on top of config/project/llama-swap.base.yaml.
# After editing run: ./scripts/AUDiaLLMGateway.sh generate
#               then: systemctl restart audia-gateway
#
# --- Global settings ---
#
# healthCheckTimeout: 300   # seconds to wait for llama-server to start
# logLevel: info            # debug | info | warn | error
#
# --- Backend binary macros ---
# By default all macros resolve to the installed 'llama-server' binary.
# Use backend-specific macros to point at specific builds if you have multiple
# installed. Use 'AUDiaLLMGateway.sh install components' to install binaries.
#
# macros:
#   llama-server-cpu:    "llama-server-cpu"       # explicit CPU build
#   llama-server-cuda:   "llama-server-cuda"      # explicit CUDA build
#   llama-server-rocm:   "llama-server-rocm"      # explicit ROCm build
#   llama-server-vulkan: "llama-server-vulkan"    # explicit Vulkan build
#   model-path:          "--model models/gguf"
#   mmproj-path:         "--mmproj models/gguf"
#
# --- Per-model backend selection ---
# Keep LLAMA_BACKEND=auto so the runtime provisions separate ROCm and Vulkan
# directories, then
# set executable_macro in config/local/models.override.yaml to route
# specific models to specific backends:
#   executable_macro: llama-server-rocm     # run this model on ROCm
#   executable_macro: llama-server-vulkan   # run this model on Vulkan
EOF
    chmod 666 config/local/llama-swap.override.yaml
fi

# Seed model overrides
if [ ! -f config/local/models.override.yaml ]; then
    cat > config/local/models.override.yaml <<'EOF'
# AUDia LLM Gateway — local model overrides.
# Add or override model definitions here.
# After editing run: ./scripts/AUDiaLLMGateway.sh generate
#               then: systemctl restart audia-gateway
#
# Example — add a local GGUF model:
# models:
#   - name: my-model
#     model_file: MyModel/my-model-Q4_K_M.gguf
#     context_size: 4096
#     # Optional: pin to a specific backend binary
#     # executable_macro: llama-server-rocm
EOF
    chmod 666 config/local/models.override.yaml
fi

# Seed backend runtime variant overrides (separate from model catalog).
if [ ! -f config/local/backend-runtime.override.yaml ]; then
    cat > config/local/backend-runtime.override.yaml <<'EOF'
# AUDia LLM Gateway — backend runtime variant overrides.
# Merged on top of config/project/backend-runtime.base.yaml.
# After editing run: ./scripts/AUDiaLLMGateway.sh generate
#               then: systemctl restart audia-gateway
#
# variants:
#   rocm-b8429:
#     backend: rocm
#     macro: llama-server-rocm-b8429
#     version: b8429
#     runtime_subdir: rocm/b8429
#
#   vulkan-custom-url:
#     backend: vulkan
#     macro: llama-server-vulkan-custom
#     source_type: direct_url
#     download_url: https://example.com/llama-vulkan-custom.tar.gz
#     archive_type: tar.gz
#     runtime_subdir: vulkan/custom
#
#   rocm-built-from-git:
#     backend: rocm
#     macro: llama-server-rocm-git
#     source_type: git
#     git_url: https://github.com/ggml-org/llama.cpp.git
#     git_ref: master
#     configure_command: cmake -S . -B build -DLLAMA_BUILD_SERVER=ON -DGGML_HIPBLAS=ON -DCMAKE_BUILD_TYPE=Release
#     build_command: cmake --build build --config Release --parallel
#     source_subdir: .
#     build_root_subdir: rocm/git-main
#     build_env:
#       CMAKE_BUILD_PARALLEL_LEVEL: "8"
#     pre_configure_command: cmake --version
#     binary_glob: build/bin/llama-server
#     library_glob: build/bin/*.so*
#     apt_packages:
#       - git
#       - cmake
#       - build-essential
EOF
    chmod 666 config/local/backend-runtime.override.yaml
fi

# Install Python venv and pip dependencies (hard failure — nothing works without this)
./scripts/AUDiaLLMGateway.sh install stack \
    || { echo "[error] Python stack install failed"; exit 1; }

# Download llama-swap and llama.cpp binaries (soft failure — user can retry with
# './scripts/AUDiaLLMGateway.sh install components')
./scripts/AUDiaLLMGateway.sh install components \
    || echo "[warn] Component install had errors — run 'AUDiaLLMGateway.sh install components' to retry"

# Generate runtime configs from installed state (hard failure)
./scripts/AUDiaLLMGateway.sh generate \
    || { echo "[error] Config generation failed"; exit 1; }

# Open firewall ports for any service ports that are bound to a non-loopback
# address. Skipped silently when no recognised firewall manager is present or
# when all services are bound to loopback only.
./scripts/AUDiaLLMGateway.sh install firewall \
    || echo "[warn] Firewall setup had errors — run 'AUDiaLLMGateway.sh install firewall' to retry, or open ports manually"

# Register and enable the systemd service
systemctl daemon-reload
systemctl enable audia-gateway

# Start the service now so the install is immediately operational.
# A start failure here does not abort the package install — the user can
# investigate with 'systemctl status audia-gateway'.
systemctl start audia-gateway \
    || echo "[warn] Service start failed — check 'systemctl status audia-gateway'"
