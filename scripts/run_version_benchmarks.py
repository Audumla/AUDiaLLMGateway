from __future__ import annotations

import argparse
import functools
import json
import os
import platform
import re
import subprocess
import sys
import time
import urllib.request
import statistics
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.launcher.local_backend_validation import (
    detect_host_acceleration,
    load_validation_catalog,
    validation_profile_native_models,
)
from src.launcher.config_loader import load_model_catalog, load_stack_config


def get_latest_github_releases(owner: str, repo: str, limit: int = 5) -> list[str]:
    url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    request = urllib.request.Request(url, headers={"User-Agent": "AUDiaLLMGateway-Benchmark"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    tags = [str(item["tag_name"]) for item in data if not item.get("prerelease") and not item.get("draft")]
    return tags[:limit]


def get_repo_head(owner: str, repo: str, branch: str) -> str:
    url = f"https://api.github.com/repos/{owner}/{repo}/commits/{branch}"
    request = urllib.request.Request(url, headers={"User-Agent": "AUDiaLLMGateway-Benchmark"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    return str(data["sha"])


def _preferred_workspace_python() -> str:
    candidates = [
        REPO_ROOT / ".venv" / "Scripts" / "python.exe",
        REPO_ROOT / ".venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def _timestamp_slug() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def _version_slug(version: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in version)


def _version_label(version_ref: str, track: str) -> str:
    ref = str(version_ref or "").strip()
    track_name = str(track or "").strip().lower()
    if not ref:
        return "unknown"
    if track_name == "latest-release":
        return ref
    if track_name == "latest-head":
        return f"master@{ref[:7]}" if len(ref) >= 7 else f"master@{ref}"
    if len(ref) > 12 and all(ch in "0123456789abcdef" for ch in ref.lower()):
        return ref[:7]
    return ref


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _format_metric(value: Any, suffix: str = "") -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.2f}{suffix}"
    return "FAILED" if value is None else str(value)


def _markdown_cell(value: Any) -> str:
    return str(value).replace("|", r"\|")


@functools.lru_cache(maxsize=1)
def _validation_target_catalog() -> dict[str, dict[str, Any]]:
    _, _, catalog = load_validation_catalog(REPO_ROOT)
    targets = catalog.get("targets", {})
    if not isinstance(targets, dict):
        return {}
    return {
        str(name).strip(): value
        for name, value in targets.items()
        if str(name).strip() and isinstance(value, dict)
    }


@functools.lru_cache(maxsize=1)
def _llama_cpp_profiles() -> dict[str, dict[str, Any]]:
    stack = load_stack_config(REPO_ROOT)
    settings = stack.component_settings.get("llama_cpp", {})
    if not isinstance(settings, dict):
        return {}
    profiles = settings.get("profiles", {})
    if not isinstance(profiles, dict):
        return {}
    return {
        str(name).strip(): value
        for name, value in profiles.items()
        if str(name).strip() and isinstance(value, dict)
    }


@functools.lru_cache(maxsize=1)
def _llama_cpp_settings() -> dict[str, Any]:
    stack = load_stack_config(REPO_ROOT)
    settings = stack.component_settings.get("llama_cpp", {})
    return settings if isinstance(settings, dict) else {}


def _repo_slug_from_url(url: str) -> str:
    text = str(url or "").strip().rstrip("/")
    if not text:
        return ""
    if text.endswith(".git"):
        text = text[:-4]
    if "github.com/" in text:
        return text.split("github.com/", 1)[1].strip("/")
    return ""


def _source_family_from_slug(slug: str, download_url: str = "") -> str:
    normalized = slug.strip().lower()
    download = str(download_url or "").lower()
    if normalized.startswith("ggml-org/"):
        return "ggml-org"
    if normalized.startswith("lemonade-sdk/"):
        return "Lemonade"
    if normalized.startswith("thetom/"):
        return "TheTom"
    if normalized.startswith("domvox/"):
        return "domvox"
    if normalized.startswith("unixsysdev/"):
        return "unixsysdev"
    if normalized.startswith("carlosfundora/"):
        return "carlosfundora"
    if normalized.startswith("ikawrakow/"):
        return "ikawrakow"
    if normalized.startswith("sirmo/"):
        return "sirmo"
    if "repo.radeon.com/rocm/llama.cpp" in download:
        return "AMD validated"
    return "Custom"


def _extract_toolchain_hint(*, profile: dict[str, Any], download_url: str, version: str) -> str:
    candidates = [
        str(download_url or ""),
        str(version or ""),
        str(profile.get("download_url") or ""),
    ]
    for candidate in candidates:
        match = re.search(r"rocm(?:-rel-)?[-_]?(\d+\.\d+(?:\.\d+)?)", candidate, re.IGNORECASE)
        if match:
            return f"ROCm {match.group(1)}"
        match = re.search(r"vulkan[-_ ]sdk[-_ ]?(\d+\.\d+(?:\.\d+)?)", candidate, re.IGNORECASE)
        if match:
            return f"Vulkan SDK {match.group(1)}"
    required = profile.get("required_toolchains", [])
    if isinstance(required, list):
        if "rocm_sdk" in required:
            return "ROCm SDK"
        if "vulkan_sdk" in required:
            return "Vulkan SDK"
    return ""


def _short_commit(value: str) -> str:
    text = str(value or "").strip()
    if len(text) >= 7:
        return text[:7]
    return text


def _compact_executable_label(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    path = Path(text)
    name = path.name
    if not name:
        return text
    parent = path.parent.name
    if parent and parent.lower() not in {"bin", "lib", "release", "debug"}:
        return f"{parent}/{name}"
    grandparent = path.parent.parent.name if path.parent.parent else ""
    if grandparent:
        return f"{grandparent}/{name}"
    return name


def _compact_model_label(target_context: dict[str, Any], fallback: str = "") -> str:
    source_page = str(target_context.get("source_page_url") or "").strip()
    model_filename = str(target_context.get("model_filename") or "").strip()
    backend_model_name = str(target_context.get("backend_model_name") or "").strip()
    model_display_name = str(target_context.get("model_display_name") or "").strip()
    alias_candidates = [
        str(target_context.get("native_model") or "").strip(),
        backend_model_name,
        str(target_context.get("llama_swap_model") or "").strip(),
    ]
    source_repo = ""
    if "huggingface.co/" in source_page:
        source_repo = (
            source_page.split("huggingface.co/", 1)[1]
            .strip("/")
            .replace("/tree/main", "")
            .replace("/blob/main", "")
        )
    if not source_repo:
        alias = next((item for item in alias_candidates if item), "")
        if alias:
            resolved = _model_profile_for_label(REPO_ROOT, alias)
            if resolved is not None:
                _, _, profile, deployment = resolved
                artifacts = profile.get("artifacts", {}) if isinstance(profile.get("artifacts"), dict) else {}
                source_page = str(deployment.get("source_page_url") or artifacts.get("source_page_url") or "").strip()
                model_filename = model_filename or str(deployment.get("model_filename") or artifacts.get("model_filename") or "").strip()
                if "huggingface.co/" in source_page:
                    source_repo = (
                        source_page.split("huggingface.co/", 1)[1]
                        .strip("/")
                        .replace("/tree/main", "")
                        .replace("/blob/main", "")
                    )
    if source_repo and model_filename:
        return f"{source_repo} / {model_filename}"
    if model_display_name:
        return model_display_name
    if source_repo:
        return source_repo
    if model_filename:
        return model_filename
    if backend_model_name:
        return backend_model_name
    return str(fallback or "").strip()


def _model_profile_for_label(root: Path, model_label: str) -> tuple[str, str, dict[str, Any], dict[str, Any]] | None:
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


def _profile_identity(
    *,
    target_name: str,
    target_context: dict[str, Any] | None = None,
    installation_context: dict[str, Any] | None = None,
) -> dict[str, str]:
    target_context = target_context if isinstance(target_context, dict) else {}
    installation_context = installation_context if isinstance(installation_context, dict) else {}
    target_catalog = _validation_target_catalog().get(target_name, {})
    profile_name = str(
        target_context.get("native_llama_cpp_profile")
        or installation_context.get("llama_cpp_profile")
        or ""
    ).strip()
    profile = _llama_cpp_profiles().get(profile_name, {})
    settings = _llama_cpp_settings()
    source_type = str(profile.get("source_type") or "").strip().lower()
    backend = str(
        installation_context.get("llama_cpp_backend")
        or target_context.get("native_backend")
        or profile.get("backend")
        or target_catalog.get("backend")
        or ""
    ).strip()
    version = str(
        installation_context.get("llama_cpp_version")
        or target_context.get("llama_version")
        or profile.get("version")
        or ""
    ).strip()
    git_url = str(profile.get("git_url") or "").strip()
    download_url = str(profile.get("download_url") or "").strip()
    owner = str(profile.get("repo_owner") or settings.get("repo_owner") or "").strip()
    repo = str(profile.get("repo_name") or settings.get("repo_name") or "").strip()
    slug = _repo_slug_from_url(git_url)
    if not slug and owner and repo:
        slug = f"{owner}/{repo}"
    if not source_type:
        if git_url:
            source_type = "git"
        elif download_url:
            source_type = "direct_url"
        elif slug:
            source_type = "github_release"
    lane_family = _source_family_from_slug(slug, download_url)

    exact_ref = version
    repo_or_artifact = slug or Path(download_url).name
    source_label = source_type or str(target_catalog.get("transport") or "")
    resolved_commit = ""
    if source_type == "git":
        branch = str(profile.get("branch") or profile.get("git_ref") or profile.get("ref") or "").strip()
        git_commit = str(profile.get("git_commit") or version).strip()
        resolved_commit = git_commit
        if branch:
            exact_ref = f"{slug} @ {branch}" if slug else branch
        else:
            exact_ref = f"{slug} @ {_short_commit(git_commit)}" if slug else _short_commit(git_commit)
        source_label = "git"
    elif source_type == "github_release":
        exact_ref = f"{slug} @ {version}" if slug and version else (version or slug)
        source_label = "github_release"
    elif source_type == "direct_url":
        artifact = Path(download_url).name if download_url else version
        repo_or_artifact = artifact
        exact_ref = artifact
        source_label = "direct_url"
    elif source_type == "docker_image":
        image = str(target_catalog.get("docker_image") or profile.get("docker_image") or "").strip()
        repo_or_artifact = image
        exact_ref = image
        source_label = "docker_image"

    return {
        "lane_family": lane_family,
        "lane_source": source_label,
        "repo_or_artifact": repo_or_artifact,
        "exact_ref": exact_ref,
        "resolved_commit": resolved_commit,
        "build_profile": profile_name,
        "backend": backend,
        "version": version,
        "toolchain_hint": _extract_toolchain_hint(profile=profile, download_url=download_url, version=version),
        "executable_path_or_package": _compact_executable_label(
            str(
                installation_context.get("llama_cpp_executable_path")
                or installation_context.get("llama_cpp_install_dir")
                or Path(download_url).name
                or repo_or_artifact
                or ""
            ).strip()
        ),
    }


def _host_label_from_context(
    benchmark_context: dict[str, Any] | None,
    target_backend: str | None = None,
) -> str:
    if not isinstance(benchmark_context, dict):
        return "Unknown host"
    host = benchmark_context.get("host", {})
    if not isinstance(host, dict):
        return "Unknown host"
    gpu_name = str(host.get("gpu_name") or "").strip()
    platform_name = str(host.get("platform") or "").strip()
    host_acceleration = str(host.get("host_acceleration") or "").strip().upper()
    target_backend_name = str(target_backend or "").strip().lower()
    if target_backend_name == "cpu":
        processor = str(host.get("processor") or "").strip().lower()
        if "intel" in processor:
            return "Intel CPU"
        if "amd" in processor:
            return "AMD CPU"
        return "CPU"
    if gpu_name:
        return gpu_name
    if host_acceleration == "ROCM":
        return "AMD GPU"
    if host_acceleration == "CUDA":
        return "NVIDIA GPU"
    if host_acceleration == "VULKAN":
        return "Vulkan GPU"
    if host_acceleration == "CPU":
        processor = str(host.get("processor") or "").strip()
        if "intel" in processor.lower():
            return "Intel CPU"
        if "amd" in processor.lower():
            return "AMD CPU"
        return "CPU"
    if platform_name and host_acceleration:
        return f"{platform_name} {host_acceleration}"
    if platform_name:
        return platform_name
    if host_acceleration:
        return host_acceleration
    return "Unknown host"


def _stack_label(latest: dict[str, Any]) -> str:
    benchmark_context = latest.get("benchmark_context", {})
    if not isinstance(benchmark_context, dict):
        benchmark_context = {}
    target = benchmark_context.get("target", {})
    if not isinstance(target, dict):
        target = {}
    installation = benchmark_context.get("installation", {})
    if not isinstance(installation, dict):
        installation = {}
    target_name = str(latest.get("target_name") or latest.get("target", ""))
    identity = _profile_identity(target_name=target_name, target_context=target, installation_context=installation)
    parts = [identity.get("build_profile", "")]
    if identity.get("version") or identity.get("backend"):
        parts.append("/".join(part for part in (identity.get("version", ""), identity.get("backend", "")) if part))
    return " | ".join(parts)


def _build_label(
    *,
    target_name: str,
    target_context: dict[str, Any] | None = None,
    installation_context: dict[str, Any] | None = None,
) -> str:
    target_context = target_context if isinstance(target_context, dict) else {}
    installation_context = installation_context if isinstance(installation_context, dict) else {}
    identity = _profile_identity(target_name=target_name, target_context=target_context, installation_context=installation_context)
    parts = [
        part
        for part in (
            identity.get("lane_family", ""),
            identity.get("repo_or_artifact", ""),
            identity.get("exact_ref", ""),
            identity.get("build_profile", ""),
            "/".join(part for part in (identity.get("version", ""), identity.get("backend", "")) if part),
            identity.get("toolchain_hint", ""),
        )
        if part
    ]
    return " | ".join(parts) if parts else "Unknown build"


def _load_route_details(benchmark_output: Any) -> list[dict[str, Any]]:
    if not benchmark_output:
        return []
    benchmark_path = Path(str(benchmark_output))
    if not benchmark_path.exists():
        return []

    benchmark = _load_json(benchmark_path, {})
    rows = benchmark.get("results", []) if isinstance(benchmark, dict) else []
    benchmark_context = benchmark.get("benchmark_context", {}) if isinstance(benchmark, dict) else {}
    target_details = []
    if isinstance(benchmark_context, dict):
        targets = benchmark_context.get("targets", [])
        if isinstance(targets, list):
            target_details = [item for item in targets if isinstance(item, dict)]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        route = str(row.get("route", "unknown"))
        grouped.setdefault(route, []).append(row)

    details: list[dict[str, Any]] = []
    target_context = benchmark_context.get("target", {}) if isinstance(benchmark_context, dict) else {}
    installation_context = benchmark_context.get("installation", {}) if isinstance(benchmark_context, dict) else {}
    if not isinstance(target_context, dict):
        target_context = {}
    if not isinstance(installation_context, dict):
        installation_context = {}
    native_profile = str(target_context.get("native_llama_cpp_profile") or installation_context.get("llama_cpp_profile") or "").strip()
    version = str(installation_context.get("llama_cpp_version") or target_context.get("llama_version") or "").strip()
    backend = str(installation_context.get("llama_cpp_backend") or target_context.get("native_backend") or "").strip()
    stack_parts = [part for part in (native_profile, "/".join(part for part in (version, backend) if part)) if part]
    stack_label = " | ".join(stack_parts) if stack_parts else "Unknown stack"
    target_backend = str(target_context.get("native_backend") or "").strip() or None
    host_label = _host_label_from_context(benchmark_context if isinstance(benchmark_context, dict) else {}, target_backend)
    identity = _profile_identity(target_name=str(target_context.get("validation_target_name") or ""), target_context=target_context, installation_context=installation_context)
    backend_device_selection = None
    backend_device_family = None
    settings_profile = None
    experimental = None
    if target_details:
        device_selection = target_details[0].get("backend_device_selection")
        if isinstance(device_selection, dict):
            backend_device_selection = device_selection
            backend_device_family = device_selection.get("family")
        settings_profile = target_details[0].get("benchmark_settings_profile")
        experimental = target_details[0].get("experimental")

    for route, sample_rows in grouped.items():
        passed_rows = [row for row in sample_rows if isinstance(row.get("tok_per_sec"), (int, float))]
        summary = _route_sample_summary(sample_rows)
        models = sorted({str(row.get("model", "")) for row in sample_rows if row.get("model")})
        observed_models = sorted({str(row.get("observed_model", "")) for row in sample_rows if row.get("observed_model")})
        target_name = str(sample_rows[0].get("target", "")) if sample_rows else ""
        details.append(
            {
                "route": route,
                "model": ", ".join(models) if models else "",
                "observed_model": ", ".join(observed_models) if observed_models else "",
                "status": "passed" if passed_rows else "failed",
                "client_avg_tok_per_sec": summary.get("client_avg_tok_per_sec"),
                "backend_avg_tok_per_sec": summary.get("backend_avg_tok_per_sec"),
                "round_trip_avg_seconds": summary.get("round_trip_avg_seconds"),
                "client_min_tok_per_sec": summary.get("client_min_tok_per_sec"),
                "client_max_tok_per_sec": summary.get("client_max_tok_per_sec"),
                "backend_min_tok_per_sec": summary.get("backend_min_tok_per_sec"),
                "backend_max_tok_per_sec": summary.get("backend_max_tok_per_sec"),
                "sample_count": summary.get("sample_count", len(sample_rows)),
                "success_count": summary.get("success_count", len(passed_rows)),
                "base_url": sample_rows[0].get("base_url"),
                "benchmark_mode": "timed",
                "benchmark_output": str(benchmark_path),
                "benchmark_context": benchmark_context,
                "_target_context": target_context,
                "_installation_context": installation_context,
                "backend_device_family": backend_device_family,
                "backend_device_selection": backend_device_selection,
                "settings_profile": settings_profile,
                "experimental": experimental,
                "host_label": host_label,
                "stack_label": stack_label,
                "build_label": _build_label(
                    target_name=target_name,
                    target_context=target_context,
                    installation_context=installation_context,
                ),
                "target_backend": target_backend or identity.get("backend"),
                "lane_family": identity.get("lane_family"),
                "lane_source": identity.get("lane_source"),
                "repo_or_artifact": identity.get("repo_or_artifact"),
                "exact_ref": identity.get("exact_ref"),
                "build_profile": identity.get("build_profile"),
                "backend": identity.get("backend"),
                "toolchain_version": identity.get("toolchain_hint"),
                "executable_path_or_package": identity.get("executable_path_or_package"),
                "samples": sample_rows,
                "preload_status": "ok"
                if any(isinstance(row.get("preload"), dict) for row in sample_rows)
                else ("failed" if any(row.get("preload_error") for row in sample_rows) else "n/a"),
            }
        )
    return details


def _route_sample_summary(sample_rows: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [row for row in sample_rows if isinstance(row.get("tok_per_sec"), (int, float))]
    if not successful:
        return {
            "sample_count": len(sample_rows),
            "success_count": 0,
            "client_avg_tok_per_sec": None,
            "backend_avg_tok_per_sec": None,
            "round_trip_avg_seconds": None,
            "client_min_tok_per_sec": None,
            "client_max_tok_per_sec": None,
            "backend_min_tok_per_sec": None,
            "backend_max_tok_per_sec": None,
        }
    client_values = [float(row["tok_per_sec"]) for row in successful]
    backend_values = [float(row.get("backend_tok_per_sec", 0.0) or 0.0) for row in successful if isinstance(row.get("backend_tok_per_sec"), (int, float))]
    elapsed_values = [float(row["elapsed_seconds"]) for row in successful if isinstance(row.get("elapsed_seconds"), (int, float))]
    return {
        "sample_count": len(sample_rows),
        "success_count": len(successful),
        "client_avg_tok_per_sec": statistics.mean(client_values),
        "backend_avg_tok_per_sec": statistics.mean(backend_values) if backend_values else None,
        "round_trip_avg_seconds": statistics.mean(elapsed_values) if elapsed_values else None,
        "client_min_tok_per_sec": min(client_values),
        "client_max_tok_per_sec": max(client_values),
        "backend_min_tok_per_sec": min(backend_values) if backend_values else None,
        "backend_max_tok_per_sec": max(backend_values) if backend_values else None,
    }


def _validation_profile_details(profile_name: str) -> dict[str, Any]:
    _, _, catalog = load_validation_catalog(REPO_ROOT)
    profiles = catalog.get("profiles", {})
    if profile_name not in profiles:
        raise ValueError(f"Unknown validation profile: {profile_name}")
    profile = profiles[profile_name]
    docker = profile.get("docker", {}) if isinstance(profile, dict) else {}
    native_models = profile.get("native_models", {}) if isinstance(profile, dict) else {}
    return {
        "profile": profile_name,
        "description": profile.get("description", "") if isinstance(profile, dict) else "",
        "docker_model_name": docker.get("model_name", ""),
        "docker_model_url": docker.get("model_url", ""),
        "native_models": native_models,
    }


def resolve_versions(args: argparse.Namespace) -> list[dict[str, str]]:
    if args.versions:
        requested = [item.strip() for item in args.versions.split(",") if item.strip()]
        resolved: list[dict[str, str]] = []
        for item in requested:
            if item == "latest-release":
                latest = get_latest_github_releases("ggml-org", "llama.cpp", limit=1)
                if latest:
                    resolved.append({"track": "latest-release", "ref": latest[0]})
            elif item in {"master", "latest-head"}:
                resolved.append({"track": "latest-head", "ref": get_repo_head("ggml-org", "llama.cpp", "master")})
            else:
                resolved.append({"track": "pinned", "ref": item})
        return resolved

    versions: list[dict[str, str]] = []
    if args.include_head:
        versions.append({"track": "latest-head", "ref": get_repo_head("ggml-org", "llama.cpp", "master")})
    for tag in get_latest_github_releases("ggml-org", "llama.cpp", limit=args.limit):
        versions.append({"track": "latest-release", "ref": tag})
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for item in versions:
        if item["ref"] in seen:
            continue
        seen.add(item["ref"])
        unique.append(item)
    return unique


def run_matrix_for_version(
    *,
    version_ref: str,
    track: str,
    accel: str,
    mode: str,
    results_root: Path,
    validation_profile: str,
    benchmark_settings_profile: str,
    include_experimental: bool,
    dry_run: bool,
) -> tuple[dict[str, Any], Path]:
    version_dir = results_root / _version_slug(version_ref) / accel / _version_slug(benchmark_settings_profile)
    command = [
        _preferred_workspace_python(),
        str(REPO_ROOT / "scripts" / "run_backend_validation_matrix.py"),
        "--mode",
        mode,
        "--llama-version",
        version_ref,
        "--results-dir",
        str(version_dir),
        "--validation-profile",
        validation_profile,
        "--benchmark-settings-profile",
        benchmark_settings_profile,
    ]
    if include_experimental:
        command.append("--include-experimental")
    if dry_run:
        command.append("--dry-run")

    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    env["AUDIA_LOCAL_VALIDATION_ACCEL"] = accel

    completed = subprocess.run(command, env=env, check=False, capture_output=False)
    summary_path = version_dir / "matrix-summary.json"
    summary = _load_json(summary_path, {})
    return {
        "returncode": completed.returncode,
        "command": command,
        "summary_path": str(summary_path),
        "summary": summary,
        "version_ref": version_ref,
        "track": track,
        "acceleration": accel,
        "settings_profile": benchmark_settings_profile,
        "mode": mode,
    }, version_dir


def _result_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = summary.get("results", [])
    return rows if isinstance(rows, list) else []


def _combination_key(*, version_ref: str, validation_profile: str, acceleration: str, settings_profile: str, target: str) -> str:
    return f"{version_ref}|{validation_profile}|{acceleration}|{settings_profile}|{target}"


def update_history(
    *,
    catalog: dict[str, Any],
    run_record: dict[str, Any],
    validation_profile: str,
) -> None:
    catalog.setdefault("schema_version", 2)
    catalog.setdefault("runs", [])
    catalog.setdefault("combinations", {})
    catalog["runs"].append(run_record)

    summary = run_record.get("summary", {})
    version_ref = str(run_record["version_ref"])
    acceleration = str(run_record["acceleration"])
    settings_profile = str(run_record.get("settings_profile", "default"))
    for result in _result_rows(summary):
        target = str(result.get("target", "unknown"))
        benchmark = result.get("benchmark", {}) if isinstance(result.get("benchmark"), dict) else {}
        key = _combination_key(
            version_ref=version_ref,
            validation_profile=validation_profile,
            acceleration=acceleration,
            settings_profile=settings_profile,
            target=target,
        )
        history = catalog["combinations"].setdefault(key, {"history": []})
        previous_entries = history.get("history", [])
        if not isinstance(previous_entries, list):
            previous_entries = []
        prior_statuses = [
            str(item.get("status", "")).strip().lower()
            for item in previous_entries
            if isinstance(item, dict) and str(item.get("status", "")).strip()
        ]
        ever_passed_before = any(status == "passed" for status in prior_statuses)
        latest_previous_status = prior_statuses[-1] if prior_statuses else ""
        status = str(result.get("status", "failed"))
        regression_detected = ever_passed_before and status != "passed"
        entry = {
            "version_ref": version_ref,
            "validation_profile": validation_profile,
            "acceleration": acceleration,
            "settings_profile": settings_profile,
            "target": target,
            "experimental": result.get("experimental"),
            "status": status,
            "returncode": result.get("returncode"),
            "benchmark_output": result.get("benchmark_output"),
            "top_tok_per_sec": benchmark.get("top_tok_per_sec"),
            "backend_top_tok_per_sec": benchmark.get("backend_top_tok_per_sec"),
            "benchmark_context": benchmark.get("benchmark_context", {}),
            "success_count": benchmark.get("success_count"),
            "run_id": run_record["run_id"],
            "updated_at_utc": run_record["started_at_utc"],
            "track": run_record.get("track", "pinned"),
            "previous_status": latest_previous_status or None,
            "ever_passed_before": ever_passed_before,
            "regression_detected": regression_detected,
        }
        history["latest"] = entry
        history["history"].append(entry)


def _collect_regressions(catalog: dict[str, Any], *, validation_profile: str) -> list[dict[str, Any]]:
    combos = catalog.get("combinations", {})
    if not isinstance(combos, dict):
        return []

    regressions: list[dict[str, Any]] = []
    for key, payload in combos.items():
        latest = payload.get("latest", {}) if isinstance(payload, dict) else {}
        if not isinstance(latest, dict):
            continue
        if latest.get("validation_profile") != validation_profile:
            continue
        if not latest.get("regression_detected"):
            continue
        regressions.append(
            {
                "key": key,
                "version_ref": latest.get("version_ref"),
                "acceleration": latest.get("acceleration"),
                "settings_profile": latest.get("settings_profile", "default"),
                "target": latest.get("target"),
                "status": latest.get("status"),
                "previous_status": latest.get("previous_status"),
                "run_id": latest.get("run_id"),
                "benchmark_output": latest.get("benchmark_output"),
            }
        )
    regressions.sort(
        key=lambda item: (
            str(item.get("version_ref", "")),
            str(item.get("acceleration", "")),
            str(item.get("settings_profile", "")),
            str(item.get("target", "")),
        )
    )
    return regressions


def normalize_history_regressions(catalog: dict[str, Any]) -> None:
    combos = catalog.get("combinations", {})
    if not isinstance(combos, dict):
        return
    for payload in combos.values():
        if not isinstance(payload, dict):
            continue
        history = payload.get("history", [])
        if not isinstance(history, list):
            continue
        seen_pass = False
        previous_status = ""
        for entry in history:
            if not isinstance(entry, dict):
                continue
            status = str(entry.get("status", "")).strip().lower()
            entry["previous_status"] = previous_status or None
            entry["ever_passed_before"] = seen_pass
            entry["regression_detected"] = bool(seen_pass and status != "passed")
            if status == "passed":
                seen_pass = True
            if status:
                previous_status = status
        if history:
            payload["latest"] = history[-1]


def _expected_native_model_label(*, validation_profile: str, acceleration: str, target: str | None = None) -> str | None:
    profile_labels = validation_profile_native_models(REPO_ROOT, validation_profile)
    if not profile_labels:
        return None
    lowered_target = (target or "").strip().lower()
    if lowered_target:
        if "vulkan" in lowered_target:
            return profile_labels.get("vulkan")
        if "rocm" in lowered_target or "hip" in lowered_target:
            return profile_labels.get("rocm")
        if "cpu" in lowered_target:
            return profile_labels.get("cpu")
    return profile_labels.get(acceleration)


def _collect_anomalies(catalog: dict[str, Any], *, validation_profile: str) -> list[str]:
    combos = catalog.get("combinations", {})
    if not isinstance(combos, dict):
        return []

    anomalies: list[str] = []
    for payload in combos.values():
        latest = payload.get("latest", {}) if isinstance(payload, dict) else {}
        if latest.get("validation_profile") != validation_profile:
            continue
        if latest.get("status") != "passed":
            continue
        benchmark_output = latest.get("benchmark_output")
        if not benchmark_output:
            continue
        benchmark_path = Path(str(benchmark_output))
        if not benchmark_path.exists():
            continue
        settings_profile = str(latest.get("settings_profile", "default"))

        try:
            benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
        except Exception:
            anomalies.append(
                f"{_version_label(str(latest.get('version_ref')), str(latest.get('track', '')))} / {latest.get('acceleration')} / {settings_profile} / {latest.get('target')}: "
                f"unable to read benchmark output at {benchmark_path}"
            )
            continue

        expected_model = _expected_native_model_label(
            validation_profile=validation_profile,
            acceleration=str(latest.get("acceleration", "")),
            target=str(latest.get("target", "")),
        )
        if expected_model:
            observed_models = sorted(
                {
                    str(row.get("model"))
                    for row in benchmark.get("results", [])
                    if isinstance(row, dict) and row.get("model")
                }
            )
            if observed_models and any(model != expected_model for model in observed_models):
                anomalies.append(
                    f"{_version_label(str(latest.get('version_ref')), str(latest.get('track', '')))} / {latest.get('acceleration')} / {settings_profile} / {latest.get('target')}: "
                    f"model mismatch, expected `{expected_model}` but observed {', '.join(f'`{m}`' for m in observed_models)}"
                )

        route_groups: dict[str, list[dict[str, Any]]] = {}
        for row in benchmark.get("results", []):
            if not isinstance(row, dict):
                continue
            route = str(row.get("route", "unknown"))
            route_groups.setdefault(route, []).append(row)
        route_summaries = [
            (route, _route_sample_summary(sample_rows))
            for route, sample_rows in route_groups.items()
            if any(isinstance(row.get("tok_per_sec"), (int, float)) for row in sample_rows)
        ]
        if len(route_summaries) < 2:
            continue
        speeds = [float(summary["client_avg_tok_per_sec"]) for _, summary in route_summaries if summary.get("client_avg_tok_per_sec") is not None]
        if len(speeds) < 2:
            continue
        low = min(speeds)
        high = max(speeds)
        if low <= 0 or high / low < 3.0:
            pass
        low_route = min(route_summaries, key=lambda item: float(item[1]["client_avg_tok_per_sec"] or 0.0))[0]
        high_route = max(route_summaries, key=lambda item: float(item[1]["client_avg_tok_per_sec"] or 0.0))[0]
        median = statistics.median(speeds)
        backend_speed = max(
            (float(summary.get("backend_avg_tok_per_sec", 0.0) or 0.0) for _, summary in route_summaries),
            default=0.0,
        )
        if low > 0 and high / low >= 3.0:
            anomalies.append(
                f"{_version_label(str(latest.get('version_ref')), str(latest.get('track', '')))} / {latest.get('acceleration')} / {settings_profile} / {latest.get('target')}: "
                f"{low_route} is {high / low:.2f}x slower than {high_route} "
                f"({low:.2f} vs {high:.2f} T/s, median {median:.2f}); investigate routing or startup overhead"
            )
        if backend_speed > 0 and low > 0 and backend_speed / low >= 3.0:
            anomalies.append(
                f"{_version_label(str(latest.get('version_ref')), str(latest.get('track', '')))} / {latest.get('acceleration')} / {settings_profile} / {latest.get('target')}: "
                f"backend reported {backend_speed:.2f} T/s but client saw only {low:.2f} T/s; "
                f"the slowdown is in gateway/transport, not the model backend"
            )

    return anomalies


def build_table_report(
    catalog: dict[str, Any],
    *,
    validation_profile: str,
    current_run_ids: set[str] | None = None,
    historic: bool = False,
) -> dict[str, Any]:
    combos = catalog.get("combinations", {})
    latest_rows: list[dict[str, Any]] = []
    rows_by_key: dict[str, dict[str, Any]] = {}
    route_details: list[dict[str, Any]] = []
    for payload in combos.values():
        latest = payload.get("latest", {})
        if latest.get("validation_profile") != validation_profile:
            continue
        is_current = current_run_ids is None or str(latest.get("run_id", "")) in current_run_ids
        if historic == is_current:
            continue
        latest_rows.append(latest)
        rows_by_key[_combination_key(
            version_ref=str(latest.get("version_ref", "")),
            validation_profile=validation_profile,
            acceleration=str(latest.get("acceleration", "")),
            settings_profile=str(latest.get("settings_profile", "default")),
            target=str(latest.get("target", "")),
        )] = latest

    versions = sorted({str(item["version_ref"]) for item in latest_rows}, reverse=True)
    version_tracks = {
        str(item["version_ref"]): str(item.get("track", ""))
        for item in latest_rows
        if str(item.get("version_ref", ""))
    }
    version_labels = {version: _version_label(version, version_tracks.get(version, "")) for version in versions}
    targets = sorted({str(item["target"]) for item in latest_rows})
    accels = sorted({str(item["acceleration"]) for item in latest_rows})
    settings_profiles = sorted({str(item.get("settings_profile", "default")) for item in latest_rows}, key=lambda value: (value != "default", value))

    rows: list[dict[str, Any]] = []
    for version in versions:
        for settings_profile in settings_profiles:
            for accel in accels:
                cells: dict[str, Any] = {}
                for target in targets:
                    latest = rows_by_key.get(
                        _combination_key(
                            version_ref=version,
                            validation_profile=validation_profile,
                            acceleration=accel,
                            settings_profile=settings_profile,
                            target=target,
                        )
                    )
                    if not latest:
                        cells[target] = {"display": "N/A", "status": "missing"}
                    else:
                        benchmark_context = latest.get("benchmark_context", {})
                        target_context = benchmark_context.get("target", {}) if isinstance(benchmark_context, dict) else {}
                        installation_context = benchmark_context.get("installation", {}) if isinstance(benchmark_context, dict) else {}
                        if not isinstance(target_context, dict):
                            target_context = {}
                        if not isinstance(installation_context, dict):
                            installation_context = {}
                        identity = _profile_identity(target_name=target, target_context=target_context, installation_context=installation_context)
                        target_backend = identity.get("backend") or str(target_context.get("native_backend") or "").strip() or None
                        host_label = _host_label_from_context(benchmark_context if isinstance(benchmark_context, dict) else {}, target_backend)
                        preload_status = "ok" if isinstance(latest.get("preload"), dict) else ("failed" if latest.get("preload_error") else "n/a")
                        latest_context_present = isinstance(benchmark_context, dict) and bool(benchmark_context)
                        if latest.get("status") == "passed" and latest.get("top_tok_per_sec") is not None:
                            client_avg = latest.get("client_avg_tok_per_sec", latest.get("top_tok_per_sec"))
                            backend_avg = latest.get("backend_avg_tok_per_sec", latest.get("backend_top_tok_per_sec"))
                            cells[target] = {
                                "display": f"{float(client_avg):.2f} T/s",
                                "status": "passed",
                                "top_tok_per_sec": client_avg,
                                "backend_top_tok_per_sec": backend_avg,
                                "client_avg_tok_per_sec": client_avg,
                                "backend_avg_tok_per_sec": backend_avg,
                                "benchmark_context": benchmark_context,
                                "benchmark_output": latest.get("benchmark_output"),
                                "host_label": host_label,
                                "stack_label": _stack_label(
                                    {
                                        "target": target_context,
                                        "installation": installation_context,
                                        "target_name": target,
                                    }
                                ),
                                "target_backend": target_backend,
                                "lane_family": identity.get("lane_family"),
                                "lane_source": identity.get("lane_source"),
                                "repo_or_artifact": identity.get("repo_or_artifact"),
                                "exact_ref": identity.get("exact_ref"),
                                "resolved_commit": identity.get("resolved_commit"),
                                "build_profile": identity.get("build_profile"),
                                "backend": identity.get("backend"),
                                "toolchain_version": identity.get("toolchain_hint"),
                                "executable_path_or_package": identity.get("executable_path_or_package"),
                                "preload_status": preload_status,
                                "regression_detected": bool(latest.get("regression_detected", False)),
                                "previous_status": latest.get("previous_status"),
                            }
                        else:
                            cells[target] = {
                                "display": "FAILED",
                                "status": latest.get("status", "failed"),
                                "benchmark_context": benchmark_context,
                                "benchmark_output": latest.get("benchmark_output"),
                                "host_label": host_label,
                                "stack_label": _stack_label(
                                    {
                                        "target": target_context,
                                        "installation": installation_context,
                                        "target_name": target,
                                    }
                                ),
                                "target_backend": target_backend,
                                "lane_family": identity.get("lane_family"),
                                "lane_source": identity.get("lane_source"),
                                "repo_or_artifact": identity.get("repo_or_artifact"),
                                "exact_ref": identity.get("exact_ref"),
                                "resolved_commit": identity.get("resolved_commit"),
                                "build_profile": identity.get("build_profile"),
                                "backend": identity.get("backend"),
                                "toolchain_version": identity.get("toolchain_hint"),
                                "executable_path_or_package": identity.get("executable_path_or_package"),
                                "preload_status": preload_status,
                                "regression_detected": bool(latest.get("regression_detected", False)),
                                "previous_status": latest.get("previous_status"),
                            }
                        for detail in _load_route_details(latest.get("benchmark_output")):
                            detail_target_context = detail.get("_target_context", {})
                            if not isinstance(detail_target_context, dict):
                                detail_target_context = target_context
                            detail_installation_context = detail.get("_installation_context", {})
                            if not isinstance(detail_installation_context, dict):
                                detail_installation_context = installation_context
                            detail["version"] = version
                            detail["version_label"] = version_labels.get(version, version)
                            detail["accel"] = accel
                            detail["settings_profile"] = settings_profile
                            detail["target"] = target
                            if not detail.get("benchmark_context"):
                                detail["benchmark_context"] = latest.get("benchmark_context", {})
                            detail_identity = _profile_identity(
                                target_name=target,
                                target_context=detail_target_context,
                                installation_context=detail_installation_context,
                            )
                            detail["lane_family"] = detail_identity.get("lane_family")
                            detail["lane_source"] = detail_identity.get("lane_source")
                            detail["repo_or_artifact"] = detail_identity.get("repo_or_artifact")
                            detail["exact_ref"] = detail_identity.get("exact_ref")
                            detail["resolved_commit"] = detail_identity.get("resolved_commit")
                            detail["build_profile"] = detail_identity.get("build_profile")
                            detail["backend"] = detail_identity.get("backend")
                            detail["toolchain_version"] = detail_identity.get("toolchain_hint")
                            detail["executable_path_or_package"] = detail_identity.get("executable_path_or_package")
                            detail["target_backend"] = detail_identity.get("backend") or detail.get("target_backend")
                            detail["experimental"] = bool(latest.get("experimental", False))
                            detail["requested_model"] = str(
                                _compact_model_label(detail_target_context)
                                or _expected_native_model_label(
                                    validation_profile=validation_profile,
                                    acceleration=accel,
                                    target=target,
                                )
                                or ""
                            ).strip()
                            detail["observed_model"] = str(detail.get("observed_model") or detail.get("model") or "")
                            if latest_context_present:
                                detail["host_label"] = host_label
                                detail["stack_label"] = _stack_label(
                                    {
                                        "target": detail_target_context,
                                        "installation": detail_installation_context,
                                        "target_name": target,
                                    }
                                )
                            detail["build_label"] = _build_label(
                                target_name=target,
                                target_context=detail_target_context,
                                installation_context=detail_installation_context,
                            )
                            route_details.append(detail)
                rows.append(
                    {
                        "version": version,
                        "version_label": version_labels.get(version, version),
                        "accel": accel,
                        "settings_profile": settings_profile,
                        "historic": historic,
                        "cells": cells,
                    }
                )

    return {
        "schema_version": 2,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "validation_profile": validation_profile,
        "historic": historic,
        "versions": versions,
        "version_labels": version_labels,
        "settings_profiles": settings_profiles,
        "accelerations": accels,
        "targets": targets,
        "rows": rows,
        "rows_by_key": rows_by_key,
        "route_details": route_details,
        "regressions": _collect_regressions(catalog, validation_profile=validation_profile),
        "suspicious_runs": _collect_anomalies(catalog, validation_profile=validation_profile),
    }


def build_markdown_report(
    catalog: dict[str, Any],
    *,
    validation_profile: str,
    current_run_ids: set[str] | None = None,
    historic: bool = False,
) -> str:
    report = build_table_report(
        catalog,
        validation_profile=validation_profile,
        current_run_ids=current_run_ids,
        historic=historic,
    )
    versions = report["versions"]
    version_labels = report.get("version_labels", {})
    targets = report["targets"]
    accels = report["accelerations"]
    settings_profiles = report.get("settings_profiles", [])
    scope_label = "historic" if historic else "current"

    lines = [
        f"# Version Benchmark Report ({validation_profile}, {scope_label})",
        "",
        f"Generated: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        "",
        f"Versions: {', '.join(version_labels.get(version, version) for version in versions) if versions else 'none'}",
        f"Settings: {', '.join(settings_profiles) if settings_profiles else 'none'}",
        f"Accelerations: {', '.join(accels) if accels else 'none'}",
        "Note: Acceleration is the sweep bucket; Route Metrics shows actual host hardware, lane family, and stack profile/version/backend.",
        "Note: Client Avg T/s is the mean end-to-end throughput across the request suite; Backend Avg T/s is the mean model-only throughput reported by llama.cpp timings.",
        "",
    ]

    header = "| Version | Accel | Settings | " + " | ".join(targets) + " |"
    separator = "|---|---|---|" + "|".join(["---" for _ in targets]) + "|"
    lines.extend([header, separator])

    for version in versions:
        for settings_profile in settings_profiles:
            for accel in accels:
                row = [version_labels.get(version, version), accel, settings_profile]
                for target in targets:
                    latest = report["rows_by_key"].get(
                        _combination_key(
                            version_ref=version,
                            validation_profile=validation_profile,
                            acceleration=accel,
                            settings_profile=settings_profile,
                            target=target,
                        )
                    )
                    if not latest:
                        row.append("N/A")
                    elif latest.get("status") == "passed" and latest.get("top_tok_per_sec") is not None:
                        row.append(f"{float(latest['top_tok_per_sec']):.2f} T/s")
                    else:
                        row.append("FAILED")
                lines.append("| " + " | ".join(row) + " |")

    anomalies = _collect_anomalies(catalog, validation_profile=validation_profile)
    regressions = report.get("regressions", [])
    if regressions:
        lines.extend(
            [
                "",
                "## Regression Candidates",
                "",
            ]
        )
        for item in regressions:
            lines.append(
                f"- {_version_label(str(item.get('version_ref')), str(item.get('track', '')))} / {item.get('acceleration')} / {item.get('settings_profile')} / {item.get('target')}: "
                f"regressed from `{item.get('previous_status')}` to `{item.get('status')}`; investigate and fix before accepting the run"
            )
    if anomalies:
        lines.extend(
            [
                "",
                "## Suspicious Runs",
                "",
            ]
        )
    lines.extend(f"- {item}" for item in anomalies)

    route_details = report.get("route_details", [])
    if route_details:
        lines.extend(
            [
                "",
                "## Route Metrics",
                "",
                "| Version | Host | Lane | Lane Source | Repo / Artifact | Exact Ref | Build Profile | Backend | Toolchain Version | Executable Path / Package | Experimental | Settings | Target | Route | Samples | Requested Model | Observed Model | Status | Backend Device | Client Avg T/s | Backend Avg T/s | Round-trip Avg s | Base URL |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
            ]
        )
        for row in route_details:
            device_selection = row.get("backend_device_selection") if isinstance(row, dict) else None
            backend_device = "N/A"
            if isinstance(device_selection, dict):
                devices = device_selection.get("devices")
                if isinstance(devices, list) and devices:
                    backend_device = ",".join(str(item) for item in devices)
                elif device_selection.get("raw"):
                    backend_device = str(device_selection.get("raw"))
            sample_count = row.get("sample_count")
            success_count = row.get("success_count")
            sample_label = f"{success_count}/{sample_count}" if isinstance(success_count, int) and isinstance(sample_count, int) else "n/a"
            lines.append(
                "| "
                + " | ".join(
                    [
                        _markdown_cell(row.get("version_label") or row.get("version", "")),
                        _markdown_cell(row.get("host_label") or row.get("accel", "")),
                        _markdown_cell(row.get("lane_family") or ""),
                        _markdown_cell(row.get("lane_source") or ""),
                        _markdown_cell(row.get("repo_or_artifact") or ""),
                        _markdown_cell(row.get("exact_ref") or ""),
                        _markdown_cell(row.get("build_profile") or ""),
                        _markdown_cell(row.get("backend") or row.get("target_backend") or ""),
                        _markdown_cell(row.get("toolchain_version") or ""),
                        _markdown_cell(row.get("executable_path_or_package") or ""),
                        _markdown_cell("yes" if row.get("experimental") else "no"),
                        _markdown_cell(row.get("settings_profile", "")),
                        _markdown_cell(row.get("target", "")),
                        _markdown_cell(row.get("route", "")),
                        _markdown_cell(sample_label),
                        _markdown_cell(row.get("requested_model") or ""),
                        _markdown_cell(row.get("observed_model") or row.get("model", "")),
                        _markdown_cell(row.get("status", "")),
                        backend_device,
                        _format_metric(row.get("client_avg_tok_per_sec"), " T/s") if row.get("client_avg_tok_per_sec") is not None else "N/A",
                        _format_metric(row.get("backend_avg_tok_per_sec"), " T/s") if row.get("backend_avg_tok_per_sec") is not None else "N/A",
                        _format_metric(row.get("round_trip_avg_seconds"), "s") if row.get("round_trip_avg_seconds") is not None else "N/A",
                        _markdown_cell(row.get("base_url", "")),
                    ]
                )
                + " |"
            )
    return "\n".join(lines)


def _json_table_report(report: dict[str, Any]) -> dict[str, Any]:
    exportable = dict(report)
    exportable.pop("rows_by_key", None)
    return exportable


def _persist_reports(
    *,
    results_root: Path,
    run_dir: Path,
    history_path: Path,
    catalog: dict[str, Any],
    validation_profile: str,
    run_manifest: dict[str, Any],
    current_run_ids: set[str],
) -> None:
    latest_report_table = build_table_report(
        catalog,
        validation_profile=validation_profile,
        current_run_ids=current_run_ids,
        historic=False,
    )
    historic_report_table = build_table_report(
        catalog,
        validation_profile=validation_profile,
        current_run_ids=current_run_ids,
        historic=True,
    )
    latest_report = build_markdown_report(
        catalog,
        validation_profile=validation_profile,
        current_run_ids=current_run_ids,
        historic=False,
    )
    historic_report = build_markdown_report(
        catalog,
        validation_profile=validation_profile,
        current_run_ids=current_run_ids,
        historic=True,
    )
    _write_json(history_path, catalog)
    _write_json(results_root / "benchmark_metrics.json", _json_table_report(latest_report_table))
    _write_json(results_root / "benchmark_metrics.historic.json", _json_table_report(historic_report_table))
    (results_root / "benchmark_metrics.md").write_text(latest_report, encoding="utf-8")
    (results_root / "benchmark_metrics.historic.md").write_text(historic_report, encoding="utf-8")
    _write_json(run_dir / "run_manifest.json", run_manifest)
    (run_dir / "report.md").write_text(latest_report, encoding="utf-8")
    (run_dir / "report.json").write_text(json.dumps(_json_table_report(latest_report_table), indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run reusable llama.cpp version benchmark matrix scans.")
    parser.add_argument("--limit", type=int, default=3, help="Number of recent release tags to include.")
    parser.add_argument("--versions", type=str, help="Comma-separated specific refs or aliases like latest-release,latest-head.")
    parser.add_argument(
        "--accels",
        type=str,
        default="auto",
        help="Comma-separated forced accelerations, or auto to use configured host capabilities.",
    )
    parser.add_argument("--mode", type=str, default="native", help="Validation mode to run (native, docker, all).")
    parser.add_argument("--validation-profile", default="quick", help="Validation profile to benchmark.")
    parser.add_argument("--include-head", action="store_true", help="Include the latest upstream master head.")
    parser.add_argument("--include-experimental", action="store_true", help="Include experimental targets.")
    parser.add_argument(
        "--settings-profiles",
        type=str,
        default="default,batch,batch_flash_off,large_context",
        help="Comma-separated benchmark settings profiles to sweep.",
    )
    parser.add_argument("--results-root", default=str(REPO_ROOT / "test-work" / "version-benchmarks"), help="Root directory for benchmark results.")
    parser.add_argument("--refresh-existing", action="store_true", help="Rerun combinations even if a latest result already exists.")
    parser.add_argument("--latest-only", action="store_true", help="Run only the most recent resolved ref.")
    parser.add_argument("--dry-run", action="store_true", help="Resolve versions and print actions without executing benchmark commands.")
    return parser.parse_args()


def _resolve_settings_profiles(validation_catalog: dict[str, Any], requested: str) -> list[str]:
    profiles = validation_catalog.get("benchmark_settings_profiles", {})
    if not isinstance(profiles, dict) or not profiles:
        return ["default"]
    requested_profiles = [item.strip() for item in requested.split(",") if item.strip()]
    if not requested_profiles:
        requested_profiles = [str(validation_catalog.get("defaults", {}).get("benchmark_settings_profile", "default"))]
    missing = [name for name in requested_profiles if name not in profiles]
    if missing:
        raise ValueError(f"Unknown benchmark settings profile(s): {', '.join(missing)}")
    return requested_profiles


def _resolve_accelerations(validation_catalog: dict[str, Any], requested: str, host_capabilities: set[str]) -> list[str]:
    requested_items = [item.strip().lower() for item in requested.split(",") if item.strip()]
    if requested_items and requested_items != ["auto"]:
        return requested_items

    benchmark_defaults = validation_catalog.get("defaults", {}).get("benchmark", {})
    if isinstance(benchmark_defaults, dict):
        configured = benchmark_defaults.get("accelerations", "auto")
        if isinstance(configured, str):
            configured_items = [item.strip().lower() for item in configured.split(",") if item.strip()]
            if configured_items and configured_items != ["auto"]:
                return configured_items

    resolved = [item for item in ["cpu", "cuda", "rocm", "vulkan"] if item in host_capabilities]
    return resolved or ["cpu"]


def main() -> int:
    args = parse_args()
    validation_details = _validation_profile_details(args.validation_profile)
    validation_catalog = load_validation_catalog(REPO_ROOT)[2]
    settings_profiles = _resolve_settings_profiles(validation_catalog, args.settings_profiles)
    detection = detect_host_acceleration()
    resolved_versions = resolve_versions(args)
    if args.latest_only and resolved_versions:
        resolved_versions = resolved_versions[:1]
    if not resolved_versions:
        print("No versions resolved for benchmarking.", file=sys.stderr)
        return 1

    accels = _resolve_accelerations(validation_catalog, args.accels, set(detection.supported_accelerations))
    results_root = Path(args.results_root).resolve()
    results_root.mkdir(parents=True, exist_ok=True)
    history_path = results_root / "benchmark_history.json"
    catalog = _load_json(history_path, {})
    run_id = _timestamp_slug()
    run_dir = results_root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    run_manifest = {
        "run_id": run_id,
        "started_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host_platform": platform.system(),
        "host_acceleration": detection.host_acceleration,
        "supported_accelerations": list(detection.supported_accelerations),
        "validation_profile": args.validation_profile,
        "validation_description": validation_details["description"],
        "settings_profiles": settings_profiles,
        "default_docker_model_name": validation_details["docker_model_name"],
        "default_native_models": validation_details["native_models"],
        "mode": args.mode,
        "include_experimental": args.include_experimental,
        "resolved_versions": resolved_versions,
        "accelerations": accels,
        "results": [],
    }

    for version in resolved_versions:
        for accel in accels:
            for settings_profile in settings_profiles:
                existing_key_prefix = f"{version['ref']}|{args.validation_profile}|{accel}|{settings_profile}|"
                already_present = any(str(key).startswith(existing_key_prefix) for key in catalog.get("combinations", {}))
                if already_present and not args.refresh_existing:
                    print(f"Skipping existing benchmark set for {version['ref']} [{accel}] ({settings_profile})")
                    continue
                print(
                    f"\nRunning {version['track']} {version['ref']} on {accel} with profile {args.validation_profile} "
                    f"and settings {settings_profile}"
                )
                result, _ = run_matrix_for_version(
                    version_ref=version["ref"],
                    track=version["track"],
                    accel=accel,
                    mode=args.mode,
                    results_root=results_root,
                    validation_profile=args.validation_profile,
                    benchmark_settings_profile=settings_profile,
                    include_experimental=args.include_experimental,
                    dry_run=args.dry_run,
                )
                result["run_id"] = run_id
                result["started_at_utc"] = run_manifest["started_at_utc"]
                run_manifest["results"].append(result)
                if not args.dry_run and result.get("summary"):
                    update_history(catalog=catalog, run_record=result, validation_profile=args.validation_profile)
                    _persist_reports(
                        results_root=results_root,
                        run_dir=run_dir,
                        history_path=history_path,
                        catalog=catalog,
                        validation_profile=args.validation_profile,
                        run_manifest=run_manifest,
                        current_run_ids={entry["run_id"] for entry in run_manifest["results"] if entry.get("run_id")},
                    )

    if not args.dry_run:
        current_run_ids = {entry["run_id"] for entry in run_manifest["results"] if entry.get("run_id")}
        report = build_markdown_report(
            catalog,
            validation_profile=args.validation_profile,
            current_run_ids=current_run_ids,
            historic=False,
        )
        _persist_reports(
            results_root=results_root,
            run_dir=run_dir,
            history_path=history_path,
            catalog=catalog,
            validation_profile=args.validation_profile,
            run_manifest=run_manifest,
            current_run_ids=current_run_ids,
        )
        print(report)
        print(f"\nRun manifest: {run_dir / 'run_manifest.json'}")
        print(f"History: {history_path}")
    else:
        print(json.dumps(run_manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
