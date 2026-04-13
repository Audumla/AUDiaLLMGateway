from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.launcher.local_backend_validation import (
    detect_host_acceleration,
    llama_variant_for_acceleration,
    load_validation_catalog,
    native_llama_cpp_profile_for_acceleration,
    native_smoke_model_for_acceleration,
)
from src.launcher.config_loader import deep_merge, load_model_catalog
from src.installer.release_installer import download_file
from scripts.smoke_runner import (
    _benchmark_request_suite,
    _chat_completion_request,
    _preload_chat_completion_route,
    _summarize_benchmark_rows,
    _wait_for_any,
)


def _total_memory_bytes() -> int | None:
    try:
        if os.name == "nt":
            class _MemoryStatusEx(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = _MemoryStatusEx()
            status.dwLength = ctypes.sizeof(_MemoryStatusEx)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):  # type: ignore[attr-defined]
                return int(status.ullTotalPhys)
            return None
        if hasattr(os, "sysconf") and "SC_PAGE_SIZE" in os.sysconf_names and "SC_PHYS_PAGES" in os.sysconf_names:
            return int(os.sysconf("SC_PAGE_SIZE")) * int(os.sysconf("SC_PHYS_PAGES"))
    except Exception:
        return None
    return None


def _benchmark_host_context(detection) -> dict[str, object]:
    host_label = detection.gpu_name or f"{platform.system()} {str(detection.host_acceleration).upper()}"
    return {
        "platform": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "memory_bytes": _total_memory_bytes(),
        "gpu_name": detection.gpu_name,
        "host_label": host_label,
        "host_acceleration": detection.host_acceleration,
        "container_acceleration": detection.container_acceleration,
        "reason": detection.reason,
        "supported_accelerations": list(detection.supported_accelerations),
    }


def _benchmark_settings_profile_details(validation_catalog: dict[str, object], profile_name: str) -> dict[str, object]:
    profiles = validation_catalog.get("benchmark_settings_profiles", {})
    if not isinstance(profiles, dict):
        profiles = {}
    profile = profiles.get(profile_name, {})
    if not isinstance(profile, dict):
        profile = {}
    native = profile.get("native", {})
    if not isinstance(native, dict):
        native = {}
    return {
        "profile": profile_name,
        "description": str(profile.get("description", "")),
        "native": native,
    }


def _benchmark_request_profile_details(validation_catalog: dict[str, object], profile_name: str) -> dict[str, object]:
    profiles = validation_catalog.get("benchmark_request_profiles", {})
    if not isinstance(profiles, dict):
        profiles = {}
    profile = profiles.get(profile_name, {})
    if not isinstance(profile, dict):
        profile = {}
    requests = profile.get("requests", [])
    if not isinstance(requests, list):
        requests = []
    return {
        "profile": profile_name,
        "description": str(profile.get("description", "")),
        "requests": requests,
    }


def _model_profile_for_label(root: Path, model_label: str) -> tuple[str, str, dict[str, object], dict[str, object]] | None:
    _, _, catalog = load_model_catalog(root)
    profiles = catalog.get("model_profiles", {})
    if not isinstance(profiles, dict):
        return None
    for profile_name, profile in profiles.items():
        if not isinstance(profile, dict):
            continue
        deployments = profile.get("deployments", {})
        if not isinstance(deployments, dict):
            continue
        for deployment_name, deployment in deployments.items():
            if not isinstance(deployment, dict):
                continue
            if str(deployment.get("label", "")).strip() == model_label:
                return str(profile_name), str(deployment_name), profile, deployment
    return None


def _source_model_display_name(source_page_url: str, model_filename: str, fallback: str) -> str:
    source_page = str(source_page_url or "").strip()
    filename = str(model_filename or "").strip()
    source_repo = ""
    if "huggingface.co/" in source_page:
        source_repo = (
            source_page.split("huggingface.co/", 1)[1]
            .strip("/")
            .replace("/tree/main", "")
            .replace("/blob/main", "")
        )
    if source_repo and filename:
        return f"{source_repo} / {filename}"
    if source_repo:
        return source_repo
    if filename:
        return filename
    return str(fallback or "").strip()


