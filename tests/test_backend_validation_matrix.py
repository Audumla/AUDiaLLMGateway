from __future__ import annotations

import json
from pathlib import Path

import scripts.run_backend_validation_matrix as matrix
from src.launcher.local_backend_validation import ValidationTarget


def test_selected_profiles_prefers_default_when_not_overridden() -> None:
    catalog = {
        "defaults": {"validation_profile": "quick"},
        "profiles": {"quick": {}, "full": {}},
    }

    assert matrix._selected_profiles(catalog, [], all_profiles=False) == ["quick"]


def test_selected_profiles_returns_every_profile_when_requested() -> None:
    catalog = {
        "defaults": {"validation_profile": "quick"},
        "profiles": {"quick": {}, "full": {}},
    }

    assert matrix._selected_profiles(catalog, [], all_profiles=True) == ["quick", "full"]


def test_build_target_command_sets_container_acceleration_for_docker_target(tmp_path: Path) -> None:
    target = ValidationTarget(
        name="docker-cpu",
        transport="docker",
        backend="cpu",
        experimental=False,
        native_profile=None,
        native_model_label=None,
    )

    command, env = matrix._build_target_command(
        target=target,
        profile_name="quick",
        benchmark_settings_profile="default",
        benchmark_output=tmp_path / "quick__docker-cpu.json",
        image="audia-integration",
        llama_version="b8720",
        model_cache=tmp_path / "models",
        native_root_base=tmp_path / "native",
    )

    assert command[1] == "scripts/run_local_backend_validation.py"
    assert "--mode" in command
    assert "docker" in command
    assert env["AUDIA_LOCAL_VALIDATION_CONTAINER_ACCEL"] == "cpu"


def test_build_target_command_passes_external_docker_image_overrides(tmp_path: Path) -> None:
    target = ValidationTarget(
        name="docker-rocm-amd-full",
        transport="docker",
        backend="rocm",
        experimental=True,
        native_profile=None,
        native_model_label=None,
        docker_image="rocm/llama.cpp:llama.cpp-b6652.amd0_rocm7.0.0_ubuntu24.04_full",
        docker_run_mode="external-llama-server",
    )

    command, env = matrix._build_target_command(
        target=target,
        profile_name="quick",
        benchmark_settings_profile="default",
        benchmark_output=tmp_path / "quick__docker-rocm-amd-full.json",
        image="audia-integration",
        llama_version="b8720",
        model_cache=tmp_path / "models",
        native_root_base=tmp_path / "native",
    )

    assert "--docker-image-override" in command
    assert "rocm/llama.cpp:llama.cpp-b6652.amd0_rocm7.0.0_ubuntu24.04_full" in command
    assert env["AUDIA_LOCAL_VALIDATION_CONTAINER_ACCEL"] == "rocm"


def test_build_target_command_sets_native_profile_and_model(tmp_path: Path, monkeypatch) -> None:
    target = ValidationTarget(
        name="native-vulkan-turboquant",
        transport="native",
        backend="vulkan",
        experimental=True,
        native_profile="windows-vulkan-turboquant",
        native_model_label="local/qwen2b_validation_vulkan",
    )

    source_sdk = tmp_path / "source-sdk"
    (source_sdk / "Include" / "vulkan").mkdir(parents=True)
    (source_sdk / "Lib").mkdir(parents=True)
    (source_sdk / "Bin").mkdir(parents=True)
    (source_sdk / "Include" / "vulkan" / "vulkan.h").write_text("header", encoding="utf-8")
    (source_sdk / "Lib" / "vulkan-1.lib").write_text("lib", encoding="utf-8")
    (source_sdk / "Bin" / "glslc.exe").write_text("exe", encoding="utf-8")
    monkeypatch.setenv("AUDIA_VULKAN_SDK_SOURCE", str(source_sdk))

    command, env = matrix._build_target_command(
        target=target,
        profile_name="quick",
        benchmark_settings_profile="default",
        benchmark_output=tmp_path / "quick__native-vulkan-turboquant.json",
        image="audia-integration",
        llama_version="b8720",
        model_cache=tmp_path / "models",
        native_root_base=tmp_path / "native",
    )

    assert "--native-llama-cpp-profile" in command
    assert "windows-vulkan-turboquant" in command
    assert "--native-model" in command
    assert "local/qwen2b_validation_vulkan" in command
    assert "AUDIA_LOCAL_VALIDATION_CONTAINER_ACCEL" not in env


