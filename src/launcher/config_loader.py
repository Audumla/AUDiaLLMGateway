from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


@dataclass(frozen=True)
class ProjectSettings:
    github_owner: str
    github_repo: str
    release_asset_strategy: str
    state_path: str
    protected_paths: list[str]
    managed_paths: list[str]
    seed_paths: list[str]
    components: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class LlamaSwapRuntime:
    executable: str
    host: str
    port: int
    project_config_path: str
    local_override_path: str
    generated_config_path: str
    health_paths: list[str]
    extra_args: list[str]


@dataclass(frozen=True)
class LiteLLMRuntime:
    host: str
    port: int
    executable: str
    generated_config_path: str
    master_key_env: str
    health_paths: list[str]
    extra_args: list[str]


@dataclass(frozen=True)
class PublishedModel:
    stable_name: str
    llama_swap_model: str
    backend_model_name: str
    purpose: str
    api_key_placeholder: str
    mode: str


@dataclass(frozen=True)
class MCPConfig:
    enabled: bool
    project_config_path: str
    local_override_path: str
    generated_client_path: str
    gateway_server_name: str


@dataclass(frozen=True)
class InstallConfig:
    venv_path: str
    python_min_version: str


@dataclass(frozen=True)
class StackConfig:
    root: Path
    project: ProjectSettings
    install: InstallConfig
    llama_swap: LlamaSwapRuntime
    litellm: LiteLLMRuntime
    published_models: list[PublishedModel]
    mcp: MCPConfig
    routing: dict[str, Any]
    reverse_proxy: dict[str, Any]


