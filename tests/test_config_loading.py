from pathlib import Path

import yaml

from src.launcher.config_loader import (
    load_backend_runtime_catalog,
    load_layered_yaml,
    load_model_catalog,
    load_stack_config,
)


def test_load_stack_config_from_repo_fixture() -> None:
    root = Path(__file__).resolve().parents[1]
    config = load_stack_config(root)

    assert config.llama_swap.port == 41080
    assert config.litellm.port == 4000
    assert config.vllm.port == 8000
    assert config.network.nginx_port == 8080
    assert config.project.state_path == "state/install-state.json"
    assert config.component_settings["llama_cpp"]["default_profiles"]["windows"] == "windows-vulkan"
    assert "linux-rocm" in config.component_settings["llama_cpp"]["profiles"]
    assert "macos-metal" in config.component_settings["llama_cpp"]["profiles"]
    model_labels = [model.label for model in config.published_models]
    assert model_labels[0] == "local/qwen27_fast"
    assert "local/qwen122_smart" in model_labels


def test_load_stack_config_includes_vllm_models_when_enabled(monkeypatch) -> None:
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("AUDIA_ENABLE_VLLM", "true")
    monkeypatch.setenv("VLLM_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")

    config = load_stack_config(root)

    assert config.vllm.enabled is True
    assert any(model.label == "local/vllm_default" for model in config.published_models)


