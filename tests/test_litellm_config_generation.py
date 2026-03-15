from pathlib import Path

import json
import yaml

from src.launcher.config_loader import (
    build_litellm_config,
    load_stack_config,
    write_generated_configs,
)


def test_build_litellm_config_contains_expected_models() -> None:
    root = Path(__file__).resolve().parents[1]
    stack = load_stack_config(root)
    config = build_litellm_config(stack)

    model_names = [entry["model_name"] for entry in config["model_list"]]
    assert model_names[:2] == ["local/qwen27_fast", "local/qwen122_smart"]
    assert config["model_list"][0]["litellm_params"]["api_base"] == "http://127.0.0.1:41080/v1"
    assert config["model_list"][0]["litellm_params"]["extra_headers"]["X-LLAMA-SWAP-MODEL"] == "qwen3.5-27b-(96k-Q6)"


def test_write_generated_configs_writes_yaml_and_json(tmp_path: Path) -> None:
    source_root = Path(__file__).resolve().parents[1]
    for rel_path in [
        "config/project/stack.base.yaml",
        "config/project/llama-swap.base.yaml",
        "config/project/mcp.base.yaml",
        "config/local/stack.override.yaml",
        "config/local/llama-swap.override.yaml",
        "config/local/mcp.override.yaml",
    ]:
        source = source_root / rel_path
        target = tmp_path / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    output = write_generated_configs(tmp_path)
    litellm_path = tmp_path / "config" / "generated" / "litellm.config.yaml"
    mcp_path = tmp_path / "config" / "generated" / "litellm.mcp.client.json"
    litellm_data = yaml.safe_load(litellm_path.read_text(encoding="utf-8").split("\n", 3)[3])
    mcp_data = json.loads(mcp_path.read_text(encoding="utf-8"))

    assert output["llama_swap"].name == "llama-swap.generated.yaml"
    assert litellm_data["litellm_settings"]["master_key"] == "os.environ/LITELLM_MASTER_KEY"
    assert "litellm-gateway" in mcp_data["servers"]

