from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _detect_local_ip() -> str:
    """Return the single non-loopback IPv4 address, or '127.0.0.1' if zero or multiple."""
    import socket

    candidates: set[str] = set()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            addr = s.getsockname()[0]
            if not addr.startswith("127."):
                candidates.add(addr)
    except Exception:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            addr = info[4][0]
            if not addr.startswith("127."):
                candidates.add(addr)
    except Exception:
        pass
    if len(candidates) == 1:
        return next(iter(candidates))
    return "127.0.0.1"


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
    revision: str
    model_filename: str
    model_url: str
    additional_model_urls: list[str]
    mmproj_filename: str
    mmproj_url: str
    source_page_url: str
    load_groups: list[str]
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
class NginxRuntime:
    enabled: bool
    executable: str
    config_path: str
    host: str
    port: int
    health_paths: list[str]


@dataclass(frozen=True)
class SystemdConfig:
    enabled: bool
    service_name: str
    user: str
    group: str
    description: str
    after: str
    restart: str


@dataclass(frozen=True)
class InstallConfig:
    venv_path: str
    python_min_version: str


@dataclass(frozen=True)
class NetworkConfig:
    backend_bind_host: str
    public_host: str
    llamaswap_host: str
    llamaswap_port: int
    litellm_host: str
    litellm_port: int
    nginx_host: str
    nginx_port: int


