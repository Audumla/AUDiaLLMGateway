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
    assert [model.label for model in config.published_models][:2] == [
        "local/qwen27_fast",
        "local/qwen122_smart",
    ]


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


def test_load_backend_runtime_catalog_from_repo_fixture() -> None:
    root = Path(__file__).resolve().parents[1]
    _, _, catalog = load_backend_runtime_catalog(root)
    config = load_stack_config(root)

    assert "variants" in catalog
    assert "profiles" in catalog
    assert "rocm" in catalog["variants"]
    assert "build-rocm-gfx1030-gfx1100" in catalog["profiles"]
    assert config.backend_runtime_project_config_path == "config/project/backend-runtime.base.yaml"
    assert config.backend_runtime_local_override_path == "config/local/backend-runtime.override.yaml"
