from pathlib import Path

import json
import yaml

from src.launcher.config_loader import (
    build_llama_swap_config,
    build_litellm_config,
    build_vllm_config,
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


def test_build_vllm_config_uses_model_catalog_runtime_overrides(monkeypatch) -> None:
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("AUDIA_ENABLE_VLLM", "true")
    monkeypatch.setenv("VLLM_MODEL", "Qwen/Qwen3-0.6B")
    monkeypatch.setenv("VLLM_GPU_MEM", "0.91")
    monkeypatch.setenv("VLLM_MAX_LEN", "8192")
    monkeypatch.setenv("VLLM_TENSOR_PARALLEL_SIZE", "1")
    monkeypatch.setenv("VLLM_PIPELINE_PARALLEL_SIZE", "1")
    monkeypatch.setenv("VLLM_VISIBLE_DEVICES", "")

    stack = load_stack_config(root)
    config = build_vllm_config(stack)
    startup = config["startup"]

    assert startup["model"] == "Qwen/Qwen3-0.6B"
    assert startup["gpu_memory_utilization"] == 0.91
    assert startup["max_model_len"] == 8192
    assert startup["tensor_parallel_size"] == 1
    assert startup["pipeline_parallel_size"] == 1
    assert "visible_devices" in startup
    assert "extra_args" in startup


def test_build_vllm_config_supports_vllm_preset(tmp_path: Path, monkeypatch) -> None:
    source_root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("AUDIA_ENABLE_VLLM", "true")
    monkeypatch.setenv("VLLM_MODEL", "Qwen/Qwen3-0.6B")
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

    models_override = tmp_path / "config" / "local" / "models.override.yaml"
    data = yaml.safe_load(models_override.read_text(encoding="utf-8"))
    data.setdefault("presets", {}).setdefault("vllm_profiles", {})["dual_split"] = {
        "tensor_parallel_size": 2,
        "pipeline_parallel_size": 1,
    }
    data["model_profiles"]["vllm_default"]["deployments"]["vllm_primary"]["vllm_preset"] = "dual_split"
    data["model_profiles"]["vllm_default"]["deployments"]["vllm_primary"]["vllm"] = {
        "visible_devices": "0,1",
    }
    models_override.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    stack = load_stack_config(tmp_path)
    config = build_vllm_config(stack)
    startup = config["startup"]

    assert startup["tensor_parallel_size"] == 2
    assert startup["pipeline_parallel_size"] == 1
    assert startup["visible_devices"] == "0,1"


def test_build_vllm_config_supports_gpu_profile_backend_block(tmp_path: Path, monkeypatch) -> None:
    source_root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("AUDIA_ENABLE_VLLM", "true")
    monkeypatch.setenv("VLLM_MODEL", "Qwen/Qwen3-0.6B")
    monkeypatch.setenv("VLLM_BACKEND", "rocm")
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

    models_override = tmp_path / "config" / "local" / "models.override.yaml"
    data = yaml.safe_load(models_override.read_text(encoding="utf-8"))
    data.setdefault("presets", {}).setdefault("deployment_profiles", {})["vllm_split_tp2"] = {
        "framework": "vllm",
        "transport": "direct",
        "vllm_backend": "rocm",
        "vllm": {
            "tensor_parallel_size": 2,
            "pipeline_parallel_size": 1,
            "visible_devices": "0,1",
        },
    }
    data["model_profiles"]["vllm_default"]["deployments"]["vllm_primary"]["profile"] = "vllm_split_tp2"
    models_override.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    stack = load_stack_config(tmp_path)
    config = build_vllm_config(stack)
    startup = config["startup"]

    assert startup["tensor_parallel_size"] == 2
    assert startup["pipeline_parallel_size"] == 1
    assert startup["visible_devices"] == "0,1"


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
    backend_catalog_path = tmp_path / "config" / "generated" / "llama-swap" / "backend-runtime.catalog.json"
    mcp_path = tmp_path / "config" / "generated" / "mcp" / "litellm.mcp.client.json"
    nginx_path = tmp_path / "config" / "generated" / "nginx" / "nginx.conf"
    nginx_index_path = tmp_path / "config" / "generated" / "nginx" / "index.html"
    litellm_data = yaml.safe_load(litellm_path.read_text(encoding="utf-8").split("\n", 3)[3])
    backend_catalog = json.loads(backend_catalog_path.read_text(encoding="utf-8"))
    mcp_data = json.loads(mcp_path.read_text(encoding="utf-8"))

    assert output["llama_swap"].name == "llama-swap.generated.yaml"
    assert output["backend_runtime_catalog"].name == "backend-runtime.catalog.json"
    assert litellm_data["litellm_settings"]["master_key"] == "os.environ/LITELLM_MASTER_KEY"
    assert vllm_path.exists()
    assert backend_catalog["schema_version"] == 1
    assert any(item["backend"] == "rocm" for item in backend_catalog["variants"])
    assert "litellm-gateway" in mcp_data["servers"]
    assert nginx_path.exists()
    assert nginx_index_path.exists()


def test_write_generated_configs_includes_base_path_namespace_routes(tmp_path: Path) -> None:
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

    write_generated_configs(tmp_path)
    nginx_text = (tmp_path / "config" / "generated" / "nginx" / "nginx.conf").read_text(encoding="utf-8")
    index_text = (tmp_path / "config" / "generated" / "nginx" / "index.html").read_text(encoding="utf-8")

    assert "location = /audia/llmgateway {" in nginx_text
    assert "location /audia/llmgateway/ {" in nginx_text
    assert "proxy_pass http://127.0.0.1:8080;" in nginx_text
    assert "href=\"/audia/llmgateway/v1/models\"" in index_text
    assert "href=\"/audia/llmgateway/llamaswap/\"" in index_text


def test_build_llama_swap_config_contains_generated_catalog_models() -> None:
    root = Path(__file__).resolve().parents[1]
    stack = load_stack_config(root)
    config = build_llama_swap_config(stack)

    assert "InternVL3-5-GPT-OSS-20B@gpu2" not in config["models"]
    assert config["macros"]["cache-q8-args"] == "--cache-type-k q8_0 --cache-type-v q8_0"
    assert config["macros"]["qwen-nothink-args"] == '--reasoning-budget 0 --reasoning-format none --chat-template-kwargs {"enable_thinking":false}'
    generated_qwen = config["models"]["qwen3.5-27b-(96k-Q6)"]["cmd"]
    generated_qwen_vision = config["models"]["qwen3-5-4b-ud-q5-k-xl-vision"]["cmd"]
    assert "${context-96k-args}" in generated_qwen
    assert "--device Vulkan0,Vulkan2" in generated_qwen
    assert "${coder_args}" in generated_qwen
    assert generated_qwen_vision.startswith("${llama-server-vulkan} ")
    assert "--device Vulkan0" in generated_qwen_vision
    assert config["models"]["tiny-qwen25-test"]["cmd"].startswith("${llama-server-rocm} ")
    assert "--device ROCm0" in config["models"]["tiny-qwen25-test"]["cmd"]
    assert "--flash-attn on" in config["macros"]["batch-args"]
    assert "--flash-attn on" in config["macros"]["coder_args"]
    assert "--flash-attn off" in config["macros"]["flash-off-args"]
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


def test_write_generated_configs_includes_nginx_timeouts_and_llamaswap_ui_routes(tmp_path: Path) -> None:
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

    write_generated_configs(tmp_path)
    nginx_text = (tmp_path / "config" / "generated" / "nginx" / "nginx.conf").read_text(encoding="utf-8")

    assert "proxy_connect_timeout 60s;" in nginx_text
    assert "proxy_send_timeout 600s;" in nginx_text
    assert "proxy_read_timeout 600s;" in nginx_text
    assert "location = /llamaswap {" in nginx_text
    assert "return 301 /llamaswap/ui/;" in nginx_text
    assert "location /llamaswap/ui/ {" in nginx_text
    assert "rewrite ^/llamaswap/ui/(.*)$ /ui/$1 break;" in nginx_text
    assert "sub_filter 'href=\"/ui/' 'href=\"/llamaswap/ui/';" in nginx_text


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
                    "deployment_profiles": {
                        "llamacpp_vulkan_single": {
                            "framework": "llama_cpp",
                            "transport": "llama-swap",
                            "executable_macro": "llama-server-vulkan",
                            "llama_cpp_options": {
                                "device": "Vulkan0",
                                "split_mode": "none",
                            },
                        }
                    },
                    "runtime_profiles": {},
                },
                "model_profiles": {
                    "alias_test": {
                        "mode": "chat",
                        "defaults": {
                            "context_preset": "40k",
                        },
                        "artifacts": {
                            "model_file": "AliasTest\\alias-test.gguf",
                        },
                        "deployments": {
                            "llamacpp_vulkan": {
                                "label": "local/alias_test",
                                "profile": "llamacpp_vulkan_single",
                                "llama_swap_model": "alias-test-model",
                            }
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "config" / "local" / "models.override.yaml").write_text(yaml.safe_dump({}), encoding="utf-8")

    stack = load_stack_config(tmp_path)
    config = build_llama_swap_config(stack)

    assert config["macros"]["context-40k-args"] == "--ctx-size 40960"
    assert "--device Vulkan0 --split-mode none" in config["models"]["alias-test-model"]["cmd"]
    assert "${context-40k-args}" in config["models"]["alias-test-model"]["cmd"]


def test_backend_runtime_variants_generate_versioned_macros_and_catalog(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AUDIA_DOCKER", "true")
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

    models_override = tmp_path / "config" / "local" / "models.override.yaml"
    data = yaml.safe_load(models_override.read_text(encoding="utf-8"))
    data.setdefault("backend_runtime_variants", []).append(
        {
            "name": "rocm-b8429",
            "backend": "rocm",
            "macro": "llama-server-rocm-b8429",
            "version": "b8429",
            "runtime_subdir": "rocm/b8429",
        }
    )
    models_override.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    write_generated_configs(tmp_path)
    llama_swap_text = (tmp_path / "config" / "generated" / "llama-swap" / "llama-swap.generated.yaml").read_text(encoding="utf-8")
    backend_catalog = json.loads((tmp_path / "config" / "generated" / "llama-swap" / "backend-runtime.catalog.json").read_text(encoding="utf-8"))

    assert "llama-server-rocm-b8429" in llama_swap_text
    assert "/app/runtime-root/rocm/b8429/bin/llama-server-rocm" in llama_swap_text
    assert any(
        item.get("macro") == "llama-server-rocm-b8429"
        and item.get("backend") == "rocm"
        and item.get("version") == "b8429"
        for item in backend_catalog.get("variants", [])
    )
