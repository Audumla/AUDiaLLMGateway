from pathlib import Path

from src.launcher.config_loader import LlamaSwapRuntime
from src.launcher.process_manager import llama_swap_command


def test_llama_swap_command_uses_serve_and_addr() -> None:
    root = Path("/workspace")
    runtime = LlamaSwapRuntime(
        executable="llama-swap",
        host="127.0.0.1",
        port=41080,
        project_config_path="config/project/llama-swap.base.yaml",
        local_override_path="config/local/llama-swap.override.yaml",
        generated_config_path="config/generated/llama-swap/llama-swap.generated.yaml",
        health_paths=["/health", "/v1/models"],
        extra_args=["--verbose"],
    )

    command = llama_swap_command(root, runtime)

    assert command == [
        "llama-swap",
        "-config",
        str((root / runtime.generated_config_path).resolve()),
        "-listen",
        "127.0.0.1:41080",
        "-watch-config",
        "--verbose",
    ]


def test_provision_runtime_launches_llama_swap_by_default() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "scripts" / "provision-runtime.sh").read_text(encoding="utf-8")

    assert 'BACKEND_RUNTIME_CATALOG_PATH="${BACKEND_RUNTIME_CATALOG_PATH:-/app/config/backend-runtime.catalog.json}"' in script
    assert "load_runtime_catalog" in script
    assert 'while [ ! -s "$DEFAULT_SWAP_CONFIG" ]; do' in script
    assert 'exec llama-swap -config "$DEFAULT_SWAP_CONFIG" -listen "$DEFAULT_SWAP_ADDR" -watch-config' in script


def test_unified_backend_image_installs_llama_swap() -> None:
    root = Path(__file__).resolve().parents[1]
    backend_base = (root / "docker" / "Dockerfile.backend-base").read_text(encoding="utf-8")
    dockerfile = (root / "docker" / "Dockerfile.unified-backend").read_text(encoding="utf-8")

    assert "/usr/local/bin/llama-swap" in backend_base
    assert "api.github.com/repos/mostlygeek/llama-swap/releases/latest" in backend_base
    assert "ARG BACKEND_BASE_IMAGE=" in dockerfile
    assert "FROM ${BACKEND_BASE_IMAGE}" in dockerfile


def test_gateway_image_uses_publishable_base() -> None:
    root = Path(__file__).resolve().parents[1]
    gateway_base = (root / "docker" / "Dockerfile.gateway-base").read_text(encoding="utf-8")
    dockerfile = (root / "docker" / "Dockerfile.gateway").read_text(encoding="utf-8")

    assert "COPY requirements.txt ." in gateway_base
    assert "pip install --no-cache-dir --prefix=/install -r requirements.txt" in gateway_base
    assert "ARG GATEWAY_BASE_IMAGE=" in dockerfile
    assert "FROM ${GATEWAY_BASE_IMAGE}" in dockerfile