def _merge_runtime_presets(existing: list[str], additions: list[str]) -> list[str]:
    merged: list[str] = []
    for item in existing + additions:
        cleaned = str(item).strip()
        if cleaned and cleaned not in merged:
            merged.append(cleaned)
    return merged


def _write_native_benchmark_settings_overlay(
    root: Path,
    *,
    model_label: str,
    settings_profile: dict[str, object],
) -> Path | None:
    native_spec = settings_profile.get("native", {})
    if not isinstance(native_spec, dict) or not native_spec:
        return None
    resolved = _model_profile_for_label(root, model_label)
    if resolved is None:
        return None
    profile_name, _, profile, _ = resolved
    defaults = profile.get("defaults", {})
    if not isinstance(defaults, dict):
        defaults = {}
    runtime_presets = [str(item) for item in defaults.get("runtime_presets", []) if str(item).strip()]
    additions = [str(item) for item in native_spec.get("runtime_presets_add", []) if str(item).strip()]
    context_override = str(native_spec.get("context_preset", "")).strip()
    if not additions and not context_override:
        return None
    overlay_defaults: dict[str, object] = {}
    if context_override:
        overlay_defaults["context_preset"] = context_override
    if additions:
        overlay_defaults["runtime_presets"] = _merge_runtime_presets(runtime_presets, additions)
    elif runtime_presets:
        overlay_defaults["runtime_presets"] = runtime_presets
    if not overlay_defaults:
        return None

    overlay = {
        "model_profiles": {
            profile_name: {
                "defaults": overlay_defaults,
            }
        }
    }
    overlay_path = root / "config" / "local" / "models.private.yaml"
    overlay_path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, object] = {}
    if overlay_path.exists():
        try:
            loaded = yaml.safe_load(overlay_path.read_text(encoding="utf-8")) or {}
            if isinstance(loaded, dict):
                existing = loaded
        except Exception:
            existing = {}
    merged = deep_merge(existing, overlay)

    overlay_path.write_text(yaml.safe_dump(merged, sort_keys=False), encoding="utf-8")
    return overlay_path


def _benchmark_target_context(
    *,
    detection,
    docker_profile: dict[str, object],
    backend: str,
    image: str,
    model_path: Path,
    benchmark_settings_profile: str,
) -> dict[str, object]:
    backend_device_selection = {
        "family": backend,
        "devices": [detection.gpu_name] if detection.gpu_name else [],
        "device_count": 1 if detection.gpu_name else 0,
        "raw": detection.gpu_name or "",
    }
    return {
        "host": _benchmark_host_context(detection),
        "backend_device_selection": backend_device_selection,
        "target": {
            "kind": "docker-external-llama-server",
            "image": image,
            "backend": backend,
            "model_name": str(docker_profile["model_name"]),
            "model_url": str(docker_profile["model_url"]),
            "model_path": str(model_path),
            "min_size_bytes": docker_profile["min_size_bytes"],
            "benchmark_settings_profile": benchmark_settings_profile,
        },
    }


