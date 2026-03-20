from pathlib import Path

import json
import yaml

from src.launcher.config_loader import (
    build_llama_swap_config,
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
    assert "model_url" in config["model_list"][0]["model_info"]
    assert "source_page_url" in config["model_list"][0]["model_info"]
    assert config["model_list"][0]["model_info"]["revision"] == "main"
    assert config["model_list"][0]["model_info"]["model_filename"] == "Qwen3.5-27B.Q6_K.gguf"
    assert "coding_active" in config["model_list"][0]["model_info"]["load_groups"]
    assert len(config["model_list"][1]["model_info"]["additional_model_urls"]) == 2


def test_build_litellm_config_adds_vllm_routes_when_enabled(monkeypatch) -> None:
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("AUDIA_ENABLE_VLLM", "true")
    monkeypatch.setenv("VLLM_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")

    stack = load_stack_config(root)
    config = build_litellm_config(stack)

    vllm_entry = next(item for item in config["model_list"] if item["model_name"] == "local/vllm_default")
    assert vllm_entry["litellm_params"]["api_base"] == "http://127.0.0.1:8000/v1"
    assert "extra_headers" not in vllm_entry["litellm_params"]
    assert vllm_entry["model_info"]["framework"] == "vllm"
    assert vllm_entry["model_info"]["transport"] == "direct"


def test_write_generated_configs_writes_yaml_and_json(tmp_path: Path) -> None:
    source_root = Path(__file__).resolve().parents[1]
    for rel_path in [
        "config/project/stack.base.yaml",
        "config/project/llama-swap.base.yaml",
        "config/project/models.base.yaml",
        "config/project/mcp.base.yaml",
        "config/local/stack.override.yaml",
        "config/local/llama-swap.override.yaml",
        "config/local/models.override.yaml",
        "config/local/mcp.override.yaml",
    ]:
        source = source_root / rel_path
        target = tmp_path / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    output = write_generated_configs(tmp_path)
    litellm_path = tmp_path / "config" / "generated" / "litellm" / "litellm.config.yaml"
    vllm_path = tmp_path / "config" / "generated" / "vllm" / "vllm.config.json"
    mcp_path = tmp_path / "config" / "generated" / "mcp" / "litellm.mcp.client.json"
    nginx_path = tmp_path / "config" / "generated" / "nginx" / "nginx.conf"
    litellm_data = yaml.safe_load(litellm_path.read_text(encoding="utf-8").split("\n", 3)[3])
    mcp_data = json.loads(mcp_path.read_text(encoding="utf-8"))

    assert output["llama_swap"].name == "llama-swap.generated.yaml"
    assert litellm_data["litellm_settings"]["master_key"] == "os.environ/LITELLM_MASTER_KEY"
    assert vllm_path.exists()
    assert "litellm-gateway" in mcp_data["servers"]
    assert nginx_path.exists()


def test_build_llama_swap_config_contains_generated_catalog_models() -> None:
    root = Path(__file__).resolve().parents[1]
    stack = load_stack_config(root)
    config = build_llama_swap_config(stack)

    assert "InternVL3-5-GPT-OSS-20B@gpu2" not in config["models"]
    assert config["macros"]["gpu1-vulkan-args"] == "--device Vulkan0 --split-mode none --parallel 1 --gpu-layers all"
    assert config["macros"]["gpu1-rocm-args"] == "--device ROCm1 --split-mode none --parallel 1 --gpu-layers all"
    assert config["macros"]["cache-q8-args"] == "--cache-type-k q8_0 --cache-type-v q8_0"
    assert config["macros"]["qwen-nothink-args"] == '--reasoning-budget 0 --reasoning-format none --chat-template-kwargs {"enable_thinking":false}'
    generated_qwen = config["models"]["qwen3.5-27b-(96k-Q6)"]["cmd"]
    generated_qwen_vision = config["models"]["qwen3-5-4b-ud-q5-k-xl-vision"]["cmd"]
    assert "${context-96k-args}" in generated_qwen
    assert "${gpu1-vulkan-args}" in generated_qwen
    assert "${coder_args}" in generated_qwen
    assert generated_qwen_vision.startswith("${llama-server-vulkan} ")
    assert "${gpu1-vulkan-args}" in generated_qwen_vision
    assert config["models"]["tiny-qwen25-test"]["cmd"].startswith("${llama-server-rocm} ")
    assert "${gpu1-rocm-args}" in config["models"]["tiny-qwen25-test"]["cmd"]
    assert "coding_active" in config["groups"]
    assert "qwen3.5-27b-(96k-Q6)" in config["groups"]["coding_active"]["members"]


def test_write_generated_configs_uses_central_network_bindings(tmp_path: Path) -> None:
    source_root = Path(__file__).resolve().parents[1]
    for rel_path in [
        "config/project/stack.base.yaml",
        "config/project/llama-swap.base.yaml",
        "config/project/models.base.yaml",
        "config/project/mcp.base.yaml",
        "config/local/stack.override.yaml",
        "config/local/llama-swap.override.yaml",
        "config/local/models.override.yaml",
        "config/local/mcp.override.yaml",
    ]:
        source = source_root / rel_path
        target = tmp_path / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    stack_override = tmp_path / "config" / "local" / "stack.override.yaml"
    stack_override.write_text(
        yaml.safe_dump(
            {
                "network": {
                    "backend_bind_host": "0.0.0.0",
                    "services": {
                        "llama_swap": {"host": "10.0.0.5", "port": 42080},
                        "litellm": {"host": "10.0.0.5", "port": 44000},
                        "nginx": {"host": "gateway.local", "port": 8088},
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    write_generated_configs(tmp_path)
    litellm_data = yaml.safe_load((tmp_path / "config" / "generated" / "litellm" / "litellm.config.yaml").read_text(encoding="utf-8").split("\n", 3)[3])
    nginx_text = (tmp_path / "config" / "generated" / "nginx" / "nginx.conf").read_text(encoding="utf-8")
    llama_swap_text = (tmp_path / "config" / "generated" / "llama-swap" / "llama-swap.generated.yaml").read_text(encoding="utf-8")

    assert litellm_data["model_list"][0]["litellm_params"]["api_base"] == "http://10.0.0.5:42080/v1"
    assert "server 10.0.0.5:44000;" in nginx_text
    assert "server 10.0.0.5:42080;" in nginx_text
    assert "listen       8088;" in nginx_text
    assert "server_name  gateway.local;" in nginx_text
    assert "--host 0.0.0.0" in llama_swap_text


def test_write_generated_configs_uses_vllm_network_bindings_when_enabled(tmp_path: Path, monkeypatch) -> None:
    source_root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("AUDIA_ENABLE_VLLM", "true")
    monkeypatch.setenv("VLLM_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
    for rel_path in [
        "config/project/stack.base.yaml",
        "config/project/llama-swap.base.yaml",
        "config/project/models.base.yaml",
        "config/project/mcp.base.yaml",
        "config/local/stack.override.yaml",
        "config/local/llama-swap.override.yaml",
        "config/local/models.override.yaml",
        "config/local/mcp.override.yaml",
    ]:
        source = source_root / rel_path
        target = tmp_path / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    stack_override = tmp_path / "config" / "local" / "stack.override.yaml"
    stack_override.write_text(
        yaml.safe_dump(
            {
                "network": {
                    "services": {
                        "vllm": {"host": "10.0.0.6", "port": 48000},
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    write_generated_configs(tmp_path)
    litellm_data = yaml.safe_load((tmp_path / "config" / "generated" / "litellm" / "litellm.config.yaml").read_text(encoding="utf-8").split("\n", 3)[3])
    nginx_text = (tmp_path / "config" / "generated" / "nginx" / "nginx.conf").read_text(encoding="utf-8")
    vllm_data = json.loads((tmp_path / "config" / "generated" / "vllm" / "vllm.config.json").read_text(encoding="utf-8"))

    vllm_entry = next(item for item in litellm_data["model_list"] if item["model_name"] == "local/vllm_default")
    assert vllm_entry["litellm_params"]["api_base"] == "http://10.0.0.6:48000/v1"
    assert "server 10.0.0.6:48000;" in nginx_text
    assert vllm_data["service"]["api_base"] == "http://10.0.0.6:48000/v1"


def test_context_alias_can_generate_macro_without_explicit_llama_swap_macro(tmp_path: Path) -> None:
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

    (tmp_path / "config" / "project" / "models.base.yaml").write_text(
        yaml.safe_dump(
            {
                "frameworks": {
                    "llama_cpp": {
                        "llama_swap": {
                            "executable_macro": "llama-server",
                            "server_args_macro": "server-args",
                            "model_path_macro": "model-path",
                            "mmproj_path_macro": "mmproj-path",
                            "context_macro_name_template": "context-{alias}-args",
                            "context_arg_template": "--ctx-size {tokens}",
                        }
                    }
                },
                "presets": {
                    "contexts": {
                        "40k": {
                            "tokens": 40960,
                        }
                    },
                    "gpu_profiles": {
                        "gpu1": {
                            "llama_swap_macro": "gpu1-args",
                            "llama_cpp_options": {
                                "device": "Vulkan0",
                                "split_mode": "none",
                            },
                        },
                    },
                    "runtime_profiles": {},
                },
                "model_profiles": {
                    "alias_test": {
                        "defaults": {
                            "context_preset": "40k",
                            "gpu_preset": "gpu1",
                        },
                        "artifacts": {
                            "model_file": "AliasTest\\alias-test.gguf",
                        },
                        "deployments": {
                            "llamacpp_vulkan": {
                                "framework": "llama_cpp",
                                "transport": "llama-swap",
                                "llama_swap_model": "alias-test-model",
                            }
                        },
                    }
                },
                "exposures": [
                    {
                        "stable_name": "local/alias_test",
                        "model_profile": "alias_test",
                        "deployment": "llamacpp_vulkan",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "config" / "local" / "models.override.yaml").write_text(yaml.safe_dump({}), encoding="utf-8")

    stack = load_stack_config(tmp_path)
    config = build_llama_swap_config(stack)

    assert config["macros"]["context-40k-args"] == "--ctx-size 40960"
    assert config["macros"]["gpu1-args"] == "--device Vulkan0 --split-mode none"
    assert "${context-40k-args}" in config["models"]["alias-test-model"]["cmd"]
