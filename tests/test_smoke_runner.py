from __future__ import annotations

from pathlib import Path

import yaml

import scripts.smoke_runner as smoke_runner
from src.launcher.config_loader import PublishedModel


def _published_model(label: str, llama_swap_model: str) -> PublishedModel:
    return PublishedModel(
        label=label,
        framework="llama_cpp",
        transport="llama-swap",
        api_base="http://127.0.0.1:41080/v1",
        llama_swap_model=llama_swap_model,
        backend_model_name=llama_swap_model,
        purpose="test",
        revision="main",
        model_filename="model.gguf",
        model_url="https://example.invalid/model.gguf",
        additional_model_urls=[],
        mmproj_filename="",
        mmproj_url="",
        source_page_url="https://example.invalid",
        source_type="download",
        source_path="",
        load_groups=[],
        api_key_placeholder="not-required",
        mode="chat",
    )


def test_resolve_direct_llama_server_command_uses_generated_model_command(tmp_path: Path) -> None:
    generated_path = tmp_path / "config" / "generated" / "llama-swap" / "llama-swap.generated.yaml"
    generated_path.parent.mkdir(parents=True, exist_ok=True)
    generated_path.write_text(
        yaml.safe_dump(
            {
                "macros": {
                    "llama-server-vulkan": "H:/tools/llama-server.exe",
                    "server-args": "--port ${PORT} --host 127.0.0.1",
                    "model-path": "--model H:/models",
                    "context-32k-args": "--ctx-size 32768",
                },
                "models": {
                    "qwen-validation": {
                        "cmd": "${llama-server-vulkan} ${server-args} "
                        "${model-path}/Qwen3.5-2B/Qwen3.5-2B-Q4_K_M.gguf "
                        "${context-32k-args} --device Vulkan0 --gpu-layers all"
                    }
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    stack = type(
        "Stack",
        (),
        {
            "llama_swap": type("Runtime", (), {"generated_config_path": "config/generated/llama-swap/llama-swap.generated.yaml"})(),
            "published_models": [_published_model("local/qwen2b_validation_vulkan", "qwen-validation")],
        },
    )()

    command = smoke_runner._resolve_direct_llama_server_command(
        tmp_path,
        stack,
        "local/qwen2b_validation_vulkan",
        port=41990,
    )

    assert command is not None
    joined = " ".join(command)
    assert "llama-server.exe" in joined
    assert "--port 41990" in joined
    assert "--device Vulkan0" in joined
    assert "--gpu-layers all" in joined


def test_benchmark_direct_llama_server_returns_benchmark_row(tmp_path: Path, monkeypatch) -> None:
    generated_path = tmp_path / "config" / "generated" / "llama-swap" / "llama-swap.generated.yaml"
    generated_path.parent.mkdir(parents=True, exist_ok=True)
    generated_path.write_text(
        yaml.safe_dump(
            {
                "macros": {
                    "llama-server-vulkan": "H:/tools/llama-server.exe",
                    "server-args": "--port ${PORT} --host 127.0.0.1",
                    "model-path": "--model H:/models",
                },
                "models": {
                    "qwen-validation": {
                        "cmd": "${llama-server-vulkan} ${server-args} "
                        "${model-path}/Qwen3.5-2B/Qwen3.5-2B-Q4_K_M.gguf --device Vulkan0 --gpu-layers all"
                    }
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    stack = type(
        "Stack",
        (),
        {
            "llama_swap": type("Runtime", (), {"generated_config_path": "config/generated/llama-swap/llama-swap.generated.yaml"})(),
            "published_models": [_published_model("local/qwen2b_validation_vulkan", "qwen-validation")],
        },
    )()

    launched: list[list[str]] = []
    stopped: list[str] = []

    monkeypatch.setattr(smoke_runner, "_wait_for_any", lambda urls, timeout=0.0, interval=0.0, headers=None: (True, urls[0]))

    def fake_chat_completion_request(**kwargs):
        if kwargs["prompt"].startswith("Warm up"):
            return {
                "body": {},
                "elapsed_seconds": 0.1,
                "completion_tokens": 3,
                "tok_per_sec": 30.0,
                "backend_tok_per_sec": 60.0,
                "finish_reason": "stop",
                "content": "warm",
            }
        return {
            "body": {},
            "elapsed_seconds": 0.5,
            "completion_tokens": 20,
            "tok_per_sec": 40.0,
            "backend_tok_per_sec": 80.0,
            "finish_reason": "stop",
            "content": "handled",
        }

    monkeypatch.setattr(smoke_runner, "_chat_completion_request", fake_chat_completion_request)

    monkeypatch.setattr(
        "src.launcher.process_manager.launch_detached",
        lambda root, service_name, command, env=None: launched.append(command) or 12345,
    )
    monkeypatch.setattr(
        "src.launcher.process_manager.stop_service",
        lambda root, service_name: stopped.append(service_name) or True,
    )

    row = smoke_runner._benchmark_direct_llama_server(
        tmp_path,
        stack,
        model_label="local/qwen2b_validation_vulkan",
        prompt="Reply with one short sentence confirming this request was handled.",
        max_tokens=48,
    )

    assert row is not None
    assert row["route"] == "direct-llama-server"
    assert row["benchmark_mode"] == "preload+timed"
    assert row["preload"] is not None
    assert row["summary"]["client_avg_tok_per_sec"] == 40.0
    assert row["summary"]["backend_avg_tok_per_sec"] == 80.0
    assert row["results"][0]["completion_tokens"] == 20
    assert row["results"][0]["model"] == "local/qwen2b_validation_vulkan"
    assert stopped[:3] == ["gateway", "llama-swap", "direct-llama-server"]
    assert launched


def test_run_stage5_routing_warms_gateway_before_benchmark(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_chat_completion_request(**kwargs):
        calls.append(kwargs)
        return {
            "body": {},
            "elapsed_seconds": 0.5,
            "completion_tokens": 20,
            "tok_per_sec": 40.0,
            "finish_reason": "stop",
            "content": "handled",
        }

    monkeypatch.setattr(smoke_runner, "_chat_completion_request", fake_chat_completion_request)
    monkeypatch.setattr(smoke_runner, "_benchmark_direct_llama_server", lambda *args, **kwargs: None)

    generated_path = Path("H:/workspace") / "config" / "generated" / "llama-swap" / "llama-swap.generated.yaml"
    generated_path.parent.mkdir(parents=True, exist_ok=True)
    generated_path.write_text(
        yaml.safe_dump(
            {
                "macros": {
                    "llama-server-vulkan": "H:/tools/llama-server.exe",
                    "server-args": "--port ${PORT} --host 127.0.0.1",
                    "model-path": "--model H:/models",
                },
                "models": {
                    "qwen-validation": {
                        "cmd": "${llama-server-vulkan} ${server-args} "
                        "${model-path}/Qwen3.5-2B/Qwen3.5-2B-Q4_K_M.gguf --device Vulkan0,Vulkan2 --gpu-layers all"
                    }
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    stack = type(
        "Stack",
        (),
        {
            "nginx": type("Nginx", (), {"enabled": False, "host": "127.0.0.1", "port": 8080})(),
            "litellm": type("LiteLLM", (), {"host": "127.0.0.1", "port": 4000, "master_key_env": "LITELLM_MASTER_KEY"})(),
            "llama_swap": type(
                "Swap",
                (),
                {"host": "127.0.0.1", "port": 41080, "generated_config_path": "config/generated/llama-swap/llama-swap.generated.yaml"},
            )(),
            "published_models": [_published_model("local/qwen2b_validation_vulkan", "qwen-validation")],
        },
    )()

    ok = smoke_runner.run_stage5_routing(
        Path("H:/workspace"),
        stack,
        ["local/qwen2b_validation_vulkan"],
        prompt="Reply with one short sentence confirming this request was handled.",
        max_tokens=48,
        benchmark_output=Path("H:/workspace/result.json"),
        benchmark_context={"host": {"platform": "Windows"}, "target": {"kind": "native-smoke"}},
    )

    assert ok is True
    assert len(calls) == 4
    assert calls[0]["prompt"] == "Warm up and reply with one word."
    assert calls[1]["prompt"] == "Reply with one short sentence confirming this request was handled."
    assert calls[2]["base_url"] == "http://127.0.0.1:41080"
    assert calls[2]["model_name"] == "qwen-validation"
    assert calls[3]["base_url"] == "http://127.0.0.1:41080"
    assert calls[3]["model_name"] == "qwen-validation"

    written = yaml.safe_load(Path("H:/workspace/result.json").read_text(encoding="utf-8"))
    assert written["benchmark_context"]["target"]["kind"] == "native-smoke"
    assert written["benchmark_context"]["targets"][0]["backend_device_selection"]["family"] == "vulkan"
    assert written["results"][0]["benchmark_mode"] == "timed"
    assert written["results"][0]["sample_count"] == 1


def test_stage5_model_names_defaults_to_qwen2b_validation() -> None:
    assert smoke_runner._stage5_model_names([], "rocm") == ["local/qwen2b_validation_rocm"]
    assert smoke_runner._stage5_model_names([], "vulkan") == ["local/qwen2b_validation_vulkan"]
    assert smoke_runner._stage5_model_names(["local/custom"], "rocm") == ["local/custom"]


def test_published_model_details_captures_backend_device_selection(tmp_path: Path) -> None:
    generated_path = tmp_path / "config" / "generated" / "llama-swap" / "llama-swap.generated.yaml"
    generated_path.parent.mkdir(parents=True, exist_ok=True)
    generated_path.write_text(
        yaml.safe_dump(
            {
                "macros": {
                    "llama-server-vulkan": "H:/tools/llama-server.exe",
                    "server-args": "--port ${PORT} --host 127.0.0.1",
                    "model-path": "--model H:/models",
                },
                "models": {
                    "qwen-validation": {
                        "cmd": "${llama-server-vulkan} ${server-args} "
                        "${model-path}/Qwen3.5-2B/Qwen3.5-2B-Q4_K_M.gguf --device Vulkan0,Vulkan2 --gpu-layers all"
                    }
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    stack = type(
        "Stack",
        (),
        {
            "llama_swap": type("Runtime", (), {"generated_config_path": "config/generated/llama-swap/llama-swap.generated.yaml"})(),
            "published_models": [_published_model("local/qwen2b_validation_vulkan", "qwen-validation")],
        },
    )()

    details = smoke_runner._published_model_details(tmp_path, stack, "local/qwen2b_validation_vulkan")

    assert details["backend_device_selection"]["family"] == "vulkan"
    assert details["backend_device_selection"]["devices"] == ["Vulkan0", "Vulkan2"]
