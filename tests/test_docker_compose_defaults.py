from pathlib import Path

import yaml


def _load_compose_services() -> dict:
    root = Path(__file__).resolve().parents[1]
    compose_path = root / "docker" / "compose" / "docker-compose.yml"
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


def test_compose_vllm_does_not_hardcode_visible_devices() -> None:
    # GPU visible-device selection moved to models.override.yaml under the
    # vllm deployment profile (visible_devices key).  docker-compose must not
    # set ROCR_VISIBLE_DEVICES / HIP_VISIBLE_DEVICES to avoid overriding the
    # config-system values and to keep deployment concerns separate.
    services = _load_compose_services()
    vllm_env = _env_map(services["llm-server-vllm"])

    assert "ROCR_VISIBLE_DEVICES" not in vllm_env, (
        "ROCR_VISIBLE_DEVICES belongs in models.override.yaml, not docker-compose"
    )
    assert "HIP_VISIBLE_DEVICES" not in vllm_env, (
        "HIP_VISIBLE_DEVICES belongs in models.override.yaml, not docker-compose"
    )


def test_compose_persists_llamacpp_runtime_root_to_host_path() -> None:
    services = _load_compose_services()
    volumes = services["llm-server-llamacpp"].get("volumes", [])

    assert any(":/app/runtime-root" in str(volume) for volume in volumes)
