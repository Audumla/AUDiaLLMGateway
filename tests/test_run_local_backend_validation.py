from __future__ import annotations

from pathlib import Path

import yaml

import scripts.run_local_backend_validation as runner


def test_seed_native_smoke_workspace_copies_local_yaml_files(tmp_path: Path, monkeypatch) -> None:
    source_root = tmp_path / "repo"
    source_local = source_root / "config" / "local"
    source_local.mkdir(parents=True)
    (source_local / "stack.override.yaml").write_text("routing:\n  notes: [sample]\n", encoding="utf-8")
    (source_local / "models.override.yaml").write_text("model_profiles: {}\n", encoding="utf-8")
    monkeypatch.setattr(runner, "REPO_ROOT", source_root)

    workspace = tmp_path / "workspace"
    runner._seed_native_smoke_workspace(workspace)

    assert (workspace / "config" / "local" / "stack.override.yaml").exists()
    assert (workspace / "config" / "local" / "models.override.yaml").exists()


def test_write_native_stack_overlay_selects_requested_profile(tmp_path: Path) -> None:
    overlay_path = runner._write_native_stack_overlay(
        tmp_path,
        profile_name="windows-vulkan",
        llama_version="b8720",
    )
    data = yaml.safe_load(overlay_path.read_text(encoding="utf-8"))

    assert data["component_settings"]["llama_cpp"]["selected_profile"] == "windows-vulkan"
    assert data["component_settings"]["llama_cpp"]["profiles"]["windows-vulkan"]["version"] == "b8720"
    assert "windows-vulkan" in data["routing"]["notes"][0]


def test_write_native_stack_overlay_can_leave_profile_version_unset(tmp_path: Path) -> None:
    overlay_path = runner._write_native_stack_overlay(
        tmp_path,
        profile_name="windows-vulkan",
        llama_version=None,
    )
    data = yaml.safe_load(overlay_path.read_text(encoding="utf-8"))

    assert data["component_settings"]["llama_cpp"]["selected_profile"] == "windows-vulkan"
    assert data["component_settings"]["llama_cpp"]["profiles"]["windows-vulkan"] == {}


def test_native_command_targets_requested_model(tmp_path: Path) -> None:
    command = runner._native_command(
        native_root=tmp_path / "native-smoke",
        model_label="local/qwen4b_validation_vulkan",
        install=True,
        stage=0,
    )

    assert command[1] == "scripts/smoke_runner.py"
    assert "--install" in command
    assert "0" in command
    assert "local/qwen4b_validation_vulkan" in command


def test_preferred_workspace_python_uses_repo_venv_when_present(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    venv_python = repo_root / ".venv" / "Scripts" / "python.exe"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text("", encoding="utf-8")
    monkeypatch.setattr(runner, "REPO_ROOT", repo_root)

    assert runner._preferred_workspace_python() == str(venv_python)


def test_native_validate_command_omits_install_flag(tmp_path: Path) -> None:
    command = runner._native_command(
        native_root=tmp_path / "native-smoke",
        model_label="local/qwen4b_validation_vulkan",
        install=False,
        stage=5,
    )

    assert command[1] == "scripts/smoke_runner.py"
    assert "--install" not in command
    assert "5" in command
    assert command[-1] == "local/qwen4b_validation_vulkan"


def test_read_installed_llama_executable_uses_install_state(tmp_path: Path) -> None:
    state_path = tmp_path / "state" / "install-state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(
        '{"component_results": {"llama_cpp": {"executable_path": "H:/tools/llama.cpp/b8724-vulkan/llama-server.exe"}}}',
        encoding="utf-8",
    )

    assert str(runner._read_installed_llama_executable(tmp_path)).endswith("b8724-vulkan\\llama-server.exe")


def test_read_installed_llama_variants_uses_variant_backends(tmp_path: Path) -> None:
    state_path = tmp_path / "state" / "install-state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(
        """
{
  "component_results": {
    "llama_cpp": {
      "executable_path": "H:/tools/llama.cpp/b8763-cpu/bin/llama-server.exe",
      "variants": {
        "windows-cpu": {
          "backend": "cpu",
          "executable_path": "H:/tools/llama.cpp/b8763-cpu/bin/llama-server.exe"
        },
        "windows-vulkan": {
          "backend": "vulkan",
          "executable_path": "H:/tools/llama.cpp/b8763-vulkan/bin/llama-server.exe"
        },
        "windows-hip": {
          "backend": "rocm",
          "executable_path": "H:/tools/llama.cpp/b8763-hip/bin/llama-server.exe"
        }
      }
    }
  }
}
""".strip(),
        encoding="utf-8",
    )

    macros, default_executable = runner._read_installed_llama_variants(tmp_path)

    assert Path(macros["llama-server-cpu"]).as_posix().endswith("b8763-cpu/bin/llama-server.exe")
    assert Path(macros["llama-server-vulkan"]).as_posix().endswith("b8763-vulkan/bin/llama-server.exe")
    assert Path(macros["llama-server-rocm"]).as_posix().endswith("b8763-hip/bin/llama-server.exe")
    assert Path(macros["llama-server-hip"]).as_posix().endswith("b8763-hip/bin/llama-server.exe")
    assert Path(default_executable).as_posix().endswith("b8763-cpu/bin/llama-server.exe")


