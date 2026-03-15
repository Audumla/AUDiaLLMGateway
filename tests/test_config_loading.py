from pathlib import Path

import yaml

from src.launcher.config_loader import load_layered_yaml, load_stack_config


def test_load_stack_config_from_repo_fixture() -> None:
    root = Path(__file__).resolve().parents[1]
    config = load_stack_config(root)

    assert config.llama_swap.port == 41080
    assert config.litellm.port == 4000
    assert config.project.state_path == "state/install-state.json"
    assert [model.stable_name for model in config.published_models][:2] == [
        "local/qwen27_fast",
        "local/qwen122_smart",
    ]


def test_load_layered_yaml_merges_project_and_local(tmp_path: Path) -> None:
    project_dir = tmp_path / "config" / "project"
    local_dir = tmp_path / "config" / "local"
    project_dir.mkdir(parents=True)
    local_dir.mkdir(parents=True)

    (project_dir / "stack.base.yaml").write_text(
        yaml.safe_dump(
            {
                "published_models": [{"stable_name": "local/base", "llama_swap_model": "base"}],
                "routing": {"notes": ["project"]},
            }
        ),
        encoding="utf-8",
    )
    (local_dir / "stack.override.yaml").write_text(
        yaml.safe_dump(
            {
                "routing": {"notes": ["local"]},
            }
        ),
        encoding="utf-8",
    )

    _, _, merged = load_layered_yaml(tmp_path, "config/project/stack.base.yaml", "config/local/stack.override.yaml")
    assert merged["published_models"][0]["stable_name"] == "local/base"
    assert merged["routing"]["notes"] == ["local"]