@dataclass(frozen=True)
class StackConfig:
    root: Path
    project: ProjectSettings
    install: InstallConfig
    network: NetworkConfig
    llama_swap: LlamaSwapRuntime
    litellm: LiteLLMRuntime
    published_models: list[PublishedModel]
    mcp: MCPConfig
    routing: dict[str, Any]
    reverse_proxy: dict[str, Any]
    nginx: NginxRuntime
    systemd: SystemdConfig
    component_settings: dict[str, Any]
    models_project_config_path: str
    models_local_override_path: str


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
        content = yaml.safe_load(handle)
    if not isinstance(content, dict):
        return {}
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
    network_raw = raw.get("network", {})
    llama_swap_raw = raw.get("llama_swap", {})
    litellm_raw = raw.get("litellm", {})
    mcp_raw = raw.get("mcp", {})
    routing = raw.get("routing", {})
    reverse_proxy = raw.get("reverse_proxy", {})
    nginx_raw = reverse_proxy.get("nginx", {}) if isinstance(reverse_proxy, dict) else {}
    _nginx_exe_raw = str(nginx_raw.get("executable", "nginx"))
    nginx = NginxRuntime(
        enabled=bool(nginx_raw.get("enabled", False)),
        executable=_nginx_exe_raw,  # resolved below after install-state is loaded
        config_path=str(nginx_raw.get("config_path", "config/generated/nginx/nginx.conf")),
        host="",  # resolved below after _auto_ip is computed
        port=int(network_raw.get("services", {}).get("nginx", {}).get("port", 8080)),
        health_paths=[str(item) for item in nginx_raw.get("health_paths", ["/health"])],
    )

    systemd_raw = raw.get("systemd", {})
    _current_user = ""
    _current_group = ""
    if os.name != "nt":
        import getpass
        import grp
        try:
            _current_user = getpass.getuser()
            _current_group = grp.getgrgid(os.getgid()).gr_name
        except Exception:
            pass

    systemd = SystemdConfig(
        enabled=bool(systemd_raw.get("enabled", True)),
        service_name=str(systemd_raw.get("service_name", "audia-gateway")),
        user=str(systemd_raw.get("user") or _current_user),
        group=str(systemd_raw.get("group") or _current_group),
        description=str(systemd_raw.get("description", "AUDia LLM Gateway")),
        after=str(systemd_raw.get("after", "network.target")),
        restart=str(systemd_raw.get("restart", "always")),
    )

    component_settings = project_raw.get("component_settings", {})
    models_raw = raw.get("models", {})

    if not isinstance(models_raw, dict):
        models_raw = {}

    if not models_raw:
        raise ValueError("stack config does not define a model catalog configuration")

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

    services_raw = network_raw.get("services", {}) if isinstance(network_raw, dict) else {}
    llamaswap_service = services_raw.get("llama_swap", {}) if isinstance(services_raw, dict) else {}
    litellm_service = services_raw.get("litellm", {}) if isinstance(services_raw, dict) else {}
    nginx_service = services_raw.get("nginx", {}) if isinstance(services_raw, dict) else {}

    _auto_ip = _detect_local_ip()
    network = NetworkConfig(
        backend_bind_host=str(network_raw.get("backend_bind_host") or _auto_ip),
        public_host=str(network_raw.get("public_host") or _auto_ip),
        llamaswap_host=str(llamaswap_service.get("host") or llama_swap_raw.get("host") or _auto_ip),
        llamaswap_port=int(llamaswap_service.get("port", llama_swap_raw.get("port", 41080))),
        litellm_host=str(litellm_service.get("host") or litellm_raw.get("host") or _auto_ip),
        litellm_port=int(litellm_service.get("port", litellm_raw.get("port", 4000))),
        nginx_host=str(nginx_service.get("host") or _auto_ip),
        nginx_port=int(nginx_service.get("port", 8080)),
    )

    # Resolve llama-swap executable: stack config > install-state.json > fallback
    _state_path = root_path / str(project_raw.get("installer", {}).get("state_path", "state/install-state.json"))
    _install_state: dict[str, Any] = {}
    if _state_path.exists():
        try:
            _install_state = json.loads(_state_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    _swap_exe_raw = str(llama_swap_raw.get("executable", "${LLAMA_SWAP_EXE}"))
    _swap_exe_resolved = _swap_exe_raw if "${" not in _swap_exe_raw else ""
    if not _swap_exe_resolved:
        _swap_exe_resolved = _install_state.get("component_results", {}).get("llama_swap", {}).get("path", "")
    if not _swap_exe_resolved:
        import shutil as _shutil
        _swap_exe_resolved = _shutil.which("llama-swap") or "llama-swap"

    # Resolve nginx executable: YAML value > install-state.json > bare name
    # If YAML has an absolute path, use it directly.  If it's a bare name like
    # "nginx", prefer the path recorded by ensure_nginx() in install-state.json
    # so that winget/apt-installed binaries are found without relying on the
    # Windows registry or a freshly opened shell.
    if not os.path.isabs(_nginx_exe_raw):
        _nginx_path_from_state = _install_state.get("component_results", {}).get("nginx", {}).get("path", "")
        if _nginx_path_from_state:
            _nginx_exe_raw = _nginx_path_from_state
    nginx = NginxRuntime(
        enabled=nginx.enabled,
        executable=_nginx_exe_raw,
        config_path=nginx.config_path,
        host=network.nginx_host,
        port=nginx.port,
        health_paths=nginx.health_paths,
    )

    llama_swap = LlamaSwapRuntime(
        executable=_swap_exe_resolved,
        host=network.llamaswap_host,
        port=network.llamaswap_port,
        project_config_path=str(llama_swap_raw.get("project_config_path", "config/project/llama-swap.base.yaml")),
        local_override_path=str(llama_swap_raw.get("local_override_path", "config/local/llama-swap.override.yaml")),
        generated_config_path=str(llama_swap_raw.get("generated_config_path", "config/generated/llama-swap/llama-swap.generated.yaml")),
        health_paths=[str(item) for item in llama_swap_raw.get("health_paths", ["/health", "/v1/models"])],
        extra_args=[str(item) for item in llama_swap_raw.get("extra_args", [])],
    )

    litellm = LiteLLMRuntime(
        host=network.litellm_host,
        port=network.litellm_port,
        executable=str(litellm_raw.get("executable", "litellm")),
        generated_config_path=str(litellm_raw.get("generated_config_path", "config/generated/litellm/litellm.config.yaml")),
        master_key_env=str(litellm_raw.get("master_key_env", "LITELLM_MASTER_KEY")),
        health_paths=[str(item) for item in litellm_raw.get("health_paths", ["/health", "/v1/models"])],
        extra_args=[str(item) for item in litellm_raw.get("extra_args", [])],
    )

    mcp = MCPConfig(
        enabled=bool(mcp_raw.get("enabled", False)),
        project_config_path=str(mcp_raw.get("project_config_path", "config/project/mcp.base.yaml")),
        local_override_path=str(mcp_raw.get("local_override_path", "config/local/mcp.override.yaml")),
        generated_client_path=str(mcp_raw.get("generated_client_path", "config/generated/mcp/litellm.mcp.client.json")),
        gateway_server_name=str(mcp_raw.get("gateway_server_name", "litellm-gateway")),
    )

    published_models: list[PublishedModel] = []
    if models_raw:
        temp_stack = StackConfig(
            root=root_path,
            project=project,
            install=install,
            network=network,
            llama_swap=llama_swap,
            litellm=litellm,
            published_models=[],
            mcp=mcp,
            routing=routing,
            reverse_proxy=reverse_proxy,
            nginx=nginx,
            systemd=systemd,
            component_settings=component_settings,
            models_project_config_path=str(models_raw.get("project_config_path", "config/project/models.base.yaml")),
            models_local_override_path=str(models_raw.get("local_override_path", "config/local/models.override.yaml")),
        )
        published_models = _catalog_published_models(temp_stack)
    return StackConfig(
        root=root_path,
        project=project,
        install=install,
        network=network,
        llama_swap=llama_swap,
        litellm=litellm,
        published_models=published_models,
        mcp=mcp,
        routing=routing,
        reverse_proxy=reverse_proxy,
        nginx=nginx,
        systemd=systemd,
        component_settings=component_settings,
        models_project_config_path=str(models_raw.get("project_config_path", "config/project/models.base.yaml")),
        models_local_override_path=str(models_raw.get("local_override_path", "config/local/models.override.yaml")),
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


def load_model_catalog(root: str | Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    root_path = Path(root).resolve()
    _, _, stack_merged = load_layered_yaml(root_path, "config/project/stack.base.yaml", "config/local/stack.override.yaml")
    models_raw = stack_merged.get("models", {})
    if not isinstance(models_raw, dict):
        models_raw = {}
    project_path = root_path / str(models_raw.get("project_config_path", "config/project/models.base.yaml"))
    local_path = root_path / str(models_raw.get("local_override_path", "config/local/models.override.yaml"))
    if not project_path.exists():
        return {}, {}, {}
    project_data = _load_yaml(project_path)
    local_data = _load_yaml(local_path) if local_path.exists() else {}
    return project_data, local_data, deep_merge(project_data, local_data)


def _resolve_context_preset(catalog: dict[str, Any], context_name: str) -> tuple[str, dict[str, Any]]:
    normalized = str(context_name).strip()
    contexts = catalog.get("presets", {}).get("contexts", {})
    if normalized in contexts:
        return normalized, contexts[normalized]
    for preset_name, preset in contexts.items():
        aliases = [str(item).strip() for item in preset.get("aliases", [])]
        if normalized in aliases:
            return str(preset_name), preset
    raise ValueError(f"Model catalog context preset '{context_name}' is not defined")


def _catalog_context_macro(catalog: dict[str, Any], context_name: str, macros: dict[str, Any], framework: dict[str, Any]) -> str:
    preset_name, context = _resolve_context_preset(catalog, context_name)
    explicit_macro_name = str(context.get("llama_swap_macro", "")).strip()
    if explicit_macro_name:
        return f"${{{explicit_macro_name}}}"

    tokens = int(context.get("tokens", 0))
    if tokens <= 0:
        raise ValueError(f"Model catalog context preset '{preset_name}' must define a positive token count")

    alias_value = str(context.get("macro_alias", preset_name)).strip()
    llama_swap_cfg = framework.get("llama_swap", {})
    macro_name_template = str(llama_swap_cfg.get("context_macro_name_template", "context-{alias}-args"))
    arg_template = str(llama_swap_cfg.get("context_arg_template", "--ctx-size {tokens}"))
    macro_name = macro_name_template.format(alias=alias_value, tokens=tokens)
    if macro_name not in macros:
        macros[macro_name] = arg_template.format(alias=alias_value, tokens=tokens)
    return f"${{{macro_name}}}"


def _catalog_named_macro(catalog: dict[str, Any], section: str, preset_name: str) -> str:
    presets = catalog.get("presets", {}).get(section, {})
    preset = presets.get(preset_name, {})
    macro_name = str(preset.get("llama_swap_macro", "")).strip()
    if not macro_name:
        raise ValueError(f"Model catalog preset '{section}.{preset_name}' does not define llama_swap_macro")
    return f"${{{macro_name}}}"


def _format_llama_cpp_option_value(value: Any) -> str:
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, separators=(",", ":"))
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _render_llama_cpp_options(options: dict[str, Any]) -> str:
    parts: list[str] = []
    for key, value in options.items():
        flag = f"--{str(key).replace('_', '-')}"
        if isinstance(value, bool):
            if value:
                parts.append(flag)
            continue
        parts.append(f"{flag} {_format_llama_cpp_option_value(value)}")
    return " ".join(parts)


def _synthesize_catalog_macros(catalog: dict[str, Any], macros: dict[str, Any], local_macros: dict[str, Any]) -> None:
    presets = catalog.get("presets", {})
    for section in ("gpu_profiles", "runtime_profiles"):
        for preset_name, preset in presets.get(section, {}).items():
            if not isinstance(preset, dict):
                continue
            macro_name = str(preset.get("llama_swap_macro", "")).strip()
            if not macro_name or macro_name in local_macros or macro_name in macros:
                continue
            options = preset.get("llama_cpp_options", {})
            if not isinstance(options, dict) or not options:
                raise ValueError(
                    f"Model catalog preset '{section}.{preset_name}' must define llama_cpp_options to synthesize macro '{macro_name}'"
                )
            macros[macro_name] = _render_llama_cpp_options(options)


def _generated_llama_swap_models(stack: StackConfig, macros: dict[str, Any]) -> dict[str, Any]:
    _, _, catalog = load_model_catalog(stack.root)
    generated: dict[str, Any] = {}
    frameworks = catalog.get("frameworks", {})
    profiles = catalog.get("model_profiles", {})

    for profile_name, profile in profiles.items():
        defaults = profile.get("defaults", {})
        artifacts = profile.get("artifacts", {})
        deployments = profile.get("deployments", {})
        for deployment_name, deployment in deployments.items():
            if not deployment.get("enabled", True):
                continue
            if str(deployment.get("transport", "llama-swap")) != "llama-swap":
                continue
            framework_name = str(deployment.get("framework", "llama_cpp"))
            if framework_name != "llama_cpp":
                continue

            framework = frameworks.get(framework_name, {})
            executable_macro = str(deployment.get("executable_macro", framework.get("llama_swap", {}).get("executable_macro", "llama-server")))
            server_args_macro = str(framework.get("llama_swap", {}).get("server_args_macro", "server-args"))
            model_path_macro = str(framework.get("llama_swap", {}).get("model_path_macro", "model-path"))
            mmproj_path_macro = str(framework.get("llama_swap", {}).get("mmproj_path_macro", "mmproj-path"))

            context_name = str(deployment.get("context_preset", defaults.get("context_preset", ""))).strip()
            gpu_name = str(deployment.get("gpu_preset", defaults.get("gpu_preset", ""))).strip()
            runtime_presets = [str(item) for item in defaults.get("runtime_presets", [])]
            runtime_presets.extend([str(item) for item in deployment.get("runtime_presets", [])])
            additional_macros = [str(item) for item in deployment.get("additional_macro_refs", [])]

            if not context_name or not gpu_name:
                raise ValueError(f"Model catalog deployment '{profile_name}.{deployment_name}' requires context_preset and gpu_preset")

            model_file = str(deployment.get("model_file", artifacts.get("model_file", ""))).strip()
            if not model_file:
                raise ValueError(f"Model catalog deployment '{profile_name}.{deployment_name}' does not define model_file")
            mmproj_file = str(deployment.get("mmproj_file", artifacts.get("mmproj_file", ""))).strip()

            model_file = model_file.replace("\\", "/")
            mmproj_file = mmproj_file.replace("\\", "/")
            lines = [
                f"${{{executable_macro}}}",
                f"${{{server_args_macro}}}",
                f"${{{model_path_macro}}}/{model_file}",
            ]
            if mmproj_file:
                lines.append(f"${{{mmproj_path_macro}}}/{mmproj_file}")
            lines.append(_catalog_context_macro(catalog, context_name, macros, framework))
            lines.append(_catalog_named_macro(catalog, "gpu_profiles", gpu_name))
            for preset_name in runtime_presets:
                lines.append(_catalog_named_macro(catalog, "runtime_profiles", preset_name))
            for macro_ref in additional_macros:
                lines.append(f"${{{macro_ref}}}")

            model_id = str(deployment.get("llama_swap_model", deployment_name))
            entry: dict[str, Any] = {"cmd": "\n".join(lines)}
            concurrency_limit = deployment.get("concurrency_limit", defaults.get("concurrency_limit"))
            if concurrency_limit is not None:
                entry["concurrencyLimit"] = int(concurrency_limit)
            generated[model_id] = entry
    return generated


def _catalog_deployment_map(catalog: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    deployments: dict[tuple[str, str], dict[str, Any]] = {}
    for profile_name, profile in catalog.get("model_profiles", {}).items():
        for deployment_name, deployment in profile.get("deployments", {}).items():
            deployments[(str(profile_name), str(deployment_name))] = deployment
    return deployments


def _generated_llama_swap_groups(stack: StackConfig) -> dict[str, Any]:
    _, _, catalog = load_model_catalog(stack.root)
    deployment_map = _catalog_deployment_map(catalog)

    # Build set of enabled llama-swap model IDs (disabled deployments must be excluded from groups)
    enabled_model_ids: set[str] = set()
    for profile_name, profile in catalog.get("model_profiles", {}).items():
        for dep_name, dep in profile.get("deployments", {}).items():
            if not dep.get("enabled", True):
                continue
            if str(dep.get("transport", "llama-swap")) != "llama-swap":
                continue
            model_id = str(dep.get("llama_swap_model", dep_name))
            enabled_model_ids.add(model_id)

    generated: dict[str, Any] = {}

    for group_name, group in catalog.get("load_groups", {}).items():
        members: list[str] = []
        for member in group.get("members", []):
            if isinstance(member, str):
                members.append(member)
                continue
            if not isinstance(member, dict):
                continue
            profile_name = str(member.get("model_profile", ""))
            deployment_name = str(member.get("deployment", ""))
            deployment = deployment_map.get((profile_name, deployment_name), {})
            llama_swap_model = str(member.get("llama_swap_model", deployment.get("llama_swap_model", ""))).strip()
            if llama_swap_model and llama_swap_model in enabled_model_ids:
                members.append(llama_swap_model)

        entry: dict[str, Any] = {
            "persistent": bool(group.get("persistent", False)),
            "swap": bool(group.get("swap", False)),
            "exclusive": bool(group.get("exclusive", False)),
            "members": members,
        }
        if "activities" in group:
            entry["activities"] = [str(item) for item in group.get("activities", [])]
        if "purpose" in group:
            entry["purpose"] = str(group.get("purpose", ""))
        generated[str(group_name)] = entry
    return generated


def _catalog_published_models(stack: StackConfig) -> list[PublishedModel]:
    _, _, catalog = load_model_catalog(stack.root)
    profiles = catalog.get("model_profiles", {})
    load_groups = catalog.get("load_groups", {})
    result: list[PublishedModel] = []
    for exposure in catalog.get("exposures", []):
        profile_name = str(exposure["model_profile"])
        profile = profiles.get(profile_name, {})
        deployment_name = str(exposure.get("deployment", ""))
        deployment = profile.get("deployments", {}).get(deployment_name, {})
        if not deployment_name or not deployment:
            raise ValueError(f"Model exposure '{exposure.get('stable_name', '<unknown>')}' references missing deployment '{profile_name}.{deployment_name}'")

        backend_model_name = str(exposure.get("backend_model_name", deployment.get("backend_model_name", deployment.get("llama_swap_model", deployment_name))))
        llama_swap_model = str(exposure.get("llama_swap_model", deployment.get("llama_swap_model", deployment_name)))
        purpose = str(exposure.get("purpose", profile.get("purpose", "")))
        model_load_groups = [
            str(group_name)
            for group_name, group in load_groups.items()
            if any(
                isinstance(member, dict)
                and str(member.get("model_profile", "")) == profile_name
                and str(member.get("deployment", "")) == deployment_name
                for member in group.get("members", [])
            )
        ]
        result.append(
            PublishedModel(
                stable_name=str(exposure["stable_name"]),
                llama_swap_model=llama_swap_model,
                backend_model_name=backend_model_name,
                purpose=purpose,
                revision=str(exposure.get("revision", profile.get("artifacts", {}).get("revision", ""))),
                model_filename=str(exposure.get("model_filename", profile.get("artifacts", {}).get("model_filename", ""))),
                model_url=str(exposure.get("model_url", profile.get("artifacts", {}).get("model_url", ""))),
                additional_model_urls=[str(url) for url in exposure.get("additional_model_urls", profile.get("artifacts", {}).get("additional_model_urls", []))],
                mmproj_filename=str(exposure.get("mmproj_filename", profile.get("artifacts", {}).get("mmproj_filename", ""))),
                mmproj_url=str(exposure.get("mmproj_url", profile.get("artifacts", {}).get("mmproj_url", ""))),
                source_page_url=str(exposure.get("source_page_url", profile.get("artifacts", {}).get("source_page_url", ""))),
                load_groups=model_load_groups,
                api_key_placeholder=str(exposure.get("api_key_placeholder", "not-required-for-local-backends")),
                mode=str(exposure.get("mode", "chat")),
            )
        )
    return result


def load_published_models(root: str | Path) -> list[PublishedModel]:
    return load_stack_config(root).published_models


def build_llama_swap_config(stack: StackConfig) -> dict[str, Any]:
    _, llama_local, merged = load_llama_swap_source_config(stack.root)
    _, _, catalog = load_model_catalog(stack.root)
    local_macros = llama_local.get("macros", {}) if isinstance(llama_local, dict) else {}
    state_path = stack.root / stack.project.state_path
    install_state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    llama_cpp_state = install_state.get("component_results", {}).get("llama_cpp", {})
    macros = merged.setdefault("macros", {})
    if "server-args" not in local_macros:
        macros["server-args"] = f"--port ${{PORT}} --host {stack.network.backend_bind_host}"
    # Generate per-backend macros from all installed variants
    # e.g. llama-server-cpu, llama-server-rocm, llama-server-vulkan, llama-server-cuda
    variants = llama_cpp_state.get("variants", {})
    for profile_name, info in variants.items():
        backend = str(info.get("backend", "")).strip() or profile_name
        exe = str(info.get("executable_path", ""))
        if not exe:
            continue
        # Backend-named macro (llama-server-rocm, llama-server-vulkan, etc.)
        backend_macro = f"llama-server-{backend}"
        if backend_macro not in local_macros:
            macros[backend_macro] = exe
        # Also add rocm_executable_path alias for backward compat
        if backend == "rocm" and "rocm_executable_path" not in llama_cpp_state:
            llama_cpp_state["rocm_executable_path"] = exe

    # llama-server (default) — prefer the cpu variant, then primary executable_path
    executable_path = llama_cpp_state.get("executable_path")
    if "llama-server" not in local_macros:
        cpu_exe = next(
            (str(i.get("executable_path", "")) for i in variants.values()
             if str(i.get("backend", "")) == "cpu" and i.get("executable_path")),
            None,
        )
        if cpu_exe:
            macros["llama-server"] = cpu_exe
        elif executable_path:
            macros["llama-server"] = str(executable_path)

    # llama-server-rocm backward compat from top-level state field
    rocm_executable_path = llama_cpp_state.get("rocm_executable_path")
    if rocm_executable_path and "llama-server-rocm" not in local_macros and "llama-server-rocm" not in macros:
        macros["llama-server-rocm"] = str(rocm_executable_path)

    models_state = install_state.get("component_results", {}).get("models", {})
    model_dir = models_state.get("model_dir", "")
    if model_dir:
        if "model-path" not in local_macros:
            macros["model-path"] = f"--model {model_dir}"
        if "mmproj-path" not in local_macros:
            macros["mmproj-path"] = f"--mmproj {model_dir}"
    _synthesize_catalog_macros(catalog, macros, local_macros)
    generated_models = _generated_llama_swap_models(stack, macros)
    merged["models"] = {**merged.get("models", {}), **generated_models}
    generated_groups = _generated_llama_swap_groups(stack)
    merged["groups"] = {**merged.get("groups", {}), **generated_groups}
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
                    "revision": model.revision,
                    "model_filename": model.model_filename,
                    "model_url": model.model_url,
                    "additional_model_urls": model.additional_model_urls,
                    "mmproj_filename": model.mmproj_filename,
                    "mmproj_url": model.mmproj_url,
                    "source_page_url": model.source_page_url,
                    "load_groups": model.load_groups,
                },
            }
        )

    return {
        "model_list": model_list,
        "litellm_settings": {},
        "general_settings": {
            "disable_spend_logs": True,
            "no_auth": True,
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
                "url": f"http://{stack.network.litellm_host}:{stack.network.litellm_port}/mcp",
                "headers": {
                    "Authorization": f"Bearer ${{{stack.litellm.master_key_env}}}",
                },
            }
        },
        "upstream_registry": registry,
    }


