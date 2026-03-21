from pathlib import Path

import yaml


def _load_compose_services() -> dict:
    root = Path(__file__).resolve().parents[1]
    compose_path = root / "docker-compose.yml"
    compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    return compose.get("services", {})


def _env_map(service: dict) -> dict[str, str]:
    env = service.get("environment", {})
    if isinstance(env, dict):
        return {str(k): str(v) for k, v in env.items()}
    result: dict[str, str] = {}
    if isinstance(env, list):
        for item in env:
            item_str = str(item)
            if "=" not in item_str:
                continue
            key, value = item_str.split("=", 1)
            result[key] = value
    return result


def test_compose_wires_default_postgres_for_gateway_auth() -> None:
    services = _load_compose_services()

    assert "llm-db-postgres" in services
    assert "llm-gateway" in services

    gateway_env = _env_map(services["llm-gateway"])
    assert "DATABASE_URL" in gateway_env
    assert "@llm-db-postgres:5432/" in gateway_env["DATABASE_URL"]
    assert "llm-db-postgres" in services["llm-gateway"].get("depends_on", {})


def test_compose_wires_vllm_visible_devices_for_amd_runtime() -> None:
    services = _load_compose_services()
    vllm = services["llm-server-vllm"]
    vllm_env = _env_map(vllm)

    assert vllm_env.get("ROCR_VISIBLE_DEVICES") == "${VLLM_VISIBLE_DEVICES:-0}"
    assert vllm_env.get("HIP_VISIBLE_DEVICES") == "${VLLM_VISIBLE_DEVICES:-0}"


def test_compose_persists_llamacpp_runtime_root_to_host_path() -> None:
    services = _load_compose_services()
    volumes = services["llm-server-llamacpp"].get("volumes", [])

    assert any(":/app/runtime-root" in str(volume) for volume in volumes)
