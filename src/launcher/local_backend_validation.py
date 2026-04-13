from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config_loader import _detect_local_gfx_version, load_layered_yaml

SUPPORTED_ACCELERATIONS = {"cpu", "cuda", "rocm", "vulkan"}
SUPPORTED_CONTAINER_ACCELERATIONS = {"cpu", "vulkan"}
SUPPORTED_VALIDATION_PROFILES = {"quick", "full"}
DEFAULT_VALIDATION_PROFILE = "quick"
DEFAULT_VALIDATION_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class HostAcceleration:
    host_acceleration: str
    container_acceleration: str
    supported_accelerations: tuple[str, ...]
    gpu_name: str | None
    reason: str


@dataclass(frozen=True)
class ValidationTarget:
    name: str
    transport: str
    backend: str
    experimental: bool
    native_profile: str | None
    native_model_label: str | None
    llama_version: str | None = None
    docker_image: str | None = None
    docker_run_mode: str | None = None
    fallback_targets: tuple[str, ...] = ()
    metadata: dict[str, Any] | None = None


def _normalize_acceleration(value: str | None) -> str | None:
    if not value:
        return None
    lowered = value.strip().lower()
    if lowered in SUPPORTED_ACCELERATIONS:
        return lowered
    raise ValueError(f"Unsupported acceleration '{value}'")


def _normalize_validation_profile(value: str | None) -> str:
    if not value:
        return DEFAULT_VALIDATION_PROFILE
    lowered = value.strip().lower()
    if lowered in SUPPORTED_VALIDATION_PROFILES:
        return lowered
    raise ValueError(f"Unsupported validation profile '{value}'")


def supported_accelerations_for_host(host_acceleration: str) -> tuple[str, ...]:
    normalized = _normalize_acceleration(host_acceleration) or "cpu"
    if normalized == "rocm":
        return ("cpu", "rocm", "vulkan")
    if normalized == "cuda":
        return ("cpu", "cuda")
    if normalized == "vulkan":
        return ("cpu", "vulkan")
    return ("cpu",)


def _normalize_platform_name(value: str | None = None) -> str:
    system = (value or platform.system()).strip().lower()
    if system == "darwin":
        return "macos"
    if system in {"windows", "linux", "macos"}:
        return system
    raise ValueError(f"Unsupported platform '{value or system}'")


