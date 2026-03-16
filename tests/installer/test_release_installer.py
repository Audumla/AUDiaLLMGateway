from pathlib import Path

import yaml

from src.installer.release_installer import find_release_asset, resolve_component_selection, resolve_llama_cpp_profile
from src.launcher.config_loader import validate_layered_configs


def test_resolve_component_selection_includes_required_and_defaults() -> None:
    manifest = {
        "components": {
            "python_runtime": {"required": True, "default_enabled": True},
            "gateway_python_deps": {"required": True, "default_enabled": True},
            "llama_cpp": {"required": True, "default_enabled": True},
            "nginx": {"required": False, "default_enabled": False},
        }
    }
    selected = resolve_component_selection(manifest, ["nginx"])
    assert selected == ["python_runtime", "gateway_python_deps", "llama_cpp", "nginx"]


def test_find_release_asset_matches_all_tokens() -> None:
    metadata = {
        "assets": [
            {"name": "llama-b9999-bin-win-vulkan-x64.zip", "browser_download_url": "https://example.invalid/vulkan.zip"},
            {"name": "llama-b9999-bin-win-cpu-x64.zip", "browser_download_url": "https://example.invalid/cpu.zip"},
        ]
    }
    asset = find_release_asset(metadata, ["win", "vulkan", "x64"])
    assert asset["browser_download_url"] == "https://example.invalid/vulkan.zip"


def test_resolve_llama_cpp_profile_uses_platform_default() -> None:
    settings = {
        "selected_profile": "auto",
        "default_profiles": {
            "windows": "windows-vulkan",
            "linux": "linux-rocm",
            "macos": "macos-metal",
        },
        "profiles": {
            "windows-vulkan": {
                "platform": "windows",
                "backend": "vulkan",
                "asset_match_tokens": ["win", "vulkan", "x64"],
            },
            "linux-rocm": {
                "platform": "linux",
                "backend": "rocm",
                "asset_match_tokens": ["linux", "rocm", "x64"],
            },
            "macos-metal": {
                "platform": "macos",
                "backend": "metal",
                "asset_match_tokens": ["macos", "metal"],
            },
        },
    }

    profile_name, profile = resolve_llama_cpp_profile(settings, "linux")
    assert profile_name == "linux-rocm"
    assert profile["backend"] == "rocm"


def test_resolve_llama_cpp_profile_rejects_wrong_platform() -> None:
    settings = {
        "selected_profile": "windows-vulkan",
        "profiles": {
            "windows-vulkan": {
                "platform": "windows",
                "backend": "vulkan",
                "asset_match_tokens": ["win", "vulkan", "x64"],
            }
        },
    }

    try:
        resolve_llama_cpp_profile(settings, "macos")
    except RuntimeError as exc:
        assert "targets platform 'windows'" in str(exc)
    else:
        raise AssertionError("Expected wrong-platform llama.cpp profile selection to fail")


def test_validate_layered_configs_reports_type_conflicts(tmp_path: Path) -> None:
    for rel_path, payload in {
        "config/project/stack.base.yaml": {
            "models": {
                "project_config_path": "config/project/models.base.yaml",
                "local_override_path": "config/local/models.override.yaml",
            }
        },
        "config/local/stack.override.yaml": {"models": ["bad-type"]},
        "config/project/llama-swap.base.yaml": {"models": {}},
        "config/local/llama-swap.override.yaml": {"models": []},
        "config/project/models.base.yaml": {"exposures": [], "model_profiles": {}},
        "config/local/models.override.yaml": {"exposures": {"bad": "type"}},
        "config/project/mcp.base.yaml": {"servers": []},
        "config/local/mcp.override.yaml": {"servers": {"bad": "type"}},
    }.items():
        target = tmp_path / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(yaml.safe_dump(payload), encoding="utf-8")

    report = validate_layered_configs(tmp_path)
    assert "models" in report["type_conflicts"]["stack"]
    assert "models" in report["type_conflicts"]["llama_swap"]
    assert "exposures" in report["type_conflicts"]["models"]
    assert "servers" in report["type_conflicts"]["mcp"]