def test_write_native_llama_swap_overlay_uses_workspace_paths(tmp_path: Path) -> None:
    state_path = tmp_path / "state" / "install-state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(
        """
{
  "component_results": {
    "llama_cpp": {
      "executable_path": "H:/tools/llama.cpp/b8763-vulkan/bin/llama-server.exe",
      "variants": {
        "windows-vulkan": {
          "backend": "vulkan",
          "executable_path": "H:/tools/llama.cpp/b8763-vulkan/bin/llama-server.exe"
        },
        "windows-hip": {
          "backend": "rocm",
          "executable_path": "H:/tools/llama.cpp/b8763-hip/bin/llama-server.exe"
        }
      }
    }
  }
}
""".strip(),
        encoding="utf-8",
    )
    overlay_path = runner._write_native_llama_swap_overlay(
        tmp_path,
        executable=Path("H:/tools/llama.cpp/b8724-vulkan/llama-server.exe"),
    )
    data = yaml.safe_load(overlay_path.read_text(encoding="utf-8"))

    assert Path(data["macros"]["llama-server"]).as_posix().endswith("b8763-vulkan/bin/llama-server.exe")
    assert Path(data["macros"]["llama-server-vulkan"]).as_posix().endswith("b8763-vulkan/bin/llama-server.exe")
    assert Path(data["macros"]["llama-server-rocm"]).as_posix().endswith("b8763-hip/bin/llama-server.exe")
    assert "llama-server-cpu" not in data["macros"]
    assert data["macros"]["model-path"].endswith("\\models")
    assert data["macros"]["mmproj-path"].endswith("\\models")


def test_docker_run_command_includes_quick_validation_profile() -> None:
    detection = type(
        "Detection",
        (),
        {
            "host_acceleration": "vulkan",
            "container_acceleration": "cpu",
            "gpu_name": "AMD Radeon RX 7900 GRE",
        },
    )()

    command = runner._docker_run_command(
        image="audia-integration",
        model_cache=Path("H:/cache"),
        detection=detection,
        validation_profile="quick",
        docker_profile={
            "model_name": "Qwen3.5-2B-Q4_K_M.gguf",
            "model_url": "https://example.invalid/Qwen3.5-2B-Q4_K_M.gguf",
            "min_size_bytes": 1000000000,
        },
        benchmark_output=Path("H:/results/quick__docker-cpu.json"),
        benchmark_prompt="Reply with one short sentence confirming this request was handled.",
        benchmark_max_tokens=48,
    )

    joined = " ".join(command)
    assert "AUDIA_VALIDATION_PROFILE=quick" in joined
    assert "AUDIA_VALIDATION_MODEL_NAME=Qwen3.5-2B-Q4_K_M.gguf" in joined
    assert "AUDIA_BENCHMARK_OUTPUT=/benchmark/quick__docker-cpu.json" in joined


def test_native_benchmark_context_includes_installation_metadata() -> None:
    context = runner._native_benchmark_context(
        detection=type(
            "Detection",
            (),
            {
                "host_acceleration": "vulkan",
                "container_acceleration": "cpu",
                "gpu_name": "AMD Radeon RX 7900 GRE",
                "reason": "detected",
                "supported_accelerations": ["cpu", "vulkan"],
            },
        )(),
        native_profile="windows-vulkan",
        native_model="local/qwen2b_validation_vulkan",
        llama_version="b8763",
        benchmark_settings_profile="batch",
        install_state={
            "component_results": {
                "llama_cpp": {
                    "profile": "windows-vulkan",
                    "version": "b8763",
                    "backend": "vulkan",
                    "cache_hit": True,
                    "install_dir": "H:/tools/llama.cpp/b8763-vulkan",
                    "executable_path": "H:/tools/llama.cpp/b8763-vulkan/bin/llama-server.exe",
                }
            }
        },
    )

    assert context["installation"]["llama_cpp_cache_hit"] is True
    assert context["installation"]["llama_cpp_profile"] == "windows-vulkan"
    assert context["target"]["benchmark_settings_profile"] == "batch"


def test_benchmark_host_context_uses_gpu_label_when_available() -> None:
    context = runner._benchmark_host_context(
        type(
            "Detection",
            (),
            {
                "gpu_name": "AMD Radeon RX 7900 GRE",
                "host_acceleration": "rocm",
                "container_acceleration": "cpu",
                "reason": "detected",
                "supported_accelerations": ["cpu", "rocm"],
            },
        )()
    )

    assert context["host_label"] == "AMD Radeon RX 7900 GRE"