def test_build_target_command_passes_local_vulkan_sdk_root_for_turboquant(tmp_path: Path) -> None:
    target = ValidationTarget(
        name="native-vulkan-turboquant",
        transport="native",
        backend="vulkan",
        experimental=True,
        native_profile="windows-vulkan-turboquant",
        native_model_label="local/qwen2b_validation_vulkan",
    )

    repo_sdk = tmp_path / "repo" / "test-work" / "toolchains" / "vulkan-sdk" / "windows"
    repo_sdk.mkdir(parents=True)
    original_root = matrix.REPO_ROOT
    matrix.REPO_ROOT = tmp_path / "repo"
    try:
        command, env = matrix._build_target_command(
            target=target,
            profile_name="quick",
            benchmark_settings_profile="default",
            benchmark_output=tmp_path / "quick__native-vulkan-turboquant.json",
            image="audia-integration",
            llama_version="b8720",
            model_cache=tmp_path / "models",
            native_root_base=tmp_path / "native",
        )
    finally:
        matrix.REPO_ROOT = original_root

    assert command[1] == "scripts/run_local_backend_validation.py"
    assert env["AUDIA_VULKAN_SDK_ROOT"].endswith("quick\\native-vulkan-turboquant\\toolchains\\vulkan-sdk\\windows")
    assert env["AUDIA_VULKAN_SDK_SOURCE"].endswith("test-work\\toolchains\\vulkan-sdk\\windows")


def test_build_target_command_passes_local_vulkan_sdk_root_for_any_vulkan_native_target(tmp_path: Path) -> None:
    target = ValidationTarget(
        name="native-vulkan-upstream-head",
        transport="native",
        backend="vulkan",
        experimental=True,
        native_profile="windows-vulkan-upstream-head",
        native_model_label="local/qwen2b_validation_vulkan",
    )

    repo_sdk = tmp_path / "repo" / "test-work" / "toolchains" / "vulkan-sdk" / "windows"
    repo_sdk.mkdir(parents=True)
    original_root = matrix.REPO_ROOT
    matrix.REPO_ROOT = tmp_path / "repo"
    try:
        command, env = matrix._build_target_command(
            target=target,
            profile_name="quick",
            benchmark_settings_profile="default",
            benchmark_output=tmp_path / "quick__native-vulkan-upstream-head.json",
            image="audia-integration",
            llama_version="",
            model_cache=tmp_path / "models",
            native_root_base=tmp_path / "native",
        )
    finally:
        matrix.REPO_ROOT = original_root

    assert command[1] == "scripts/run_local_backend_validation.py"
    assert env["AUDIA_VULKAN_SDK_ROOT"].endswith("quick\\native-vulkan-upstream-head\\toolchains\\vulkan-sdk\\windows")
    assert env["AUDIA_VULKAN_SDK_SOURCE"].endswith("test-work\\toolchains\\vulkan-sdk\\windows")


def test_summarize_benchmark_reports_top_tok_per_sec(tmp_path: Path) -> None:
    benchmark_path = tmp_path / "quick__native-vulkan.json"
    benchmark_path.write_text(
        json.dumps(
            {
                "benchmark_context": {"host": {"platform": "Windows"}, "target": {"kind": "native-smoke"}},
                "results": [
                    {"route": "gateway", "tok_per_sec": 12.5, "backend_tok_per_sec": 20.0},
                    {"route": "direct-llama-server", "tok_per_sec": 18.0, "backend_tok_per_sec": 25.0},
                ]
            }
        ),
        encoding="utf-8",
    )

    summary = matrix._summarize_benchmark(benchmark_path)

    assert summary["success_count"] == 2
    assert summary["sample_count"] == 2
    assert summary["top_tok_per_sec"] == 15.25
    assert summary["backend_top_tok_per_sec"] == 22.5
    assert summary["benchmark_context"]["target"]["kind"] == "native-smoke"


