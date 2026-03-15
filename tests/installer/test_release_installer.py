from pathlib import Path

import yaml

from src.installer.release_installer import resolve_component_selection
from src.launcher.config_loader import validate_layered_configs


def test_resolve_component_selection_includes_required_and_defaults() -> None:
    manifest = {
        "components": {
            "python_runtime": {"required": True, "default_enabled": True},
            "gateway_python_deps": {"required": True, "default_enabled": True},
            "nginx": {"required": False, "default_enabled": False},
        }
    }
    selected = resolve_component_selection(manifest, ["nginx"])
    assert selected == ["python_runtime", "gateway_python_deps", "nginx"]


def test_validate_layered_configs_reports_type_conflicts(tmp_path: Path) -> None:
    for rel_path, payload in {
        "config/project/stack.base.yaml": {"published_models": [{"stable_name": "local/base", "llama_swap_model": "base"}]},
        "config/local/stack.override.yaml": {"published_models": {"bad": "type"}},
        "config/project/llama-swap.base.yaml": {"models": {}},
        "config/local/llama-swap.override.yaml": {"models": []},
        "config/project/mcp.base.yaml": {"servers": []},
        "config/local/mcp.override.yaml": {"servers": {"bad": "type"}},
    }.items():
        target = tmp_path / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(yaml.safe_dump(payload), encoding="utf-8")

    report = validate_layered_configs(tmp_path)
    assert "published_models" in report["type_conflicts"]["stack"]
    assert "models" in report["type_conflicts"]["llama_swap"]
    assert "servers" in report["type_conflicts"]["mcp"]