def _native_benchmark_context(
    *,
    detection,
    native_profile: str,
    native_model: str,
    llama_version: str,
    benchmark_settings_profile: str,
    install_state: dict[str, object] | None = None,
) -> dict[str, object]:
    model_display_name = native_model
    source_page_url = ""
    model_filename = ""
    backend_model_name = native_model
    resolved = _model_profile_for_label(REPO_ROOT, native_model)
    if resolved is not None:
        _, _, profile, deployment = resolved
        artifacts = profile.get("artifacts", {}) if isinstance(profile.get("artifacts"), dict) else {}
        source_page_url = str(deployment.get("source_page_url") or artifacts.get("source_page_url") or "").strip()
        model_filename = str(deployment.get("model_filename") or artifacts.get("model_filename") or "").strip()
        backend_model_name = str(deployment.get("backend_model_name") or deployment.get("llama_swap_model") or native_model).strip()
        model_display_name = _source_model_display_name(
            source_page_url,
            model_filename,
            str(
                deployment.get("backend_model_name")
                or deployment.get("llama_swap_model")
                or native_model
            ).strip(),
        )
    llama_cpp: dict[str, object] = {}
    if isinstance(install_state, dict):
        component_results = install_state.get("component_results", {})
        if isinstance(component_results, dict):
            llama_cpp_candidate = component_results.get("llama_cpp", {})
            if isinstance(llama_cpp_candidate, dict):
                llama_cpp = llama_cpp_candidate
    return {
        "host": _benchmark_host_context(detection),
        "target": {
            "kind": "native-smoke",
            "native_llama_cpp_profile": native_profile,
            "native_backend": _native_backend_from_profile(native_profile),
            "native_model": native_model,
            "model_display_name": model_display_name,
            "backend_model_name": backend_model_name,
            "model_filename": model_filename,
            "source_page_url": source_page_url,
            "llama_version": llama_version or None,
            "benchmark_settings_profile": benchmark_settings_profile,
        },
        "installation": {
            "llama_cpp_profile": llama_cpp.get("profile"),
            "llama_cpp_version": llama_cpp.get("version"),
            "llama_cpp_backend": llama_cpp.get("backend"),
            "llama_cpp_cache_hit": llama_cpp.get("cache_hit"),
            "llama_cpp_install_dir": llama_cpp.get("install_dir"),
            "llama_cpp_executable_path": llama_cpp.get("executable_path"),
        },
    }


def _run(command: list[str]) -> None:
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode != 0:
        hint = _diagnose_failure(completed.stderr or completed.stdout or "")
        if hint:
            print(f"[diagnostic] {hint}", file=sys.stderr)
        raise subprocess.CalledProcessError(
            completed.returncode,
            command,
            output=completed.stdout,
            stderr=completed.stderr,
        )