def _substitute_env(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        return os.environ.get(match.group(1), match.group(0))

    return ENV_PATTERN.sub(replace, value)


def _resolve_env(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {key: _resolve_env(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [_resolve_env(item) for item in obj]
    if isinstance(obj, str):
        return _substitute_env(obj)
    return obj


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}
    if not isinstance(content, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return _resolve_env(content)


def deep_merge(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            if key in merged:
                merged[key] = deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged
    if isinstance(base, list) and isinstance(override, list):
        if not override:
            return list(base)
        return list(override)
    return override


def type_conflicts(base: Any, override: Any, prefix: str = "") -> list[str]:
    conflicts: list[str] = []
    if isinstance(base, dict) and isinstance(override, dict):
        for key, value in override.items():
            if key in base:
                child_prefix = f"{prefix}.{key}" if prefix else key
                conflicts.extend(type_conflicts(base[key], value, child_prefix))
        return conflicts
    if isinstance(base, dict) != isinstance(override, dict):
        conflicts.append(prefix or "<root>")
    return conflicts


def load_layered_yaml(root: str | Path, project_rel: str, local_rel: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    root_path = Path(root).resolve()
    project_path = root_path / project_rel
    local_path = root_path / local_rel
    project_data = _load_yaml(project_path)
    local_data = _load_yaml(local_path) if local_path.exists() else {}
    merged = deep_merge(project_data, local_data)
    return project_data, local_data, merged


def load_stack_config(root: str | Path) -> StackConfig:
    root_path = Path(root).resolve()
    _, _, raw = load_layered_yaml(root_path, "config/project/stack.base.yaml", "config/local/stack.override.yaml")

    project_raw = raw.get("project", {})
    install_raw = raw.get("install", {})
    llama_swap_raw = raw.get("llama_swap", {})
    litellm_raw = raw.get("litellm", {})
    published_raw = raw.get("published_models", [])
    mcp_raw = raw.get("mcp", {})
    routing = raw.get("routing", {})
    reverse_proxy = raw.get("reverse_proxy", {})

    if not published_raw:
        raise ValueError("stack config does not define any published_models")

    project = ProjectSettings(
        github_owner=str(project_raw.get("github", {}).get("owner", "AUDia")),
        github_repo=str(project_raw.get("github", {}).get("repo", "AUDiaLLMGateway")),
        release_asset_strategy=str(project_raw.get("github", {}).get("release_asset_strategy", "source_archive")),
        state_path=str(project_raw.get("installer", {}).get("state_path", "state/install-state.json")),
        protected_paths=[str(item) for item in project_raw.get("installer", {}).get("protected_paths", [])],
        managed_paths=[str(item) for item in project_raw.get("installer", {}).get("managed_paths", [])],
        seed_paths=[str(item) for item in project_raw.get("installer", {}).get("seed_paths", [])],
        components={str(key): value for key, value in project_raw.get("components", {}).items()},
    )

    install = InstallConfig(
        venv_path=str(install_raw.get("venv_path", ".venv")),
        python_min_version=str(install_raw.get("python_min_version", "3.11")),
    )

    llama_swap = LlamaSwapRuntime(
        executable=str(llama_swap_raw.get("executable", "llama-swap")),
        host=str(llama_swap_raw.get("host", "127.0.0.1")),
        port=int(llama_swap_raw.get("port", 41080)),
        project_config_path=str(llama_swap_raw.get("project_config_path", "config/project/llama-swap.base.yaml")),
        local_override_path=str(llama_swap_raw.get("local_override_path", "config/local/llama-swap.override.yaml")),
        generated_config_path=str(llama_swap_raw.get("generated_config_path", "config/generated/llama-swap.generated.yaml")),
        health_paths=[str(item) for item in llama_swap_raw.get("health_paths", ["/health", "/v1/models"])],
        extra_args=[str(item) for item in llama_swap_raw.get("extra_args", [])],
    )

    litellm = LiteLLMRuntime(
        host=str(litellm_raw.get("host", "127.0.0.1")),
        port=int(litellm_raw.get("port", 4000)),
        executable=str(litellm_raw.get("executable", "litellm")),
        generated_config_path=str(litellm_raw.get("generated_config_path", "config/generated/litellm.config.yaml")),
        master_key_env=str(litellm_raw.get("master_key_env", "LITELLM_MASTER_KEY")),
        health_paths=[str(item) for item in litellm_raw.get("health_paths", ["/health", "/v1/models"])],
        extra_args=[str(item) for item in litellm_raw.get("extra_args", [])],
    )

    published_models = [
        PublishedModel(
            stable_name=str(item["stable_name"]),
            llama_swap_model=str(item["llama_swap_model"]),
            backend_model_name=str(item.get("backend_model_name", item["llama_swap_model"])),
            purpose=str(item.get("purpose", "")),
            api_key_placeholder=str(item.get("api_key_placeholder", "not-required-for-local-backends")),
            mode=str(item.get("mode", "chat")),
        )
        for item in published_raw
    ]

    mcp = MCPConfig(
        enabled=bool(mcp_raw.get("enabled", False)),
        project_config_path=str(mcp_raw.get("project_config_path", "config/project/mcp.base.yaml")),
        local_override_path=str(mcp_raw.get("local_override_path", "config/local/mcp.override.yaml")),
        generated_client_path=str(mcp_raw.get("generated_client_path", "config/generated/litellm.mcp.client.json")),
        gateway_server_name=str(mcp_raw.get("gateway_server_name", "litellm-gateway")),
    )

    return StackConfig(
        root=root_path,
        project=project,
        install=install,
        llama_swap=llama_swap,
        litellm=litellm,
        published_models=published_models,
        mcp=mcp,
        routing=routing,
        reverse_proxy=reverse_proxy,
    )


def load_llama_swap_source_config(root: str | Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    root_path = Path(root).resolve()
    stack_base, stack_local, stack_merged = load_layered_yaml(root_path, "config/project/stack.base.yaml", "config/local/stack.override.yaml")
    llama_swap_raw = stack_merged.get("llama_swap", {})
    project_path = str(llama_swap_raw.get("project_config_path", "config/project/llama-swap.base.yaml"))
    local_path = str(llama_swap_raw.get("local_override_path", "config/local/llama-swap.override.yaml"))
    return load_layered_yaml(root_path, project_path, local_path)


def load_mcp_registry(root: str | Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    root_path = Path(root).resolve()
    _, _, stack_merged = load_layered_yaml(root_path, "config/project/stack.base.yaml", "config/local/stack.override.yaml")
    mcp_raw = stack_merged.get("mcp", {})
    project_path = str(mcp_raw.get("project_config_path", "config/project/mcp.base.yaml"))
    local_path = str(mcp_raw.get("local_override_path", "config/local/mcp.override.yaml"))
    return load_layered_yaml(root_path, project_path, local_path)


def build_llama_swap_config(stack: StackConfig) -> dict[str, Any]:
    _, _, merged = load_llama_swap_source_config(stack.root)
    return merged


def build_litellm_config(stack: StackConfig) -> dict[str, Any]:
    api_base = f"http://{stack.llama_swap.host}:{stack.llama_swap.port}/v1"
    model_list = []
    for model in stack.published_models:
        model_list.append(
            {
                "model_name": model.stable_name,
                "litellm_params": {
                    "model": f"openai/{model.backend_model_name}",
                    "api_base": api_base,
                    "api_key": model.api_key_placeholder,
                    "extra_headers": {
                        "X-LLAMA-SWAP-MODEL": model.llama_swap_model,
                    },
                },
                "model_info": {
                    "mode": model.mode,
                    "llama_swap_model": model.llama_swap_model,
                    "purpose": model.purpose,
                },
            }
        )

    return {
        "model_list": model_list,
        "litellm_settings": {
            "master_key": f"os.environ/{stack.litellm.master_key_env}",
        },
        "general_settings": {
            "disable_spend_logs": True,
        },
        "router_settings": {},
    }


def build_mcp_client_config(stack: StackConfig) -> dict[str, Any]:
    _, _, registry = load_mcp_registry(stack.root)
    return {
        "enabled": stack.mcp.enabled,
        "gateway_server_name": stack.mcp.gateway_server_name,
        "servers": {
            stack.mcp.gateway_server_name: {
                "type": "http",
                "url": f"http://{stack.litellm.host}:{stack.litellm.port}/mcp",
                "headers": {
                    "Authorization": f"Bearer ${{{stack.litellm.master_key_env}}}",
                },
            }
        },
        "upstream_registry": registry,
    }


def _write_yaml_with_header(path: Path, header: str, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        handle.write(header)
        yaml.safe_dump(payload, handle, sort_keys=False)
    return path


def write_llama_swap_config(root: str | Path) -> Path:
    stack = load_stack_config(root)
    output_path = stack.root / stack.llama_swap.generated_config_path
    payload = build_llama_swap_config(stack)
    header = (
        "# Generated from config/project/llama-swap.base.yaml and config/local/llama-swap.override.yaml.\n"
        "# Regenerate with:\n"
        "#   python -m src.launcher.process_manager generate-configs\n"
    )
    return _write_yaml_with_header(output_path, header, payload)


def write_litellm_config(root: str | Path) -> Path:
    stack = load_stack_config(root)
    output_path = stack.root / stack.litellm.generated_config_path
    payload = build_litellm_config(stack)
    header = (
        "# Generated from config/project/stack.base.yaml and config/local/stack.override.yaml.\n"
        "# Regenerate with:\n"
        "#   python -m src.launcher.process_manager generate-configs\n"
    )
    return _write_yaml_with_header(output_path, header, payload)


def write_mcp_client_config(root: str | Path) -> Path:
    stack = load_stack_config(root)
    output_path = stack.root / stack.mcp.generated_client_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(build_mcp_client_config(stack), handle, indent=2)
    return output_path


def validate_layered_configs(root: str | Path) -> dict[str, Any]:
    llama_base, llama_local, _ = load_llama_swap_source_config(root)
    mcp_base, mcp_local, _ = load_mcp_registry(root)
    stack_base, stack_local, _ = load_layered_yaml(root, "config/project/stack.base.yaml", "config/local/stack.override.yaml")
    state_path = stack_base.get("project", {}).get("installer", {}).get("state_path", "state/install-state.json")
    return {
        "ok": True,
        "type_conflicts": {
            "stack": type_conflicts(stack_base, stack_local),
            "llama_swap": type_conflicts(llama_base, llama_local),
            "mcp": type_conflicts(mcp_base, mcp_local),
        },
        "state_path": str(Path(root).resolve() / state_path),
    }


def write_generated_configs(root: str | Path) -> dict[str, Path]:
    return {
        "llama_swap": write_llama_swap_config(root),
        "litellm": write_litellm_config(root),
        "mcp_client": write_mcp_client_config(root),
    }
