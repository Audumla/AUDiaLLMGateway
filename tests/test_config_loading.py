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
    assert config.published_models[0].label == "local/qwen27_fast"
    assert any(model.label == "local/qwen122_smart" for model in config.published_models)


def test_local_llama_swap_override_stays_docker_free() -> None:
    root = Path(__file__).resolve().parents[1]
    local_override = (root / "config" / "local" / "llama-swap.override.yaml").read_text(encoding="utf-8")

    assert "/app/runtime-root" not in local_override
    assert "env LD_LIBRARY_PATH" not in local_override
    assert "VK_ICD_FILENAMES" not in local_override
    assert "/app/models/gguf" not in local_override


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


def test_load_layered_yaml_merges_private_overlay_after_local(tmp_path: Path) -> None:
    project_dir = tmp_path / "config" / "project"
    local_dir = tmp_path / "config" / "local"
    project_dir.mkdir(parents=True)
    local_dir.mkdir(parents=True)

    (project_dir / "stack.base.yaml").write_text(
        yaml.safe_dump({"network": {"services": {"litellm": {"port": 4000}}}}),
        encoding="utf-8",
    )
    (local_dir / "stack.override.yaml").write_text(
        yaml.safe_dump({"network": {"services": {"litellm": {"port": 4100}}}}),
        encoding="utf-8",
    )
    (local_dir / "stack.private.yaml").write_text(
        yaml.safe_dump({"network": {"services": {"litellm": {"port": 4200}}}}),
        encoding="utf-8",
    )

    _, local, merged = load_layered_yaml(tmp_path, "config/project/stack.base.yaml", "config/local/stack.override.yaml")

    assert local["network"]["services"]["litellm"]["port"] == 4200
    assert merged["network"]["services"]["litellm"]["port"] == 4200