def build_nginx_landing_page(stack: StackConfig) -> str:
    host = stack.network.public_host
    port = stack.network.nginx_port
    base = f"http://{host}:{port}"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AUDia LLM Gateway</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 720px; margin: 3rem auto; padding: 0 1.5rem; color: #222; }}
    h1 {{ font-size: 1.6rem; margin-bottom: 0.25rem; }}
    .sub {{ color: #666; margin-bottom: 2rem; font-size: 0.95rem; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 2rem; }}
    th {{ text-align: left; padding: 0.5rem 0.75rem; background: #f4f4f4; border-bottom: 2px solid #ddd; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; }}
    td {{ padding: 0.6rem 0.75rem; border-bottom: 1px solid #eee; vertical-align: top; }}
    a {{ color: #0066cc; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    code {{ background: #f4f4f4; padding: 0.1em 0.4em; border-radius: 3px; font-size: 0.9em; }}
    .tag {{ display: inline-block; font-size: 0.75rem; padding: 0.1em 0.5em; border-radius: 3px; background: #e8f4ff; color: #0066cc; }}
  </style>
</head>
<body>
  <h1>AUDia LLM Gateway</h1>
  <p class="sub">Running on <code>{host}:{port}</code></p>

  <table>
    <thead><tr><th>Endpoint</th><th>Description</th><th>Type</th></tr></thead>
    <tbody>
      <tr>
        <td><a href="{base}/v1/models">/v1/models</a></td>
        <td>OpenAI-compatible model list via LiteLLM</td>
        <td><span class="tag">API</span></td>
      </tr>
      <tr>
        <td><a href="{base}/litellm/">/litellm/</a></td>
        <td>LiteLLM gateway &mdash; full OpenAI-compatible API
          (<code>{stack.network.litellm_host}:{stack.network.litellm_port}</code>)</td>
        <td><span class="tag">Proxy</span></td>
      </tr>
      <tr>
        <td><a href="{base}/llamaswap/">/llamaswap/</a></td>
        <td>llama-swap model router &mdash; direct backend access
          (<code>{stack.network.llamaswap_host}:{stack.network.llamaswap_port}</code>)</td>
        <td><span class="tag">Proxy</span></td>
      </tr>
      <tr>
        <td><a href="{base}/ui/">/ui/</a></td>
        <td>LiteLLM admin UI</td>
        <td><span class="tag">UI</span></td>
      </tr>
      <tr>
        <td><a href="{base}/health">/health</a></td>
        <td>LiteLLM health check</td>
        <td><span class="tag">Health</span></td>
      </tr>
      <tr>
        <td><a href="{base}/llamaswap-health">/llamaswap-health</a></td>
        <td>llama-swap health check</td>
        <td><span class="tag">Health</span></td>
      </tr>
    </tbody>
  </table>

  <p style="font-size:0.85rem;color:#888;">
    Generated by AUDia LLM Gateway &mdash;
    edit <code>config/local/stack.override.yaml</code> to change hosts and ports.
  </p>
</body>
</html>
"""


def build_nginx_config(stack: StackConfig) -> str:
    return f"""pid .runtime/nginx.pid;
error_log .runtime/logs/nginx-error.log warn;

worker_processes  1;

events {{
    worker_connections  1024;
}}

http {{
    default_type  application/octet-stream;
    sendfile      on;
    tcp_nopush    on;
    tcp_nodelay   on;
    keepalive_timeout  65;

    access_log             .runtime/logs/nginx-access.log;
    client_body_temp_path  .runtime/temp/client_body;
    proxy_temp_path        .runtime/temp/proxy;
    fastcgi_temp_path      .runtime/temp/fastcgi;
    uwsgi_temp_path        .runtime/temp/uwsgi;
    scgi_temp_path         .runtime/temp/scgi;

    upstream litellm_upstream {{
        server {stack.network.litellm_host}:{stack.network.litellm_port};
        keepalive 16;
    }}

    upstream llamaswap_upstream {{
        server {stack.network.llamaswap_host}:{stack.network.llamaswap_port};
        keepalive 16;
    }}

    map $http_upgrade $connection_upgrade {{
        default upgrade;
        '' close;
    }}

    server {{
        listen       {stack.network.nginx_port};
        server_name  _;

        client_max_body_size 100m;

        location /v1/ {{
            proxy_pass http://litellm_upstream;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $connection_upgrade;
            proxy_buffering off;
            proxy_request_buffering off;
        }}

        location = /litellm {{
            return 301 /litellm/;
        }}

        location /litellm/ {{
            rewrite ^/litellm/(.*)$ /$1 break;
            proxy_pass http://litellm_upstream;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $connection_upgrade;
            proxy_buffering off;
            proxy_request_buffering off;
        }}

        location = /llamaswap {{
            return 301 /llamaswap/;
        }}

        location /llamaswap/ {{
            rewrite ^/llamaswap/(.*)$ /$1 break;
            proxy_pass http://llamaswap_upstream;
            proxy_redirect ~^/(.+)$ /llamaswap/$1;
            proxy_redirect / /llamaswap/;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $connection_upgrade;
            proxy_buffering off;
            proxy_request_buffering off;
        }}

        location = /health {{
            proxy_pass http://litellm_upstream/health;
        }}

        location = /llamaswap-health {{
            proxy_pass http://llamaswap_upstream/health;
        }}

        location = /ui {{
            return 301 /ui/;
        }}

        location /ui/ {{
            proxy_pass http://litellm_upstream;
            proxy_redirect http://{stack.network.litellm_host}:{stack.network.litellm_port}/ /;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $connection_upgrade;
            proxy_buffering off;
            proxy_request_buffering off;
        }}

        location = / {{
            root config/generated/nginx;
            try_files /index.html =404;
            default_type text/html;
        }}
    }}
}}
"""


def build_systemd_config(stack: StackConfig) -> str:
    root = stack.root.resolve()
    script_path = root / "scripts" / "AUDiaLLMGateway.sh"
    return f"""[Unit]
Description={stack.systemd.description}
After={stack.systemd.after}

[Service]
Type=simple
User={stack.systemd.user}
Group={stack.systemd.group}
WorkingDirectory={root}
ExecStart={script_path} start
ExecStop={script_path} stop
Restart={stack.systemd.restart}

[Install]
WantedBy=multi-user.target
"""


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
        "# Generated from config/project/models.base.yaml, config/local/models.override.yaml,\n"
        "# config/project/llama-swap.base.yaml, and config/local/llama-swap.override.yaml.\n"
        "# Regenerate with:\n"
        "#   python -m src.launcher.process_manager generate-configs\n"
    )
    return _write_yaml_with_header(output_path, header, payload)


def write_litellm_config(root: str | Path) -> Path:
    stack = load_stack_config(root)
    output_path = stack.root / stack.litellm.generated_config_path
    payload = build_litellm_config(stack)
    header = (
        "# Generated from config/project/models.base.yaml, config/local/models.override.yaml,\n"
        "# config/project/stack.base.yaml, and config/local/stack.override.yaml.\n"
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


def write_nginx_config(root: str | Path) -> Path:
    stack = load_stack_config(root)
    output_path = stack.root / str(stack.reverse_proxy.get("nginx", {}).get("config_path", "config/generated/nginx/nginx.conf"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# Generated from config/project/stack.base.yaml and config/local/stack.override.yaml.\n"
        "# Hosts and ports are resolved from the central network section.\n"
        "# Regenerate with:\n"
        "#   python -m src.launcher.process_manager generate-configs\n\n"
    )
    output_path.write_text(header + build_nginx_config(stack), encoding="utf-8")
    landing_path = output_path.parent / "index.html"
    landing_path.write_text(build_nginx_landing_page(stack), encoding="utf-8")
    return output_path


def write_systemd_config(root: str | Path) -> Path | None:
    stack = load_stack_config(root)
    if not stack.systemd.enabled:
        return None
    output_path = stack.root / "config" / "generated" / "systemd" / f"{stack.systemd.service_name}.service"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# Generated from config/project/stack.base.yaml and config/local/stack.override.yaml.\n"
        "# Regenerate with:\n"
        "#   python -m src.launcher.process_manager generate-configs\n\n"
    )
    output_path.write_text(header + build_systemd_config(stack), encoding="utf-8")
    return output_path


def validate_layered_configs(root: str | Path) -> dict[str, Any]:
    llama_base, llama_local, _ = load_llama_swap_source_config(root)
    mcp_base, mcp_local, _ = load_mcp_registry(root)
    models_base, models_local, _ = load_model_catalog(root)
    stack_base, stack_local, _ = load_layered_yaml(root, "config/project/stack.base.yaml", "config/local/stack.override.yaml")
    state_path = stack_base.get("project", {}).get("installer", {}).get("state_path", "state/install-state.json")
    return {
        "ok": True,
        "type_conflicts": {
            "stack": type_conflicts(stack_base, stack_local),
            "llama_swap": type_conflicts(llama_base, llama_local),
            "mcp": type_conflicts(mcp_base, mcp_local),
            "models": type_conflicts(models_base, models_local),
        },
        "state_path": str(Path(root).resolve() / state_path),
    }


def write_generated_configs(root: str | Path) -> dict[str, Path]:
    return {
        "llama_swap": write_llama_swap_config(root),
        "litellm": write_litellm_config(root),
        "mcp_client": write_mcp_client_config(root),
        "nginx": write_nginx_config(root),
        "systemd": write_systemd_config(root),
    }
