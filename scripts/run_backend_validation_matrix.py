from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import statistics
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.installer.release_installer import build_toolchain_env
from src.launcher.config_loader import load_stack_config
from src.launcher.local_backend_validation import (
    detect_host_acceleration,
    load_validation_catalog,
    resolve_validation_targets,
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


def _normalize_platform_name(value: str | None = None) -> str:
    system = (value or platform.system()).strip().lower()
    if system == "darwin":
        return "macos"
    return system


def _selected_profiles(validation_catalog: dict[str, Any], requested: list[str], *, all_profiles: bool) -> list[str]:
    available = validation_catalog.get("profiles", {})
    if not isinstance(available, dict) or not available:
        raise ValueError("Validation catalog does not define any profiles")
    if all_profiles:
        return list(available.keys())
    if requested:
        missing = [name for name in requested if name not in available]
        if missing:
            raise ValueError(f"Unknown validation profile(s): {', '.join(missing)}")
        return requested
    default_profile = str(validation_catalog.get("defaults", {}).get("validation_profile", "quick"))
    return [default_profile]


def _benchmark_file(results_dir: Path, *, profile_name: str, target_name: str) -> Path:
    return results_dir / f"{profile_name}__{target_name}.json"


def _default_vulkan_sdk_source(platform_name: str) -> Path:
    return REPO_ROOT / "test-work" / "toolchains" / "vulkan-sdk" / platform_name


def _configure_native_toolchain_env(*, target, native_profile: str | None, native_root: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    profile = None
    if native_profile:
        try:
            stack = load_stack_config(REPO_ROOT)
            llama_cpp_settings = stack.component_settings.get("llama_cpp", {})
            profiles = llama_cpp_settings.get("profiles", {}) if isinstance(llama_cpp_settings, dict) else {}
            candidate = profiles.get(native_profile)
            if isinstance(candidate, dict):
                profile = candidate
        except Exception:
            profile = None
    if isinstance(profile, dict) and (profile.get("source_type") == "git" or profile.get("required_toolchains")):
        toolchain_env, _ = build_toolchain_env(native_root, profile, _normalize_platform_name())
        env.update(toolchain_env)
        return env
    if target.backend == "vulkan":
        platform_name = _normalize_platform_name()
        env["AUDIA_VULKAN_SDK_ROOT"] = str(native_root / "toolchains" / "vulkan-sdk" / platform_name)
        source_sdk = _default_vulkan_sdk_source(platform_name)
        if source_sdk.exists():
            env["AUDIA_VULKAN_SDK_SOURCE"] = str(source_sdk)
    return env


def _build_target_command(
    *,
    target,
    profile_name: str,
    benchmark_settings_profile: str,
    benchmark_output: Path,
    image: str,
    llama_version: str,
    model_cache: Path,
    native_root_base: Path,
) -> tuple[list[str], dict[str, str]]:
    command = [
        _preferred_workspace_python(),
        "scripts/run_local_backend_validation.py",
        "--mode",
        target.transport,
        "--validation-profile",
        profile_name,
        "--benchmark-output",
        str(benchmark_output),
        "--benchmark-settings-profile",
        benchmark_settings_profile,
        "--image",
        image,
        "--llama-version",
        llama_version,
        "--model-cache",
        str(model_cache),
    ]
    env = os.environ.copy()
    if target.transport == "docker":
        if target.docker_image:
            command.extend(
                [
                    "--docker-image-override",
                    str(target.docker_image),
                    "--docker-run-mode",
                    str(target.docker_run_mode or "external-llama-server"),
                ]
            )
        env["AUDIA_LOCAL_VALIDATION_CONTAINER_ACCEL"] = target.backend
    else:
        native_root = native_root_base / profile_name / target.name
        command.extend(
            [
                "--native-root",
                str(native_root),
                "--native-llama-cpp-profile",
                str(target.native_profile),
                "--native-model",
                str(target.native_model_label),
            ]
        )
        env.update(_configure_native_toolchain_env(target=target, native_profile=target.native_profile, native_root=native_root))
    return command, env


def _summarize_benchmark(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("results", [])
    if not isinstance(rows, list):
        rows = []
    context = data.get("benchmark_context", {})
    if not isinstance(context, dict):
        context = {}
    successes = [row for row in rows if isinstance(row, dict) and not row.get("error") and isinstance(row.get("tok_per_sec"), (int, float))]
    client_speeds = [float(row.get("tok_per_sec", 0.0) or 0.0) for row in successes]
    backend_speeds = [float(row.get("backend_tok_per_sec", 0.0) or 0.0) for row in successes if isinstance(row.get("backend_tok_per_sec"), (int, float))]
    elapsed_speeds = [float(row.get("elapsed_seconds", 0.0) or 0.0) for row in successes if isinstance(row.get("elapsed_seconds"), (int, float))]
    summary = data.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}
    top_speed = float(summary.get("client_avg_tok_per_sec") or (statistics.mean(client_speeds) if client_speeds else 0.0))
    top_backend_speed = float(summary.get("backend_avg_tok_per_sec") or (statistics.mean(backend_speeds) if backend_speeds else 0.0))
    return {
        "path": str(path),
        "result_count": len(rows),
        "success_count": len(successes),
        "sample_count": int(summary.get("sample_count", len(rows)) or len(rows)),
        "top_tok_per_sec": top_speed,
        "client_avg_tok_per_sec": top_speed,
        "backend_top_tok_per_sec": top_backend_speed,
        "backend_avg_tok_per_sec": top_backend_speed,
        "round_trip_avg_seconds": float(summary.get("round_trip_avg_seconds") or (statistics.mean(elapsed_speeds) if elapsed_speeds else 0.0)),
        "client_min_tok_per_sec": summary.get("client_min_tok_per_sec"),
        "client_max_tok_per_sec": summary.get("client_max_tok_per_sec"),
        "backend_min_tok_per_sec": summary.get("backend_min_tok_per_sec"),
        "backend_max_tok_per_sec": summary.get("backend_max_tok_per_sec"),
        "benchmark_context": context,
        "results": rows,
    }


def _failure_result(
    *,
    profile_name: str,
    target,
    benchmark_output: Path,
    error: Exception,
    benchmark_settings_profile: str,
) -> dict[str, Any]:
    failure_kind, failure_hint, status = _diagnose_failure(str(error))
    return {
        "profile": profile_name,
        "target": target.name,
        "transport": target.transport,
        "backend": target.backend,
        "experimental": target.experimental,
        "benchmark_settings_profile": benchmark_settings_profile,
        "returncode": None,
        "status": status,
        "failure_kind": failure_kind,
        "failure_hint": failure_hint,
        "benchmark_output": str(benchmark_output),
        "error": str(error),
    }


def _run_single_target(
    *,
    target,
    profile_name: str,
    benchmark_settings_profile: str,
    benchmark_output: Path,
    image: str,
    llama_version: str,
    model_cache: Path,
    native_root_base: Path,
    fallback_of: str | None = None,
) -> dict[str, Any]:
    try:
        command, env = _build_target_command(
            target=target,
            profile_name=profile_name,
            benchmark_settings_profile=benchmark_settings_profile,
            benchmark_output=benchmark_output,
            image=image,
            llama_version=target.llama_version or llama_version,
            model_cache=model_cache,
            native_root_base=native_root_base,
        )
    except Exception as exc:
        row = _failure_result(
            profile_name=profile_name,
            target=target,
            benchmark_output=benchmark_output,
            error=exc,
            benchmark_settings_profile=benchmark_settings_profile,
        )
        if fallback_of:
            row["fallback_of"] = fallback_of
        return row

    print(f"\n=== {profile_name} / {target.name} ===")
    completed = subprocess.run(command, env=env, check=False)
    row: dict[str, Any] = {
        "profile": profile_name,
        "target": target.name,
        "transport": target.transport,
        "backend": target.backend,
        "experimental": target.experimental,
        "benchmark_settings_profile": benchmark_settings_profile,
        "returncode": completed.returncode,
        "status": "passed" if completed.returncode == 0 else "failed",
        "benchmark_output": str(benchmark_output),
    }
    if fallback_of:
        row["fallback_of"] = fallback_of
    if completed.returncode == 0 and benchmark_output.exists():
        row["benchmark"] = _summarize_benchmark(benchmark_output)
        install_ctx = row["benchmark"].get("benchmark_context", {}).get("installation", {})
        if isinstance(install_ctx, dict):
            row["install_cache_hit"] = install_ctx.get("llama_cpp_cache_hit")
            row["llama_cpp_install_dir"] = install_ctx.get("llama_cpp_install_dir")
    return row


def _run_target_with_fallbacks(
    *,
    target,
    profile_name: str,
    benchmark_settings_profile: str,
    image: str,
    llama_version: str,
    model_cache: Path,
    native_root_base: Path,
    target_lookup: dict[str, Any],
    completed_targets: set[str],
    results_dir: Path,
) -> tuple[list[dict[str, Any]], int]:
    if target.name in completed_targets:
        return [], 0

    benchmark_output = _benchmark_file(results_dir, profile_name=profile_name, target_name=target.name)
    if benchmark_output.exists():
        benchmark_output.unlink()

    rows: list[dict[str, Any]] = []
    failures = 0

    row = _run_single_target(
        target=target,
        profile_name=profile_name,
        benchmark_settings_profile=benchmark_settings_profile,
        benchmark_output=benchmark_output,
        image=image,
        llama_version=llama_version,
        model_cache=model_cache,
        native_root_base=native_root_base,
    )
    rows.append(row)
    completed_targets.add(target.name)
    if row.get("status") == "passed":
        return rows, 0

    resolved_by_fallback = False
    for fallback_name in getattr(target, "fallback_targets", ()):
        fallback_target = target_lookup.get(fallback_name)
        if fallback_target is None or fallback_target.name in completed_targets:
            continue
        fallback_output = _benchmark_file(results_dir, profile_name=profile_name, target_name=fallback_target.name)
        if fallback_output.exists():
            fallback_output.unlink()
        print(f"  Fallback -> {fallback_target.name}")
        fallback_row = _run_single_target(
            target=fallback_target,
            profile_name=profile_name,
            benchmark_settings_profile=benchmark_settings_profile,
            benchmark_output=fallback_output,
            image=image,
            llama_version=llama_version,
            model_cache=model_cache,
            native_root_base=native_root_base,
            fallback_of=target.name,
        )
        rows.append(fallback_row)
        completed_targets.add(fallback_target.name)
        if fallback_row.get("status") == "passed":
            resolved_by_fallback = True
            break

    if not resolved_by_fallback:
        failures = 1
    return rows, failures


def _diagnose_failure(message: str) -> tuple[str, str, str]:
    lowered = message.lower()
    if "sdk not available" in lowered or "hipconfig.cmake" in lowered:
        return (
            "missing_toolchain",
            "Bootstrap or point the workspace at the missing ROCm/HIP or Vulkan SDK before rerunning.",
            "skipped",
        )
    if "git is required" in lowered:
        return ("missing_dependency", "Install git so git-backed llama.cpp profiles can be checked out.", "failed")
    if "did not produce a binary" in lowered or "did not contain" in lowered:
        return ("build_output_missing", "The source build finished but the expected llama-server binary was not found.", "failed")
    if "health check failed" in lowered or "502" in lowered or "bad gateway" in lowered:
        return (
            "runtime_failure",
            "The backend likely started, but the gateway or health check failed; inspect the stage-5 logs.",
            "failed",
        )
    if "cmake" in lowered and "error" in lowered:
        return ("build_failure", "CMake reported an error during configure or build.", "failed")
    return ("unknown", "Inspect the printed command output and logs for the underlying cause.", "failed")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the config-driven backend validation matrix for the current platform and collect benchmark output."
    )
    _, _, validation_catalog = load_validation_catalog(REPO_ROOT)
    parser.add_argument("--image", default="audia-integration", help="Docker image tag for docker targets")
    parser.add_argument(
        "--llama-version",
        default="",
        help="Optional fallback llama.cpp version or tag override for targets that do not already pin one",
    )
    parser.add_argument(
        "--validation-profile",
        action="append",
        default=[],
        help="Validation profile name to run. Repeat to run multiple profiles.",
    )
    parser.add_argument(
        "--benchmark-settings-profile",
        default="default",
        help="Named llama.cpp settings profile to apply to native runs.",
    )
    parser.add_argument(
        "--all-profiles",
        action="store_true",
        help="Run every configured validation profile instead of just the default profile.",
    )
    parser.add_argument(
        "--target",
        action="append",
        default=[],
        help="Optional target name filter from backend-validation config. Repeat to run multiple targets.",
    )
    parser.add_argument(
        "--mode",
        choices=("docker", "native", "all"),
        default="all",
        help="Limit the matrix to docker targets, native targets, or both.",
    )
    parser.add_argument(
        "--include-experimental",
        action="store_true",
        help="Include experimental validation targets such as TurboQuant.",
    )
    parser.add_argument(
        "--results-dir",
        default=str(Path("test-work/backend-validation-matrix").resolve()),
        help="Directory to write per-run benchmark JSON and the aggregate matrix summary.",
    )
    parser.add_argument(
        "--model-cache",
        default=str(Path("test-work/models").resolve()),
        help="Host model cache directory used by docker targets.",
    )
    parser.add_argument(
        "--native-root-base",
        default=str(Path("test-work/native-backend-validation-matrix").resolve()),
        help="Base workspace directory for native target runs.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resolved target matrix and commands without executing them.",
    )
    args = parser.parse_args()

    detection = detect_host_acceleration()
    platform_name = _normalize_platform_name()
    requested_targets = set(args.target) if args.target else None
    profiles = _selected_profiles(validation_catalog, args.validation_profile, all_profiles=args.all_profiles)
    results_dir = Path(args.results_dir).resolve()
    model_cache = Path(args.model_cache).resolve()
    native_root_base = Path(args.native_root_base).resolve()
    targets = resolve_validation_targets(
        REPO_ROOT,
        host_acceleration=detection.host_acceleration,
        host_capabilities=set(detection.supported_accelerations),
        platform_name=platform_name,
        validation_profile=profiles[0],
        include_experimental=args.include_experimental,
        requested_targets=requested_targets,
    )
    if args.mode != "all":
        targets = [target for target in targets if target.transport == args.mode]
    if not targets:
        raise SystemExit("No validation targets matched the current platform and filters.")

    print(f"Host acceleration: {detection.host_acceleration}")
    print(f"Container acceleration: {detection.container_acceleration}")
    if detection.gpu_name:
        print(f"Host GPU: {detection.gpu_name}")
    print(f"Platform: {platform_name}")
    print(f"Profiles: {', '.join(profiles)}")
    print(f"Benchmark settings profile: {args.benchmark_settings_profile}")
    print("Targets:")
    for target in targets:
        note = " experimental" if target.experimental else ""
        print(f"  - {target.name} [{target.transport}/{target.backend}]{note}")

    summary_rows: list[dict[str, Any]] = []
    completed_targets: set[str] = set()
    target_lookup = {target.name: target for target in targets}
    if args.dry_run:
        for profile_name in profiles:
            for target in targets:
                benchmark_output = _benchmark_file(results_dir, profile_name=profile_name, target_name=target.name)
                try:
                    command, env = _build_target_command(
                        target=target,
                        profile_name=profile_name,
                        benchmark_settings_profile=args.benchmark_settings_profile,
                        benchmark_output=benchmark_output,
                        image=args.image,
                        llama_version=target.llama_version or args.llama_version,
                        model_cache=model_cache,
                        native_root_base=native_root_base,
                    )
                except Exception as exc:
                    print(f"Skipping {profile_name}/{target.name}: {exc}")
                    continue
                print(f"{profile_name}/{target.name}: {subprocess.list2cmdline(command)}")
                if "AUDIA_LOCAL_VALIDATION_CONTAINER_ACCEL" in env:
                    print(f"  AUDIA_LOCAL_VALIDATION_CONTAINER_ACCEL={env['AUDIA_LOCAL_VALIDATION_CONTAINER_ACCEL']}")
        return 0

    results_dir.mkdir(parents=True, exist_ok=True)
    failures = 0
    for profile_name in profiles:
        for target in targets:
            rows, failed_count = _run_target_with_fallbacks(
                target=target,
                profile_name=profile_name,
                benchmark_settings_profile=args.benchmark_settings_profile,
                image=args.image,
                llama_version=args.llama_version,
                model_cache=model_cache,
                native_root_base=native_root_base,
                target_lookup=target_lookup,
                completed_targets=completed_targets,
                results_dir=results_dir,
            )
            summary_rows.extend(rows)
            failures += failed_count

    summary = {
        "generated_at_utc": subprocess.check_output(
            [_preferred_workspace_python(), "-c", "import time; print(time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))"],
            text=True,
        ).strip(),
        "platform": platform_name,
        "host_acceleration": detection.host_acceleration,
        "container_acceleration": detection.container_acceleration,
        "host_gpu_name": detection.gpu_name,
        "profiles": profiles,
        "benchmark_settings_profile": args.benchmark_settings_profile,
        "results": summary_rows,
    }
    summary_path = results_dir / "matrix-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nMatrix summary: {summary_path}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