def test_failure_result_classifies_missing_sdk(tmp_path: Path) -> None:
    target = ValidationTarget(
        name="native-hip-official",
        transport="native",
        backend="rocm",
        experimental=False,
        native_profile="windows-hip-official",
        native_model_label="local/qwen2b_validation_rocm",
    )

    result = matrix._failure_result(
        profile_name="quick",
        target=target,
        benchmark_output=tmp_path / "quick__native-hip-official.json",
        error=RuntimeError("Local ROCm SDK not available. Set ROCM_PATH."),
        benchmark_settings_profile="default",
    )

    assert result["status"] == "skipped"
    assert result["failure_kind"] == "missing_toolchain"
    assert "bootstrap" in result["failure_hint"].lower()


def test_target_with_fallbacks_runs_source_retry_after_prebuilt_failure(tmp_path: Path, monkeypatch) -> None:
    primary = ValidationTarget(
        name="native-hip-lemonade-release",
        transport="native",
        backend="rocm",
        experimental=True,
        native_profile="windows-hip-lemonade-release",
        native_model_label="local/qwen2b_validation_rocm",
        fallback_targets=("native-hip-lemonade-head",),
    )
    fallback = ValidationTarget(
        name="native-hip-lemonade-head",
        transport="native",
        backend="rocm",
        experimental=True,
        native_profile="windows-hip-lemonade-head",
        native_model_label="local/qwen2b_validation_rocm",
    )
    calls: list[str] = []

    def fake_run_single_target(**kwargs):
        calls.append(kwargs["target"].name)
        if kwargs["target"].name == "native-hip-lemonade-release":
            return {
                "profile": kwargs["profile_name"],
                "target": kwargs["target"].name,
                "transport": kwargs["target"].transport,
                "backend": kwargs["target"].backend,
                "experimental": kwargs["target"].experimental,
                "benchmark_settings_profile": kwargs["benchmark_settings_profile"],
                "returncode": 1,
                "status": "failed",
                "benchmark_output": str(kwargs["benchmark_output"]),
            }
        return {
            "profile": kwargs["profile_name"],
            "target": kwargs["target"].name,
            "transport": kwargs["target"].transport,
            "backend": kwargs["target"].backend,
            "experimental": kwargs["target"].experimental,
            "benchmark_settings_profile": kwargs["benchmark_settings_profile"],
            "returncode": 0,
            "status": "passed",
            "benchmark_output": str(kwargs["benchmark_output"]),
            "fallback_of": kwargs.get("fallback_of"),
            "benchmark": {
                "top_tok_per_sec": 77.7,
                "benchmark_context": {"installation": {"llama_cpp_cache_hit": True}},
            },
        }

    monkeypatch.setattr(matrix, "_run_single_target", fake_run_single_target)

    rows, failures = matrix._run_target_with_fallbacks(
        target=primary,
        profile_name="quick",
        benchmark_settings_profile="default",
        image="audia-integration",
        llama_version="b8763",
        model_cache=tmp_path / "models",
        native_root_base=tmp_path / "native",
        target_lookup={primary.name: primary, fallback.name: fallback},
        completed_targets=set(),
        results_dir=tmp_path,
    )

    assert calls == ["native-hip-lemonade-release", "native-hip-lemonade-head"]
    assert failures == 0
    assert rows[0]["status"] == "failed"
    assert rows[1]["status"] == "passed"
    assert rows[1]["fallback_of"] == "native-hip-lemonade-release"