def test_load_layered_yaml_merges_project_and_local(tmp_path: Path) -> None:
    project_dir = tmp_path / "config" / "project"
    local_dir = tmp_path / "config" / "local"
    project_dir.mkdir(parents=True)
    local_dir.mkdir(parents=True)

    (project_dir / "stack.base.yaml").write_text(
        yaml.safe_dump(
            {
                "models": {
                    "project_config_path": "config/project/models.base.yaml",
                    "local_override_path": "config/local/models.override.yaml",
                },
                "routing": {"notes": ["project"]},
            }
        ),
        encoding="utf-8",
    )
    (project_dir / "models.base.yaml").write_text(
        yaml.safe_dump(
            {
                "model_profiles": {
                    "base": {
                        "mode": "chat",
                        "deployments": {
                            "llamacpp": {
                                "label": "local/base",
                                "llama_swap_model": "base",
                                "backend_model_name": "base",
                            }
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (local_dir / "models.override.yaml").write_text(yaml.safe_dump({}), encoding="utf-8")
    (local_dir / "stack.override.yaml").write_text(
        yaml.safe_dump(
            {
                "routing": {"notes": ["local"]},
            }
        ),
        encoding="utf-8",
    )

    _, _, merged = load_layered_yaml(tmp_path, "config/project/stack.base.yaml", "config/local/stack.override.yaml")
    assert merged["models"]["project_config_path"] == "config/project/models.base.yaml"
    assert merged["routing"]["notes"] == ["local"]


def test_load_layered_yaml_merges_optional_private_overlay(tmp_path: Path) -> None:
    project_dir = tmp_path / "config" / "project"
    local_dir = tmp_path / "config" / "local"
    project_dir.mkdir(parents=True)
    local_dir.mkdir(parents=True)

    (project_dir / "stack.base.yaml").write_text(
        yaml.safe_dump(
            {
                "routing": {"notes": ["project"]},
                "network": {"services": {"litellm": {"port": 4000}}},
            }
        ),
        encoding="utf-8",
    )
    (local_dir / "stack.override.yaml").write_text(
        yaml.safe_dump(
            {
                "routing": {"notes": ["local"]},
                "network": {"services": {"litellm": {"host": "127.0.0.1"}}},
            }
        ),
        encoding="utf-8",
    )
    (local_dir / "stack.private.yaml").write_text(
        yaml.safe_dump(
            {
                "routing": {"notes": ["private"]},
                "network": {"services": {"litellm": {"port": 41000}}},
            }
        ),
        encoding="utf-8",
    )

    _, overlay, merged = load_layered_yaml(tmp_path, "config/project/stack.base.yaml", "config/local/stack.override.yaml")

    assert overlay["routing"]["notes"] == ["private"]
    assert overlay["network"]["services"]["litellm"]["host"] == "127.0.0.1"
    assert merged["network"]["services"]["litellm"]["port"] == 41000


def test_load_model_catalog_from_repo_fixture() -> None:
    root = Path(__file__).resolve().parents[1]
    _, _, catalog = load_model_catalog(root)
    config = load_stack_config(root)

    assert "qwen27_fast" in catalog["model_profiles"]
    assert catalog["model_profiles"]["qwen27_fast"]["defaults"]["context_preset"] == "96k"
    assert catalog["model_profiles"]["qwen27_fast"]["deployments"]["llamacpp_vulkan"]["label"] == "local/qwen27_fast"
    assert "coding_active" in catalog["load_groups"]
    assert config.published_models[0].source_page_url == "https://huggingface.co/mradermacher/Qwen3.5-27B-GGUF"
    assert config.published_models[0].revision == "main"
    assert config.published_models[0].model_filename == "Qwen3.5-27B.Q6_K.gguf"
    assert "coding_active" in config.published_models[0].load_groups


def test_published_model_filename_defaults_from_model_file(tmp_path: Path) -> None:
    project_dir = tmp_path / "config" / "project"
    local_dir = tmp_path / "config" / "local"
    project_dir.mkdir(parents=True)
    local_dir.mkdir(parents=True)

    (project_dir / "stack.base.yaml").write_text(
        yaml.safe_dump(
            {
                "network": {
                    "services": {
                        "llama_swap": {"port": 41080},
                        "litellm": {"port": 4000},
                        "vllm": {"port": 8000},
                        "nginx": {"port": 8080},
                    }
                },
                "llama_swap": {},
                "litellm": {},
                "mcp": {},
                "routing": {},
                "reverse_proxy": {},
                "nginx": {"enabled": False},
                "systemd": {"enabled": False},
                "project": {"installer": {"state_path": "state/install-state.json"}},
                "models": {
                    "project_config_path": "config/project/models.base.yaml",
                    "local_override_path": "config/local/models.override.yaml",
                },
                "backend_runtime": {
                    "project_config_path": "config/project/backend-runtime.base.yaml",
                    "local_override_path": "config/local/backend-runtime.override.yaml",
                },
                "backend_support": {
                    "project_config_path": "config/project/backend-support.base.yaml",
                    "local_override_path": "config/local/backend-support.override.yaml",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (project_dir / "models.base.yaml").write_text(
        yaml.safe_dump(
            {
                "frameworks": {
                    "llama_cpp": {
                        "type": "llama_cpp",
                        "supports": ["llama-swap", "litellm"],
                        "llama_swap": {
                            "executable_macro": "llama-server-vulkan",
                            "server_args_macro": "server-args",
                            "model_path_macro": "model-path",
                            "mmproj_path_macro": "mmproj-path",
                            "context_macro_name_template": "context-{alias}-args",
                            "context_arg_template": "--ctx-size {tokens}",
                        },
                    }
                },
                "presets": {
                    "contexts": {"32k": {"tokens": 32768}},
                    "deployment_profiles": {
                        "llamacpp_vulkan_single": {
                            "framework": "llama_cpp",
                            "transport": "llama-swap",
                            "executable_macro": "llama-server-vulkan",
                            "llama_cpp_options": {"device": "Vulkan0"},
                        }
                    },
                },
                "model_profiles": {
                    "artifact_defaults": {
                        "mode": "chat",
                        "purpose": "filename default test",
                        "defaults": {"context_preset": "32k"},
                        "artifacts": {
                            "revision": "main",
                            "model_file": "demo/path/model-a.gguf",
                            "model_url": "https://example.invalid/model-a.gguf",
                            "mmproj_file": "demo/path/mmproj-b.gguf",
                            "mmproj_url": "https://example.invalid/mmproj-b.gguf",
                            "source_page_url": "https://example.invalid/source",
                        },
                        "deployments": {
                            "llamacpp_vulkan": {
                                "label": "local/artifact_defaults",
                                "profile": "llamacpp_vulkan_single",
                                "llama_swap_model": "artifact-defaults",
                            }
                        },
                    }
                },
                "load_groups": {},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (project_dir / "backend-runtime.base.yaml").write_text(yaml.safe_dump({"variants": {}}, sort_keys=False), encoding="utf-8")
    (project_dir / "backend-support.base.yaml").write_text(yaml.safe_dump({"rules": []}, sort_keys=False), encoding="utf-8")
    (local_dir / "stack.override.yaml").write_text(yaml.safe_dump({}), encoding="utf-8")
    (local_dir / "models.override.yaml").write_text(yaml.safe_dump({}), encoding="utf-8")
    (local_dir / "backend-runtime.override.yaml").write_text(yaml.safe_dump({}), encoding="utf-8")
    (local_dir / "backend-support.override.yaml").write_text(yaml.safe_dump({}), encoding="utf-8")

    config = load_stack_config(tmp_path)
    model = next(item for item in config.published_models if item.label == "local/artifact_defaults")

    assert model.model_filename == "model-a.gguf"
    assert model.mmproj_filename == "mmproj-b.gguf"


def test_load_backend_runtime_catalog_from_repo_fixture() -> None:
    root = Path(__file__).resolve().parents[1]
    _, _, catalog = load_backend_runtime_catalog(root)
    config = load_stack_config(root)

    assert "variants" in catalog
    assert "profiles" in catalog
    assert "rocm" in catalog["variants"]
    assert "build-rocm-gfx" in catalog["profiles"]
    assert config.backend_runtime_project_config_path == "config/project/backend-runtime.base.yaml"
    assert config.backend_runtime_local_override_path == "config/local/backend-runtime.override.yaml"