def _preferred_workspace_python() -> str:
    candidates = [
        REPO_ROOT / ".venv" / "Scripts" / "python.exe",
        REPO_ROOT / ".venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def _load_install_state(root: Path) -> dict[str, object]:
    state_path = root / "state" / "install-state.json"
    if not state_path.exists():
        return {}
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _diagnose_failure(message: str) -> str:
    lowered = message.lower()
    if "hipconfig.cmake" in lowered or "rocm sdk not available" in lowered:
        return "ROCm/HIP SDK is missing or incomplete; bootstrap or point ROCM_PATH/HIP_PATH at a valid install."
    if "vulkan sdk not available" in lowered or "glslc" in lowered or "vulkan_library" in lowered:
        return "Vulkan SDK is missing or incomplete; bootstrap or point AUDIA_VULKAN_SDK_SOURCE/VULKAN_SDK at a valid install."
    if "git is required" in lowered:
        return "Git is missing, so git-backed llama.cpp profiles cannot be checked out."
    if "did not produce a binary" in lowered or "did not contain" in lowered:
        return "The source build completed but the expected llama-server binary was not found in the build output."
    if "health check failed" in lowered or "502" in lowered or "bad gateway" in lowered:
        return "The backend started but the gateway/runtime health check failed; inspect routing and server logs."
    return ""


def _seed_native_smoke_workspace(root: Path) -> None:
    source_local = REPO_ROOT / "config" / "local"
    target_local = root / "config" / "local"
    target_local.mkdir(parents=True, exist_ok=True)
    for source in source_local.glob("*.yaml"):
        shutil.copy2(source, target_local / source.name)


def _native_backend_from_profile(profile_name: str) -> str:
    lowered = profile_name.lower()
    if lowered.endswith("vulkan"):
        return "vulkan"
    if lowered.endswith("rocm"):
        return "rocm"
    if lowered.endswith("cuda"):
        return "cuda"
    return "cpu"


def _expected_llama_executable(root: Path, *, version: str, backend: str) -> Path:
    install_dir = root / "tools" / "llama.cpp" / f"{version}-{backend}"
    candidates = [
        install_dir / "llama-server.exe",
        install_dir / "llama-server",
        install_dir / "bin" / "llama-server.exe",
        install_dir / "bin" / "llama-server",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _write_native_stack_overlay(root: Path, *, profile_name: str, llama_version: str | None) -> Path:
    overlay_path = root / "config" / "local" / "stack.private.yaml"
    import yaml
    profile_overlay: dict[str, object] = {}
    if llama_version:
        profile_overlay["version"] = llama_version
    overlay = {
        "component_settings": {
            "llama_cpp": {
                "selected_profile": profile_name,
                "profiles": {
                    profile_name: profile_overlay,
                },
            }
        },
        "routing": {
            "notes": [
                f"Native validation overlay selected llama.cpp profile '{profile_name}'.",
            ]
        },
    }
    overlay_path.parent.mkdir(parents=True, exist_ok=True)
    overlay_path.write_text(yaml.safe_dump(overlay, sort_keys=False), encoding="utf-8")
    return overlay_path


def _read_installed_llama_executable(root: Path) -> Path:
    state_path = root / "state" / "install-state.json"
    data = json.loads(state_path.read_text(encoding="utf-8"))
    executable = data["component_results"]["llama_cpp"]["executable_path"]
    return Path(str(executable))


def _read_installed_llama_variants(root: Path) -> tuple[dict[str, str], str | None]:
    state_path = root / "state" / "install-state.json"
    data = json.loads(state_path.read_text(encoding="utf-8"))
    llama_cpp = data.get("component_results", {}).get("llama_cpp", {})
    if not isinstance(llama_cpp, dict):
        return {}, None
    variants = llama_cpp.get("variants", {})
    macros: dict[str, str] = {}
    if isinstance(variants, dict):
        for info in variants.values():
            if not isinstance(info, dict):
                continue
            backend = str(info.get("backend", "")).strip().lower()
            executable = str(info.get("executable_path", "")).strip()
            if backend and executable:
                macros[f"llama-server-{backend}"] = executable
                if backend == "rocm":
                    macros["llama-server-hip"] = executable
    default_executable = str(llama_cpp.get("executable_path", "")).strip() or None
    return macros, default_executable


def _write_native_llama_swap_overlay(root: Path, *, executable: Path) -> Path:
    model_root = root / "models"
    import yaml
    variant_macros, default_executable = _read_installed_llama_variants(root)
    active_executable = str(executable)
    macros = {
        "llama-server": default_executable or active_executable,
        "model-path": f"--model {model_root}",
        "mmproj-path": f"--mmproj {model_root}",
    }
    macros.update(variant_macros)
    if not variant_macros:
        # Fall back to the active executable only when install-state has no per-backend variants.
        macros["llama-server-cpu"] = active_executable
    overlay = {
        "macros": macros
    }
    overlay_path = root / "config" / "local" / "llama-swap.private.yaml"
    overlay_path.parent.mkdir(parents=True, exist_ok=True)
    overlay_path.write_text(yaml.safe_dump(overlay, sort_keys=False), encoding="utf-8")
    return overlay_path


def _docker_build_command(*, image: str, llama_version: str, llama_variant: str) -> list[str]:
    return [
        "docker",
        "build",
        "--network=host",
        "-f",
        "tests/docker/Dockerfile.integration",
        "-t",
        image,
        "--build-arg",
        f"LLAMA_VERSION={llama_version}",
        "--build-arg",
        f"LLAMA_VARIANT={llama_variant}",
        ".",
    ]


def _docker_run_command(
    *,
    image: str,
    model_cache: Path,
    detection,
    validation_profile: str,
    docker_profile: dict[str, object],
    benchmark_output: Path | None,
    benchmark_prompt: str,
    benchmark_max_tokens: int,
) -> list[str]:
    run_command = [
        "docker",
        "run",
        "--rm",
    ]
    if detection.container_acceleration == "vulkan":
        run_command.extend(["--device", "/dev/dri:/dev/dri"])
    run_command.extend(
        [
            "-v",
            f"{model_cache}:/models",
            "-e",
            "MODEL_DIR=/models",
            "-e",
            "LITELLM_MASTER_KEY=sk-test",
            "-e",
            f"AUDIA_HOST_ACCEL={detection.host_acceleration}",
            "-e",
            f"AUDIA_CONTAINER_ACCEL={detection.container_acceleration}",
            "-e",
            f"AUDIA_LLAMA_VARIANT={llama_variant_for_acceleration(detection.container_acceleration)}",
            "-e",
            f"AUDIA_VALIDATION_PROFILE={validation_profile}",
            "-e",
            f"AUDIA_VALIDATION_MODEL_NAME={docker_profile['model_name']}",
            "-e",
            f"AUDIA_VALIDATION_MODEL_URL={docker_profile['model_url']}",
            "-e",
            f"AUDIA_VALIDATION_MODEL_MIN_SIZE={docker_profile['min_size_bytes']}",
            "-e",
            f"AUDIA_BENCHMARK_PROMPT={benchmark_prompt}",
            "-e",
            f"AUDIA_BENCHMARK_MAX_TOKENS={benchmark_max_tokens}",
        ]
    )
    if benchmark_output is not None:
        output_dir = benchmark_output.parent.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        run_command.extend(["-v", f"{output_dir}:/benchmark"])
        run_command.extend(["-e", f"AUDIA_BENCHMARK_OUTPUT=/benchmark/{benchmark_output.name}"])
    if detection.gpu_name:
        run_command.extend(["-e", f"AUDIA_HOST_GPU_NAME={detection.gpu_name}"])
    run_command.append(image)
    return run_command


def _ensure_validation_model(model_cache: Path, docker_profile: dict[str, object]) -> Path:
    model_name = str(docker_profile["model_name"])
    model_url = str(docker_profile["model_url"])
    target = model_cache / model_name
    if not target.exists():
        download_file(model_url, target)
    return target


def _docker_external_llama_server_command(
    *,
    image: str,
    model_cache: Path,
    model_path: Path,
    backend: str,
    port: int,
) -> list[str]:
    command = [
        "docker",
        "run",
        "--rm",
        "-d",
        "-p",
        f"{port}:8080",
        "-v",
        f"{model_cache}:/models",
    ]
    if backend == "rocm":
        command.extend(["--device", "/dev/kfd", "--device", "/dev/dri", "--group-add", "video", "--ipc=host"])
    elif backend == "vulkan":
        command.extend(["--device", "/dev/dri:/dev/dri"])
    command.extend(
        [
            "--entrypoint",
            "llama-server",
            image,
            "-m",
            f"/models/{model_path.name}",
            "--host",
            "0.0.0.0",
            "--port",
            "8080",
            "-ngl",
            "99",
            "-fa",
            "on",
        ]
    )
    return command


def _run_external_docker_benchmark(
    *,
    image: str,
    model_cache: Path,
    docker_profile: dict[str, object],
    backend: str,
    prompt: str,
    max_tokens: int,
    benchmark_requests: list[dict[str, object]],
    benchmark_output: Path | None,
    benchmark_context: dict[str, object] | None,
) -> None:
    model_path = _ensure_validation_model(model_cache, docker_profile)
    port = 41991
    command = _docker_external_llama_server_command(
        image=image,
        model_cache=model_cache,
        model_path=model_path,
        backend=backend,
        port=port,
    )
    container_id = ""
    try:
        model_cache.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(command, capture_output=True, text=True, check=True)
        container_id = completed.stdout.strip()
        base_url = f"http://127.0.0.1:{port}"
        ok, _ = _wait_for_any([f"{base_url}/health"], timeout=180.0, interval=2.0)
        if not ok:
            raise RuntimeError(f"{image} did not become healthy on port {port}")
        preload_result: dict[str, object] | None = None
        preload_error: str | None = None
        try:
            preload_result = _preload_chat_completion_route(
                base_url=base_url,
                model_name="direct-llama-server",
                max_tokens=max_tokens,
            )
        except Exception as exc:
            preload_error = str(exc)
        samples: list[dict[str, object]] = []
        request_suite = benchmark_requests or _benchmark_request_suite(prompt, max_tokens)
        for index, request in enumerate(request_suite, start=1):
            sample_label = str(request.get("label", f"sample-{index}"))
            sample_prompt = str(request.get("prompt", prompt))
            sample_max_tokens = int(request.get("max_tokens", max_tokens) or max_tokens)
            try:
                result = _chat_completion_request(
                    base_url=base_url,
                    model_name="direct-llama-server",
                    prompt=sample_prompt,
                    max_tokens=sample_max_tokens,
                )
                samples.append(
                    {
                        "sample_index": index,
                        "sample_label": sample_label,
                        "sample_count": len(request_suite),
                        "prompt": sample_prompt,
                        "max_tokens": sample_max_tokens,
                        "model": model_path.name,
                        "route": "direct-llama-server",
                        "benchmark_mode": "timed",
                        "base_url": base_url,
                        "preload": preload_result,
                        "preload_error": preload_error,
                        "elapsed_seconds": result["elapsed_seconds"],
                        "completion_tokens": result["completion_tokens"],
                        "tok_per_sec": result["tok_per_sec"],
                        "backend_tok_per_sec": result.get("backend_tok_per_sec"),
                        "finish_reason": result["finish_reason"],
                        "timings": result.get("timings", {}),
                        "image": image,
                    }
                )
            except Exception as exc:
                samples.append(
                    {
                        "sample_index": index,
                        "sample_label": sample_label,
                        "sample_count": len(request_suite),
                        "prompt": sample_prompt,
                        "max_tokens": sample_max_tokens,
                        "model": model_path.name,
                        "route": "direct-llama-server",
                        "benchmark_mode": "timed",
                        "base_url": base_url,
                        "preload": preload_result,
                        "preload_error": preload_error,
                        "error": str(exc),
                        "image": image,
                    }
                )
        if benchmark_output is not None:
            benchmark_output.parent.mkdir(parents=True, exist_ok=True)
            benchmark_output.write_text(
                json.dumps(
                    {
                        "route": "direct-llama-server",
                        "prompt": prompt,
                        "max_tokens": max_tokens,
                        "benchmark_suite": request_suite,
                        "benchmark_context": benchmark_context or {},
                        "results": samples,
                        "summary": _summarize_benchmark_rows(samples),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
    finally:
        if container_id:
            subprocess.run(["docker", "stop", container_id], check=False, capture_output=True, text=True)


def _native_command(
    *,
    native_root: Path,
    model_label: str,
    install: bool,
    stage: int,
    benchmark_suite_json: str = "",
) -> list[str]:
    command = [
        _preferred_workspace_python(),
        "scripts/smoke_runner.py",
        "--root",
        str(native_root),
        "--stage",
        str(stage),
        "--model",
        model_label,
    ]
    if install:
        command.append("--install")
    if benchmark_suite_json:
        command.extend(["--benchmark-suite-json", benchmark_suite_json])
    return command


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run local backend validation using a switchable Qwen smoke model. "
            "Docker mode validates the portable container path; native mode uses smoke_runner "
            "to validate the host-selected backend lane."
        )
    )
    parser.add_argument("--image", default="audia-integration", help="Docker image tag")
    parser.add_argument("--llama-version", default="", help="Optional llama.cpp release tag or exact ref override")
    parser.add_argument(
        "--mode",
        choices=("docker", "native", "all"),
        default="docker",
        help="Validation mode: Docker only, native only, or both in sequence",
    )
    _, _, validation_catalog = load_validation_catalog(REPO_ROOT)
    default_profile = str(validation_catalog.get("defaults", {}).get("validation_profile", "quick"))
    profile_choices = tuple(validation_catalog.get("profiles", {}).keys())
    parser.add_argument(
        "--validation-profile",
        choices=profile_choices,
        default=default_profile,
        help="Validation model profile from config/project/backend-validation.base.yaml",
    )
    parser.add_argument(
        "--model-cache",
        default=str(Path("test-work/models").resolve()),
        help="Host model cache directory mounted into the Docker container",
    )
    parser.add_argument(
        "--native-root",
        default=str(Path("test-work/native-backend-validation").resolve()),
        help="Workspace root for the native smoke validation run",
    )
    parser.add_argument(
        "--native-model",
        default="",
        help="Optional stable model label override for native validation",
    )
    parser.add_argument(
        "--native-llama-cpp-profile",
        default="",
        help="Optional explicit llama.cpp installer profile override for native validation",
    )
    parser.add_argument(
        "--benchmark-output",
        default="",
        help="Optional JSON file path to store benchmark results for this run",
    )
    parser.add_argument(
        "--benchmark-settings-profile",
        default="default",
        help="Named llama.cpp benchmark settings profile to apply to the native run",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the selected configuration and commands without executing them",
    )
    parser.add_argument(
        "--docker-image-override",
        default="",
        help="Optional external Docker image ref to benchmark directly instead of building the integration image.",
    )
    parser.add_argument(
        "--docker-run-mode",
        choices=("integration", "external-llama-server"),
        default="integration",
        help="Docker validation mode for the selected target.",
    )
    args = parser.parse_args()

    detection = detect_host_acceleration()
    llama_variant = llama_variant_for_acceleration(detection.container_acceleration)
    model_cache = Path(args.model_cache).resolve()
    native_root = Path(args.native_root).resolve()
    native_profile = args.native_llama_cpp_profile or native_llama_cpp_profile_for_acceleration(detection.host_acceleration)
    validation_profile = args.validation_profile
    profile_details = validation_catalog["profiles"][validation_profile]
    docker_profile = profile_details["docker"]
    benchmark_settings = validation_catalog.get("defaults", {}).get("benchmark", {})
    benchmark_settings_profile_name = str(args.benchmark_settings_profile or "default").strip() or "default"
    benchmark_settings_profile = _benchmark_settings_profile_details(validation_catalog, benchmark_settings_profile_name)
    benchmark_request_profile_name = str(benchmark_settings.get("request_profile", "medium_mix")).strip() or "medium_mix"
    benchmark_request_profile = _benchmark_request_profile_details(validation_catalog, benchmark_request_profile_name)
    benchmark_requests = _benchmark_request_suite(
        str(benchmark_settings.get("prompt", "Reply with one short sentence confirming this request was handled.")),
        int(benchmark_settings.get("max_tokens", 48)),
        benchmark_request_profile.get("requests"),
    )
    benchmark_prompt = str(benchmark_settings.get("prompt", "Reply with one short sentence confirming this request was handled."))
    benchmark_max_tokens = int(benchmark_settings.get("max_tokens", 48))
    benchmark_output = Path(args.benchmark_output).resolve() if args.benchmark_output else None
    native_model = args.native_model or native_smoke_model_for_acceleration(
        detection.host_acceleration,
        validation_profile=validation_profile,
    )

    print(f"Host acceleration: {detection.host_acceleration}")
    if detection.gpu_name:
        print(f"Host GPU: {detection.gpu_name}")
    print(f"Container acceleration: {detection.container_acceleration}")
    print(f"Docker llama.cpp asset variant: {llama_variant}")
    print(f"Validation profile: {validation_profile} ({profile_details['description']})")
    print(f"Native llama.cpp profile: {native_profile}")
    print(f"Native smoke model: {native_model}")
    print(f"Benchmark settings profile: {benchmark_settings_profile_name} ({benchmark_settings_profile['description']})")
    print(f"Benchmark request profile: {benchmark_request_profile_name} ({benchmark_request_profile['description']})")
    print(f"Reason: {detection.reason}")
    if benchmark_output is not None:
        print(f"Benchmark output: {benchmark_output}")

    docker_build = _docker_build_command(
        image=args.image,
        llama_version=args.llama_version,
        llama_variant=llama_variant,
    )
    docker_run = _docker_run_command(
        image=args.image,
        model_cache=model_cache,
        detection=detection,
        validation_profile=validation_profile,
        docker_profile=docker_profile,
        benchmark_output=benchmark_output if args.mode == "docker" else None,
        benchmark_prompt=benchmark_prompt,
        benchmark_max_tokens=benchmark_max_tokens,
    )

    _seed_native_smoke_workspace(native_root)
    benchmark_settings_overlay = _write_native_benchmark_settings_overlay(
        native_root,
        model_label=native_model,
        settings_profile=benchmark_settings_profile,
    )
    if benchmark_settings_overlay is not None:
        print(f"Native benchmark settings overlay: {benchmark_settings_overlay}")
    overlay_path = _write_native_stack_overlay(
        native_root,
        profile_name=native_profile,
        llama_version=args.llama_version,
    )
    native_install_command = _native_command(
        native_root=native_root,
        model_label=native_model,
        install=True,
        stage=0,
        benchmark_suite_json=json.dumps(benchmark_requests),
    )
    native_validate_command = _native_command(
        native_root=native_root,
        model_label=native_model,
        install=False,
        stage=5,
        benchmark_suite_json=json.dumps(benchmark_requests),
    )
    if benchmark_output is not None and args.mode in {"native", "all"}:
        native_validate_command.extend(
            [
                "--benchmark-output",
                str(benchmark_output),
                "--benchmark-prompt",
                benchmark_prompt,
                "--benchmark-max-tokens",
                str(benchmark_max_tokens),
                "--benchmark-suite-json",
                json.dumps(benchmark_requests),
                "--benchmark-context-json",
                json.dumps(
                    _native_benchmark_context(
                        detection=detection,
                        native_profile=native_profile,
                        native_model=native_model,
                        llama_version=args.llama_version,
                        benchmark_settings_profile=benchmark_settings_profile_name,
                        install_state=_load_install_state(native_root),
                    )
                ),
            ]
        )

    print(f"Native workspace: {native_root}")
    print(f"Native overlay: {overlay_path}")

    if args.dry_run:
        if args.mode in {"docker", "all"}:
            if args.docker_image_override and args.docker_run_mode == "external-llama-server":
                model_path = model_cache / str(docker_profile["model_name"])
                print(
                    "Docker run:",
                    subprocess.list2cmdline(
                        _docker_external_llama_server_command(
                            image=args.docker_image_override,
                            model_cache=model_cache,
                            model_path=model_path,
                            backend=detection.container_acceleration,
                            port=41991,
                        )
                    ),
                )
            else:
                print("Docker build:", subprocess.list2cmdline(docker_build))
                print("Docker run:", subprocess.list2cmdline(docker_run))
        if args.mode in {"native", "all"}:
            print("Native install:", subprocess.list2cmdline(native_install_command))
            print("Native smoke:", subprocess.list2cmdline(native_validate_command))
        return 0

    if args.mode in {"docker", "all"}:
        model_cache.mkdir(parents=True, exist_ok=True)
        if args.docker_image_override and args.docker_run_mode == "external-llama-server":
            _run_external_docker_benchmark(
                image=args.docker_image_override,
                model_cache=model_cache,
                docker_profile=docker_profile,
                backend=detection.container_acceleration,
                prompt=benchmark_prompt,
                max_tokens=benchmark_max_tokens,
                benchmark_requests=benchmark_requests,
                benchmark_output=benchmark_output if args.mode == "docker" else None,
                benchmark_context=_benchmark_target_context(
                    detection=detection,
                    docker_profile=docker_profile,
                    backend=detection.container_acceleration,
                    image=args.docker_image_override,
                    model_path=model_cache / str(docker_profile["model_name"]),
                    benchmark_settings_profile=benchmark_settings_profile_name,
                ),
            )
        else:
            _run(docker_build)
            _run(docker_run)
    if args.mode in {"native", "all"}:
        _run(native_install_command)
        installed_executable = _read_installed_llama_executable(native_root)
        llama_swap_overlay_path = _write_native_llama_swap_overlay(
            native_root,
            executable=installed_executable,
        )
        print(f"Native llama-swap overlay: {llama_swap_overlay_path}")
        _run(native_validate_command)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"Command failed with exit code {exc.returncode}", file=sys.stderr)
        raise
