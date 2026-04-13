from __future__ import annotations

from pathlib import Path

from src.launcher.local_backend_validation import (
    choose_container_acceleration,
    detect_host_acceleration,
    llama_variant_for_acceleration,
    native_llama_cpp_profile_for_acceleration,
    native_smoke_model_for_acceleration,
    parse_vulkan_gpu_name,
    resolve_validation_targets,
    summarize_device_selection,
)


class _Result:
    def __init__(self, returncode: int, stdout: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_parse_vulkan_gpu_name_handles_current_summary_format() -> None:
    summary = """
    Devices:
        GPU0 :
            apiVersion         = 1.4.313
            deviceName         = AMD Radeon RX 7900 GRE
    """

    assert parse_vulkan_gpu_name(summary) == "AMD Radeon RX 7900 GRE"


def test_parse_vulkan_gpu_name_handles_inline_gpu_format() -> None:
    summary = "GPU0 = AMD Radeon RX 7900 GRE"

    assert parse_vulkan_gpu_name(summary) == "AMD Radeon RX 7900 GRE"


def test_choose_container_acceleration_prefers_cpu_on_windows_vulkan_host() -> None:
    assert (
        choose_container_acceleration(
            "vulkan",
            host_platform="Windows",
            host_has_dri=False,
        )
        == "cpu"
    )


def test_choose_container_acceleration_uses_vulkan_on_linux_with_dri() -> None:
    assert (
        choose_container_acceleration(
            "vulkan",
            host_platform="Linux",
            host_has_dri=True,
        )
        == "vulkan"
    )


def test_llama_variant_for_acceleration_falls_back_to_cpu() -> None:
    assert llama_variant_for_acceleration("cpu") == "cpu"
    assert llama_variant_for_acceleration("cuda") == "cpu"
    assert llama_variant_for_acceleration("rocm") == "cpu"
    assert llama_variant_for_acceleration("vulkan") == "vulkan"


def test_native_llama_cpp_profile_prefers_vulkan_on_windows() -> None:
    assert native_llama_cpp_profile_for_acceleration("vulkan", host_platform="Windows") == "windows-vulkan"
    assert native_llama_cpp_profile_for_acceleration("cpu", host_platform="Windows") == "windows-cpu"
    assert native_llama_cpp_profile_for_acceleration("cuda", host_platform="Windows") == "windows-cpu"


def test_native_smoke_model_uses_vulkan_specific_label_only_for_vulkan_hosts() -> None:
    assert native_smoke_model_for_acceleration("vulkan") == "local/qwen2b_validation_vulkan"
    assert native_smoke_model_for_acceleration("cpu") == "local/qwen2b_validation_cpu"
    assert native_smoke_model_for_acceleration("rocm") == "local/qwen2b_validation_rocm"
    assert (
        native_smoke_model_for_acceleration("vulkan", validation_profile="full")
        == "local/qwen4b_validation_vulkan"
    )
    assert (
        native_smoke_model_for_acceleration("rocm", validation_profile="full")
        == "local/qwen4b_validation_rocm"
    )


def test_detect_host_acceleration_uses_vulkan_when_available(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.launcher.local_backend_validation.platform.system",
        lambda: "Windows",
    )
    monkeypatch.setattr(
        "src.launcher.local_backend_validation.shutil.which",
        lambda name: "vulkaninfo" if name == "vulkaninfo" else None,
    )
    monkeypatch.setattr(
        "src.launcher.local_backend_validation.Path.exists",
        lambda self: False,
    )
    monkeypatch.setattr("src.launcher.local_backend_validation._detect_local_gfx_version", lambda: "")

    detection = detect_host_acceleration(
        runner=lambda command: _Result(
            0,
            "GPU0 = AMD Radeon RX 7900 GRE\n",
        )
    )

    assert detection.host_acceleration == "vulkan"
    assert detection.container_acceleration == "cpu"
    assert detection.supported_accelerations == ("cpu", "vulkan")
    assert detection.gpu_name == "AMD Radeon RX 7900 GRE"


def test_resolve_validation_targets_filters_to_supported_windows_vulkan_matrix() -> None:
    targets = resolve_validation_targets(
        REPO_ROOT,
        host_acceleration="vulkan",
        platform_name="windows",
        validation_profile="quick",
    )

    names = {target.name for target in targets}
    assert {"docker-cpu", "native-cpu", "native-vulkan"}.issubset(names)
    assert "native-hip" not in names


def test_resolve_validation_targets_includes_experimental_turboquant_when_requested() -> None:
    targets = resolve_validation_targets(
        REPO_ROOT,
        host_acceleration="vulkan",
        platform_name="windows",
        validation_profile="quick",
        include_experimental=True,
    )

    names = {target.name for target in targets}
    assert {"docker-cpu", "native-cpu", "native-vulkan", "native-vulkan-turboquant"}.issubset(names)


def test_resolve_validation_targets_enables_linux_vulkan_container_target() -> None:
    targets = resolve_validation_targets(
        REPO_ROOT,
        host_acceleration="vulkan",
        platform_name="linux",
        validation_profile="quick",
    )

    names = {target.name for target in targets}
    assert {"docker-cpu", "docker-vulkan", "native-cpu", "native-vulkan"}.issubset(names)


def test_resolve_validation_targets_allows_vulkan_lanes_on_rocm_hosts() -> None:
    targets = resolve_validation_targets(
        REPO_ROOT,
        host_acceleration="rocm",
        host_capabilities={"cpu", "rocm", "vulkan"},
        platform_name="windows",
        validation_profile="quick",
        include_experimental=True,
    )

    names = {target.name for target in targets}
    assert "native-hip" in names
    assert "native-vulkan" in names


def test_summarize_device_selection_parses_multi_gpu_commands() -> None:
    summary = summarize_device_selection(["llama-server", "--device", "Vulkan0,Vulkan2", "--gpu-layers", "all"])

    assert summary is not None
    assert summary["family"] == "vulkan"
    assert summary["devices"] == ["Vulkan0", "Vulkan2"]
    assert summary["device_count"] == 2