def test_load_stack_config_uses_top_level_component_settings_from_private_overlay(tmp_path: Path) -> None:
    project_dir = tmp_path / "config" / "project"
    local_dir = tmp_path / "config" / "local"
    project_dir.mkdir(parents=True)
    local_dir.mkdir(parents=True)

    (project_dir / "stack.base.yaml").write_text(
        yaml.safe_dump(
            {
                "project": {"installer": {"state_path": "state/install-state.json"}},
                "install": {"venv_path": ".venv", "python_min_version": "3.11"},
                "network": {
                    "backend_bind_host": "127.0.0.1",
                    "base_path": "/audia/llmgateway",
                    "services": {
                        "llama_swap": {"host": "127.0.0.1", "port": 41080},
                        "litellm": {"host": "127.0.0.1", "port": 4000},
                        "vllm": {"host": "127.0.0.1", "port": 8000},
                        "nginx": {"port": 8080},
                    },
                },
                "llama_swap": {},
                "litellm": {},
                "mcp": {},
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
                "component_settings": {
                    "llama_cpp": {
                        "selected_profile": "windows-vulkan",
                        "profiles": {
                            "windows-vulkan": {
                                "platform": "windows",
                                "backend": "vulkan",
                                "asset_match_tokens": ["win", "vulkan", "x64"],
                            }
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (project_dir / "models.base.yaml").write_text(yaml.safe_dump({"model_profiles": {}}), encoding="utf-8")
    (project_dir / "backend-runtime.base.yaml").write_text(yaml.safe_dump({"variants": {}}), encoding="utf-8")
    (project_dir / "backend-support.base.yaml").write_text(yaml.safe_dump({"supports": {}}), encoding="utf-8")
    (local_dir / "stack.override.yaml").write_text(yaml.safe_dump({}), encoding="utf-8")
    (local_dir / "stack.private.yaml").write_text(
        yaml.safe_dump(
            {
                "component_settings": {
                    "llama_cpp": {
                        "selected_profile": "windows-vulkan-turboquant",
                        "profiles": {
                            "windows-vulkan-turboquant": {
                                "source_type": "git",
                                "git_ref": "tqp-v0.1.0",
                            }
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    config = load_stack_config(tmp_path)

    assert config.component_settings["llama_cpp"]["selected_profile"] == "windows-vulkan-turboquant"
    assert config.component_settings["llama_cpp"]["profiles"]["windows-vulkan"]["backend"] == "vulkan"
    assert config.component_settings["llama_cpp"]["profiles"]["windows-vulkan-turboquant"]["git_ref"] == "tqp-v0.1.0"


def test_load_model_catalog_from_repo_fixture() -> None:
    root = Path(__file__).resolve().parents[1]
    _, _, catalog = load_model_catalog(root)
    config = load_stack_config(root)

    assert "qwen27_fast" in catalog["model_profiles"]
    assert "qwen2b_validation" in catalog["model_profiles"]
    assert "qwen4b_validation" in catalog["model_profiles"]
    assert catalog["model_profiles"]["qwen27_fast"]["defaults"]["context_preset"] == "96k"
    assert catalog["model_profiles"]["qwen27_fast"]["deployments"]["llamacpp_vulkan"]["label"] == "local/qwen27_fast"
    assert (
        catalog["model_profiles"]["qwen2b_validation"]["deployments"]["llamacpp_cpu"]["label"]
        == "local/qwen2b_validation_cpu"
    )
    assert (
        catalog["model_profiles"]["qwen2b_validation"]["deployments"]["llamacpp_rocm"]["label"]
        == "local/qwen2b_validation_rocm"
    )
    assert (
        catalog["model_profiles"]["qwen4b_validation"]["deployments"]["llamacpp_cpu"]["label"]
        == "local/qwen4b_validation_cpu"
    )
    assert (
        catalog["model_profiles"]["qwen4b_validation"]["deployments"]["llamacpp_rocm"]["label"]
        == "local/qwen4b_validation_rocm"
    )
    assert "coding_active" in catalog["load_groups"]
    assert config.published_models[0].source_page_url == "https://huggingface.co/mradermacher/Qwen3.5-27B-GGUF"
    assert config.published_models[0].revision == "main"
    assert config.published_models[0].model_filename == "Qwen3.5-27B.Q6_K.gguf"
    assert config.published_models[0].source_type == "auto"
    assert "coding_active" in config.published_models[0].load_groups
    assert any(model.label == "local/qwen2b_validation_vulkan" for model in config.published_models)
    assert any(model.label == "local/qwen2b_validation_cpu" for model in config.published_models)
    assert any(model.label == "local/qwen2b_validation_rocm" for model in config.published_models)
    assert any(model.label == "local/qwen4b_validation_vulkan" for model in config.published_models)
    assert any(model.label == "local/qwen4b_validation_cpu" for model in config.published_models)
    assert any(model.label == "local/qwen4b_validation_rocm" for model in config.published_models)


def test_load_backend_runtime_catalog_from_repo_fixture() -> None:
    root = Path(__file__).resolve().parents[1]
    _, _, catalog = load_backend_runtime_catalog(root)
    config = load_stack_config(root)

    assert "variants" in catalog
    assert "sources" in catalog
    assert "builds" in catalog
    assert "rocm" in catalog["variants"]
    assert "rocm-gfx" in catalog["builds"]
    assert "ggml-release" in catalog["sources"]
    assert config.backend_runtime_project_config_path == "config/project/backend-runtime.base.yaml"
    assert config.backend_runtime_local_override_path == "config/local/backend-runtime.override.yaml"


def test_load_backend_runtime_catalog_merges_private_overlay(tmp_path: Path) -> None:
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
                "backend_runtime": {
                    "project_config_path": "config/project/backend-runtime.base.yaml",
                    "local_override_path": "config/local/backend-runtime.override.yaml",
                },
            }
        ),
        encoding="utf-8",
    )
    (project_dir / "models.base.yaml").write_text(yaml.safe_dump({}), encoding="utf-8")
    (project_dir / "backend-runtime.base.yaml").write_text(
        yaml.safe_dump({"variants": {"vulkan": {"backend": "vulkan", "macro": "llama-server-vulkan"}}}),
        encoding="utf-8",
    )
    (local_dir / "models.override.yaml").write_text(yaml.safe_dump({}), encoding="utf-8")
    (local_dir / "backend-runtime.override.yaml").write_text(
        yaml.safe_dump({"variants": {"vulkan": {"enabled": False}}}),
        encoding="utf-8",
    )
    (local_dir / "backend-runtime.private.yaml").write_text(
        yaml.safe_dump(
            {
                "variants": {
                    "vulkan-private": {
                        "backend": "vulkan",
                        "macro": "llama-server-vulkan-private",
                        "runtime_subdir": "vulkan/private",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    _, local, merged = load_backend_runtime_catalog(tmp_path)

    assert local["variants"]["vulkan"]["enabled"] is False
    assert "vulkan-private" in local["variants"]
    assert merged["variants"]["vulkan-private"]["macro"] == "llama-server-vulkan-private"