def load_validation_catalog(root: str | Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    return load_layered_yaml(
        root,
        "config/project/backend-validation.base.yaml",
        "config/local/backend-validation.override.yaml",
    )


def validation_profiles(root: str | Path) -> dict[str, Any]:
    _, _, merged = load_validation_catalog(root)
    profiles = merged.get("profiles", {})
    if not isinstance(profiles, dict):
        raise ValueError("Validation profiles must be a mapping")
    return profiles


def validation_profile_settings(root: str | Path, profile_name: str) -> dict[str, Any]:
    profile = validation_profiles(root).get(profile_name)
    if not isinstance(profile, dict):
        raise ValueError(f"Validation profile '{profile_name}' is not defined")
    return profile


def validation_profile_native_models(root: str | Path, profile_name: str) -> dict[str, str]:
    profile = validation_profile_settings(root, profile_name)
    native_models = profile.get("native_models", {})
    if not isinstance(native_models, dict):
        return {}
    return {
        str(key).strip().lower(): str(value).strip()
        for key, value in native_models.items()
        if str(key).strip() and str(value).strip()
    }


def validation_defaults(root: str | Path) -> dict[str, Any]:
    _, _, merged = load_validation_catalog(root)
    defaults = merged.get("defaults", {})
    if not isinstance(defaults, dict):
        raise ValueError("Validation defaults must be a mapping")
    return defaults


def resolve_validation_targets(
    root: str | Path,
    *,
    host_acceleration: str,
    platform_name: str | None = None,
    validation_profile: str = DEFAULT_VALIDATION_PROFILE,
    include_experimental: bool = False,
    requested_targets: set[str] | None = None,
    host_capabilities: set[str] | None = None,
) -> list[ValidationTarget]:
    normalized_platform = _normalize_platform_name(platform_name)
    normalized_profile = _normalize_validation_profile(validation_profile)
    normalized_host = _normalize_acceleration(host_acceleration) or "cpu"
    normalized_capabilities = {
        _normalize_acceleration(item) or "cpu"
        for item in (host_capabilities or set(supported_accelerations_for_host(normalized_host)))
    }
    _, _, merged = load_validation_catalog(root)
    targets = merged.get("targets", {})
    if not isinstance(targets, dict):
        raise ValueError("Validation targets must be a mapping")

    native_models = validation_profile_native_models(root, normalized_profile)

    resolved: list[ValidationTarget] = []
    for target_name, raw in targets.items():
        if requested_targets and target_name not in requested_targets:
            continue
        if not isinstance(raw, dict):
            continue
        if not bool(raw.get("enabled", True)):
            continue
        experimental = bool(raw.get("experimental", False))
        if experimental and not include_experimental:
            continue
        platforms = {str(item).strip().lower() for item in raw.get("platforms", [])}
        if platforms and normalized_platform not in platforms:
            continue
        host_accels = {str(item).strip().lower() for item in raw.get("host_accelerations", [])}
        if host_accels and normalized_capabilities.isdisjoint(host_accels):
            continue
        transport = str(raw.get("transport", "")).strip().lower()
        backend = str(raw.get("backend", "")).strip().lower()
        native_profile = None
        native_model = None
        if transport == "native":
            profile_map = raw.get("llama_cpp_profiles", {})
            if not isinstance(profile_map, dict):
                continue
            native_profile = str(profile_map.get(normalized_platform, "")).strip() or None
            if not native_profile:
                continue
            native_model = str(native_models.get(backend, native_models.get("cpu", ""))).strip() or None
            if not native_model:
                continue
        resolved.append(
            ValidationTarget(
                name=str(target_name),
                transport=transport,
                backend=backend,
                experimental=experimental,
                native_profile=native_profile,
                native_model_label=native_model,
                llama_version=str(raw.get("llama_version", "")).strip() or None,
                docker_image=str(raw.get("docker_image", "")).strip() or None,
                docker_run_mode=str(raw.get("docker_run_mode", "")).strip() or None,
                fallback_targets=tuple(
                    str(item).strip()
                    for item in raw.get("fallback_targets", [])
                    if str(item).strip()
                ),
                metadata=dict(raw.get("metadata", {})) if isinstance(raw.get("metadata"), dict) else {},
            )
        )
    return resolved


def parse_vulkan_gpu_name(summary: str) -> str | None:
    waiting_for_name = False
    for raw_line in summary.splitlines():
        line = raw_line.strip()
        if waiting_for_name and line.startswith("deviceName"):
            return line.split("=", 1)[1].strip() or None
        if not line.startswith("GPU"):
            continue
        if " = " in line:
            return line.split(" = ", 1)[1].strip() or None
        if " : " in line:
            inline = line.split(" : ", 1)[1].strip()
            if inline:
                return inline
            waiting_for_name = True
            continue
        if line.endswith(":"):
            waiting_for_name = True
    return None


def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def _probe_gpu_name_hint() -> str | None:
    gfx_all = _detect_local_gfx_version()
    if gfx_all:
        return f"AMD GPU ({gfx_all})"

    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        result = _run_command([nvidia_smi, "--query-gpu=name", "--format=csv,noheader"])
        if result.returncode == 0:
            gpu_name = next((line.strip() for line in result.stdout.splitlines() if line.strip()), None)
            if gpu_name:
                return gpu_name

    vulkaninfo = shutil.which("vulkaninfo")
    if vulkaninfo:
        result = _run_command([vulkaninfo, "--summary"])
        if result.returncode == 0:
            gpu_name = parse_vulkan_gpu_name(result.stdout)
            if gpu_name:
                return gpu_name

    return None


def detect_host_acceleration(
    *,
    runner=_run_command,
    env: dict[str, str] | None = None,
) -> HostAcceleration:
    environment = os.environ if env is None else env
    override = _normalize_acceleration(environment.get("AUDIA_LOCAL_VALIDATION_ACCEL"))
    if override:
        gpu_name = _probe_gpu_name_hint()
        return HostAcceleration(
            host_acceleration=override,
            container_acceleration=choose_container_acceleration(
                override,
                host_platform=platform.system(),
                host_has_dri=Path("/dev/dri").exists(),
                override=environment.get("AUDIA_LOCAL_VALIDATION_CONTAINER_ACCEL"),
            ),
            supported_accelerations=supported_accelerations_for_host(override),
            gpu_name=gpu_name,
            reason="Host acceleration forced by AUDIA_LOCAL_VALIDATION_ACCEL",
        )

    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        result = runner([nvidia_smi, "--query-gpu=name", "--format=csv,noheader"])
        if result.returncode == 0:
            gpu_name = next((line.strip() for line in result.stdout.splitlines() if line.strip()), None)
            return HostAcceleration(
                host_acceleration="cuda",
                container_acceleration=choose_container_acceleration(
                    "cuda",
                    host_platform=platform.system(),
                    host_has_dri=Path("/dev/dri").exists(),
                    override=environment.get("AUDIA_LOCAL_VALIDATION_CONTAINER_ACCEL"),
                ),
                supported_accelerations=supported_accelerations_for_host("cuda"),
                gpu_name=gpu_name,
                reason="Detected NVIDIA GPU via nvidia-smi",
            )

    # Use the shared GFX detection logic to find AMD hardware even if rocm-smi is missing
    # (Especially important on Windows).
    gfx_all = _detect_local_gfx_version()
    if gfx_all:
        return HostAcceleration(
            host_acceleration="rocm",
            container_acceleration=choose_container_acceleration(
                "rocm",
                host_platform=platform.system(),
                host_has_dri=Path("/dev/dri").exists(),
                override=environment.get("AUDIA_LOCAL_VALIDATION_CONTAINER_ACCEL"),
            ),
            supported_accelerations=supported_accelerations_for_host("rocm"),
            gpu_name=f"AMD GPU ({gfx_all})",
            reason="Detected AMD GPU architectures via Device ID lookup",
        )

    vulkaninfo = shutil.which("vulkaninfo")
    if vulkaninfo:
        result = runner([vulkaninfo, "--summary"])
        if result.returncode == 0:
            gpu_name = parse_vulkan_gpu_name(result.stdout)
            if gpu_name:
                return HostAcceleration(
                    host_acceleration="vulkan",
                    container_acceleration=choose_container_acceleration(
                        "vulkan",
                        host_platform=platform.system(),
                        host_has_dri=Path("/dev/dri").exists(),
                        override=environment.get("AUDIA_LOCAL_VALIDATION_CONTAINER_ACCEL"),
                    ),
                    supported_accelerations=supported_accelerations_for_host("vulkan"),
                    gpu_name=gpu_name,
                    reason="Detected Vulkan-capable GPU via vulkaninfo",
                )

    return HostAcceleration(
        host_acceleration="cpu",
        container_acceleration=choose_container_acceleration(
            "cpu",
            host_platform=platform.system(),
            host_has_dri=Path("/dev/dri").exists(),
            override=environment.get("AUDIA_LOCAL_VALIDATION_CONTAINER_ACCEL"),
        ),
        supported_accelerations=supported_accelerations_for_host("cpu"),
        gpu_name=None,
        reason="No supported host accelerator detected; using CPU",
    )


def choose_container_acceleration(
    host_acceleration: str,
    *,
    host_platform: str,
    host_has_dri: bool,
    override: str | None = None,
) -> str:
    normalized_override = _normalize_acceleration(override)
    if normalized_override:
        if normalized_override not in SUPPORTED_CONTAINER_ACCELERATIONS:
            return "cpu"
        return normalized_override

    normalized_host = _normalize_acceleration(host_acceleration) or "cpu"
    if normalized_host == "vulkan" and host_platform == "Linux" and host_has_dri:
        return "vulkan"
    return "cpu"


def llama_variant_for_acceleration(container_acceleration: str) -> str:
    normalized = _normalize_acceleration(container_acceleration) or "cpu"
    if normalized == "vulkan":
        return "vulkan"
    return "cpu"


def native_llama_cpp_profile_for_acceleration(
    host_acceleration: str,
    *,
    host_platform: str | None = None,
) -> str:
    normalized = _normalize_acceleration(host_acceleration) or "cpu"
    system = (host_platform or platform.system()).strip()

    if system == "Windows":
        if normalized == "vulkan":
            return "windows-vulkan"
        if normalized == "rocm":
            return "windows-hip"
        return "windows-cpu"
    if system == "Linux":
        if normalized == "vulkan":
            return "linux-vulkan"
        if normalized == "rocm":
            return "linux-rocm"
        if normalized == "cuda":
            return "linux-cuda"
        return "linux-cpu"
    if system == "Darwin":
        return "macos-metal"
    return "linux-cpu"


def native_smoke_model_for_acceleration(
    host_acceleration: str,
    *,
    validation_profile: str = DEFAULT_VALIDATION_PROFILE,
    root: str | Path = DEFAULT_VALIDATION_ROOT,
) -> str:
    normalized = _normalize_acceleration(host_acceleration) or "cpu"
    profile = _normalize_validation_profile(validation_profile)
    profile_labels = validation_profile_native_models(root, profile)
    if not profile_labels:
        raise ValueError(f"Validation profile '{profile}' does not define native_models")
    return profile_labels.get(normalized, profile_labels["cpu"])


def summarize_device_selection(command: str | list[str] | tuple[str, ...] | None) -> dict[str, Any] | None:
    if not command:
        return None
    if isinstance(command, str):
        tokens = shlex.split(command)
    else:
        tokens = [str(item) for item in command if str(item).strip()]

    values: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "--device" and index + 1 < len(tokens):
            values.append(tokens[index + 1])
            index += 2
            continue
        if token.startswith("--device="):
            values.append(token.split("=", 1)[1].strip())
        index += 1

    devices: list[str] = []
    for value in values:
        for device in value.split(","):
            cleaned = device.strip()
            if cleaned:
                devices.append(cleaned)

    if not devices:
        return None

    lowered = [device.lower() for device in devices]
    family = "unknown"
    if any(device.startswith("vulkan") for device in lowered):
        family = "vulkan"
    elif any(device.startswith("rocm") or device.startswith("hip") for device in lowered):
        family = "rocm"
    elif any(device.startswith("cuda") for device in lowered):
        family = "cuda"
    elif any(device.startswith("metal") for device in lowered):
        family = "metal"
    elif any(device == "cpu" for device in lowered):
        family = "cpu"

    return {
        "family": family,
        "raw": ",".join(values),
        "devices": devices,
        "device_count": len(devices),
    }
