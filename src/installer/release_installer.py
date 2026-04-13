from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any

def detect_platform() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    if system == "windows":
        return "windows"
    if system == "linux":
        return "linux"
    raise RuntimeError(f"Unsupported platform: {system}")


def load_manifest(root: str | Path) -> dict[str, Any]:
    path = Path(root).resolve() / "install" / "release-manifest.json"
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("install/release-manifest.json must contain an object")
    return data


def github_api_request(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    request_headers = {"Accept": "application/vnd.github+json"}
    if headers:
        request_headers.update(headers)
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request_headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def get_release_metadata(owner: str, repo: str, version: str) -> dict[str, Any]:
    if version == "latest":
        url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    else:
        url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{version}"
    return github_api_request(url)


def find_release_asset(metadata: dict[str, Any], required_tokens: list[str]) -> dict[str, Any]:
    tokens = [token.lower() for token in required_tokens]
    for asset in metadata.get("assets", []):
        name = str(asset.get("name", "")).lower()
        if all(token in name for token in tokens):
            return asset
    raise RuntimeError(f"No release asset matched tokens: {required_tokens}")


def release_summary(owner: str, repo: str, version: str = "latest") -> dict[str, Any]:
    metadata = get_release_metadata(owner, repo, version)
    return {
        "owner": owner,
        "repo": repo,
        "tag_name": str(metadata.get("tag_name", version)),
        "published_at": metadata.get("published_at"),
        "name": metadata.get("name"),
        "html_url": metadata.get("html_url"),
    }


def choose_archive_url(metadata: dict[str, Any], archive_kind: str) -> tuple[str, str]:
    if archive_kind == "zipball":
        return str(metadata["zipball_url"]), ".zip"
    if archive_kind == "tarball":
        return str(metadata["tarball_url"]), ".tar.gz"
    raise ValueError(f"Unsupported archive kind: {archive_kind}")


def download_file(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    token = os.environ.get("GITHUB_TOKEN")
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    return destination


def _unpack(archive_path: Path, destination: Path) -> None:
    """Extract archive to destination, using system tar on Unix to avoid Python gzip bugs."""
    if archive_path.suffix == ".zip":
        import zipfile
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(destination)
    elif os.name != "nt":
        subprocess.run(
            ["tar", "xf", str(archive_path.resolve()), "-C", str(destination.resolve())],
            check=True,
        )
    else:
        shutil.unpack_archive(str(archive_path), str(destination))


def extract_archive(archive_path: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    _unpack(archive_path, destination)
    children = [child for child in destination.iterdir() if child.is_dir()]
    if len(children) != 1:
        raise RuntimeError(f"Expected one top-level extracted directory in {destination}")
    return children[0]


def extract_component_archive(archive_path: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    _unpack(archive_path, destination)
    children = [child for child in destination.iterdir()]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return destination


def copy_tree(source: Path, destination: Path) -> None:
    if source.is_dir():
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def sync_release_tree(bundle_root: Path, install_root: Path, managed_paths: list[str], seed_paths: list[str]) -> None:
    install_root.mkdir(parents=True, exist_ok=True)
    for rel_path in managed_paths:
        source = bundle_root / rel_path
        if source.exists():
            copy_tree(source, install_root / rel_path)
    for rel_path in seed_paths:
        source = bundle_root / rel_path
        destination = install_root / rel_path
        if source.exists() and not destination.exists():
            copy_tree(source, destination)


def run_command(command: list[str], cwd: Path | None = None) -> None:
    subprocess.run(command, cwd=str(cwd) if cwd else None, check=True)


def run_shell_command(command: str, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        env=env,
        shell=True,
        check=True,
    )


def git_checkout_ref(
    git_executable: str,
    git_url: str,
    git_ref: str,
    destination: Path,
    git_commit: str | None = None,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    run_command([git_executable, "init", str(destination)])
    run_command([git_executable, "-C", str(destination), "remote", "add", "origin", git_url])
    run_command([git_executable, "-C", str(destination), "fetch", "--depth", "1", "origin", git_ref])
    checkout_target = git_commit.strip() if git_commit and git_commit.strip() else "FETCH_HEAD"
    run_command([git_executable, "-C", str(destination), "checkout", "--detach", checkout_target])


def _glob_matches(root: Path, patterns: str | list[str] | tuple[str, ...] | None) -> list[Path]:
    if patterns is None:
        return []
    if isinstance(patterns, str):
        pattern_list = [patterns]
    else:
        pattern_list = [str(item) for item in patterns]
    matches: list[Path] = []
    for pattern in pattern_list:
        if not pattern:
            continue
        matches.extend(path for path in root.glob(pattern) if path.exists())
    return matches


def _resolve_local_artifact_source(source_root: Path, relative_path: str) -> Path | None:
    """Resolve a local model artifact from a mounted file or directory tree."""
    if not relative_path:
        return None
    if source_root.is_file():
        return source_root
    if not source_root.exists():
        return None

    relative = Path(str(relative_path).replace("\\", "/"))
    candidates = [
        source_root / relative,
        source_root / relative.name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    if source_root.is_dir():
        matches = [path for path in source_root.rglob(relative.name) if path.is_file()]
        if matches:
            return matches[0]
    return None


def _copy_artifact_if_needed(source: Path, destination: Path) -> bool:
    """Copy a file when the destination is missing or older than the source."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        try:
            source_stat = source.stat()
            dest_stat = destination.stat()
            if dest_stat.st_size == source_stat.st_size and dest_stat.st_mtime_ns >= source_stat.st_mtime_ns:
                return False
        except OSError:
            pass
    shutil.copy2(source, destination)
    return True


def _install_state_path(root: Path) -> Path:
    return root / "state" / "install-state.json"


def _load_previous_llama_cpp_variant(root: Path, profile_name: str) -> dict[str, Any] | None:
    state_path = _install_state_path(root)
    if not state_path.exists():
        return None
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    component_results = state.get("component_results", {})
    if not isinstance(component_results, dict):
        return None
    llama_cpp = component_results.get("llama_cpp", {})
    if not isinstance(llama_cpp, dict):
        return None
    variants = llama_cpp.get("variants", {})
    if isinstance(variants, dict):
        cached = variants.get(profile_name)
        if isinstance(cached, dict):
            return cached
    if str(llama_cpp.get("profile", "")).strip() == profile_name:
        return llama_cpp
    return None


def _local_llama_cpp_install_result(
    *,
    install_dir: Path,
    executable_name: str,
    system: str,
    profile_name: str,
    source_type: str,
    backend: str,
    version: str,
    sidecar_files: list[str],
    copy_sidecar_to_binary_dir: bool,
) -> dict[str, Any] | None:
    if not install_dir.exists():
        return None
    executable_path = install_dir / "bin" / executable_name
    if not executable_path.exists():
        fallback = next(install_dir.rglob(executable_name), None)
        if fallback is None:
            return None
        executable_path = fallback

    copied_sidecars: list[str] = []
    if copy_sidecar_to_binary_dir and sidecar_files:
        for source_file in sidecar_files:
            source_path = Path(source_file)
            if source_path.exists():
                target_path = executable_path.parent / source_path.name
                if target_path.exists() or target_path.is_symlink():
                    copied_sidecars.append(str(target_path))
                else:
                    shutil.copy2(source_path, target_path)
                    copied_sidecars.append(str(target_path))

    result: dict[str, Any] = {
        "system": system,
        "provider": "github_release" if source_type == "github_release" else "direct_url",
        "source_type": source_type,
        "profile": profile_name,
        "version": version,
        "backend": backend,
        "install_dir": str(install_dir),
        "asset_name": "local-cache",
        "executable_path": str(executable_path),
        "copied_sidecars": copied_sidecars,
        "cache_hit": True,
    }
    if backend == "rocm":
        result["rocm_executable_path"] = str(executable_path)
    return result


def _llama_cpp_cache_signature(
    *,
    root: Path,
    profile_name: str,
    profile: dict[str, Any],
    system: str,
    source_type: str,
    version: str,
    backend: str,
) -> dict[str, Any]:
    toolchains = []
    for requirement in _profile_toolchain_requirements(profile):
        configured_root = os.environ.get("AUDIA_VULKAN_SDK_ROOT", "").strip() or str(profile.get("vulkan_sdk_root", "")).strip()
        if requirement == "rocm_sdk":
            configured_root = (
                os.environ.get("AUDIA_ROCM_SDK_ROOT", "").strip()
                or os.environ.get("ROCM_PATH", "").strip()
                or os.environ.get("HIP_PATH", "").strip()
                or str(profile.get("rocm_sdk_root", "")).strip()
            )
        if configured_root:
            root_path = Path(configured_root)
            if not root_path.is_absolute():
                root_path = root / root_path
            configured_root = str(root_path)
        toolchains.append({"kind": requirement, "root": configured_root})

    return {
        "system": system,
        "profile": profile_name,
        "source_type": source_type,
        "version": version,
        "backend": backend,
        "git_url": str(profile.get("git_url", "")).strip(),
        "git_ref": str(profile.get("git_ref", version)).strip() or version,
        "git_commit": str(profile.get("git_commit", "")).strip() or None,
        "download_url": str(profile.get("download_url", "")).strip(),
        "configure_command": str(profile.get("configure_command", "")).strip(),
        "build_command": str(profile.get("build_command", "")).strip(),
        "required_toolchains": _profile_toolchain_requirements(profile),
        "toolchains": toolchains,
    }


def _llama_cpp_cache_matches(cached: dict[str, Any] | None, signature: dict[str, Any]) -> bool:
    if not isinstance(cached, dict):
        return False
    keys = (
        "system",
        "profile",
        "source_type",
        "backend",
        "git_url",
        "git_ref",
        "git_commit",
        "download_url",
        "configure_command",
        "build_command",
        "required_toolchains",
        "toolchains",
    )
    for key in keys:
        if cached.get(key) != signature.get(key):
            return False
    if signature["source_type"] == "git":
        return cached.get("version") == signature.get("version")
    if signature["source_type"] in {"github_release", "direct_url"}:
        return cached.get("version") == signature.get("version")
    return cached.get("version") == signature.get("version")


def _vulkan_sdk_layout(system: str) -> dict[str, str]:
    if system == "windows":
        return {
            "include_dir": "Include",
            "library_path": "Lib/vulkan-1.lib",
            "glslc_path": "Bin/glslc.exe",
            "bin_dir": "Bin",
        }
    return {
        "include_dir": "include",
        "library_path": "lib/libvulkan.so",
        "glslc_path": "bin/glslc",
        "bin_dir": "bin",
    }


def describe_vulkan_sdk(sdk_root: Path, system: str) -> dict[str, Any]:
    layout = _vulkan_sdk_layout(system)
    include_dir = sdk_root / layout["include_dir"]
    library_path = sdk_root / layout["library_path"]
    glslc_path = sdk_root / layout["glslc_path"]
    bin_dir = sdk_root / layout["bin_dir"]
    return {
        "sdk_root": sdk_root,
        "include_dir": include_dir,
        "library_path": library_path,
        "glslc_path": glslc_path,
        "bin_dir": bin_dir,
        "valid": (include_dir / "vulkan" / "vulkan.h").exists() and library_path.exists() and glslc_path.exists(),
    }


def copy_vulkan_sdk_subset(source_root: Path, target_root: Path, system: str) -> dict[str, Any]:
    layout = _vulkan_sdk_layout(system)
    source = describe_vulkan_sdk(source_root, system)
    if not source["valid"]:
        raise RuntimeError(f"Source Vulkan SDK is incomplete: {source_root}")
    for rel_path in {layout["include_dir"], Path(layout["library_path"]).parts[0], layout["bin_dir"]}:
        source_path = source_root / rel_path
        target_path = target_root / rel_path
        if target_path.exists():
            shutil.rmtree(target_path)
        shutil.copytree(source_path, target_path)
    copied = describe_vulkan_sdk(target_root, system)
    if not copied["valid"]:
        raise RuntimeError(f"Copied Vulkan SDK is incomplete: {target_root}")
    return copied


def _candidate_vulkan_sdk_sources(system: str) -> list[Path]:
    candidates: list[Path] = []
    env_candidates = [
        os.environ.get("AUDIA_VULKAN_SDK_SOURCE", "").strip(),
        os.environ.get("VULKAN_SDK", "").strip(),
    ]
    for candidate in env_candidates:
        if candidate:
            candidates.append(Path(candidate))

    if system == "windows":
        for base in (
            os.environ.get("ProgramFiles", r"C:\\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\\Program Files (x86)"),
        ):
            base_path = Path(base)
            if base_path.exists():
                candidates.extend(sorted(base_path.glob("VulkanSDK/*"), reverse=True))
    elif system == "linux":
        candidates.extend(
            [
                Path("/opt/vulkan-sdk"),
                Path("/usr/local/vulkan-sdk"),
                Path("/usr/share/vulkan-sdk"),
            ]
        )
        for pattern in ("/opt/VulkanSDK/*", "/opt/vulkan-sdk/*"):
            for match in sorted(Path("/").glob(pattern.lstrip("/")), reverse=True):
                candidates.append(match)

    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve(strict=False)).lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def resolve_vulkan_sdk_source(system: str) -> Path | None:
    for candidate in _candidate_vulkan_sdk_sources(system):
        if candidate.exists() and describe_vulkan_sdk(candidate, system)["valid"]:
            return candidate
    return None


def ensure_local_vulkan_sdk(root: Path, profile: dict[str, Any], system: str) -> dict[str, Any]:
    configured_root = os.environ.get("AUDIA_VULKAN_SDK_ROOT", "").strip() or str(profile.get("vulkan_sdk_root", "")).strip()
    if configured_root:
        target_root = Path(configured_root)
        if not target_root.is_absolute():
            target_root = root / target_root
    else:
        target_root = root / "toolchains" / "vulkan-sdk" / system
    details = describe_vulkan_sdk(target_root, system)
    if details["valid"]:
        return details

    source_root = resolve_vulkan_sdk_source(system)
    if source_root is not None:
        return copy_vulkan_sdk_subset(source_root, target_root, system)

    raise RuntimeError(
        "Local Vulkan SDK not available. Run 'python scripts/bootstrap_vulkan_sdk.py' "
        "or set AUDIA_VULKAN_SDK_SOURCE to an existing SDK directory."
    )


def vulkan_sdk_build_env(root: Path, profile: dict[str, Any], system: str) -> tuple[dict[str, str], dict[str, Any]]:
    details = ensure_local_vulkan_sdk(root, profile, system)
    env = {
        "VULKAN_SDK": str(details["sdk_root"]),
        "VK_SDK_PATH": str(details["sdk_root"]),
        "Vulkan_INCLUDE_DIR": str(details["include_dir"]),
        "Vulkan_LIBRARY": str(details["library_path"]),
        "Vulkan_GLSLC_EXECUTABLE": str(details["glslc_path"]),
    }
    current_path = os.environ.get("PATH", "")
    env["PATH"] = str(details["bin_dir"]) + os.pathsep + current_path if current_path else str(details["bin_dir"])
    current_prefix = os.environ.get("CMAKE_PREFIX_PATH", "")
    env["CMAKE_PREFIX_PATH"] = (
        str(details["sdk_root"]) + os.pathsep + current_prefix if current_prefix else str(details["sdk_root"])
    )
    return env, details


def describe_rocm_sdk(sdk_root: Path) -> dict[str, Any]:
    hip_candidates = [
        *sdk_root.rglob("hipConfig.cmake"),
        *sdk_root.rglob("hip-config.cmake"),
    ]
    hip_config = next((path for path in hip_candidates if path.is_file()), None)
    hip_config_dir = hip_config.parent if hip_config else None
    bin_dir = sdk_root / "bin"
    include_dir = sdk_root / "include"
    valid = sdk_root.exists() and hip_config is not None
    return {
        "sdk_root": sdk_root,
        "bin_dir": bin_dir,
        "include_dir": include_dir,
        "hip_config": hip_config,
        "hip_config_dir": hip_config_dir,
        "valid": valid,
    }


def copy_rocm_sdk_subset(source_root: Path, target_root: Path) -> dict[str, Any]:
    source = describe_rocm_sdk(source_root)
    if not source["valid"]:
        raise RuntimeError(f"Source ROCm SDK is incomplete: {source_root}")

    target_root.mkdir(parents=True, exist_ok=True)
    for rel_name in ("bin", "include", "lib", "lib64", "share"):
        source_path = source_root / rel_name
        target_path = target_root / rel_name
        if source_path.exists():
            if target_path.exists():
                shutil.rmtree(target_path)
            shutil.copytree(source_path, target_path)

    copied = describe_rocm_sdk(target_root)
    if not copied["valid"]:
        raise RuntimeError(f"Copied ROCm SDK is incomplete: {target_root}")
    return copied


def _candidate_rocm_sdk_sources(system: str) -> list[Path]:
    candidates: list[Path] = []
    env_candidates = [
        os.environ.get("AUDIA_ROCM_SDK_SOURCE", "").strip(),
        os.environ.get("ROCM_PATH", "").strip(),
        os.environ.get("HIP_PATH", "").strip(),
    ]
    for candidate in env_candidates:
        if candidate:
            candidates.append(Path(candidate))

    if system == "windows":
        program_dirs = [
            os.environ.get("ProgramFiles", r"C:\\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\\Program Files (x86)"),
        ]
        for base in program_dirs:
            base_path = Path(base)
            candidates.append(base_path / "AMD" / "ROCm")
            candidates.append(base_path / "ROCm")
            if base_path.exists():
                for child in sorted(base_path.glob("AMD/ROCm*"), reverse=True):
                    candidates.append(child)
                for child in sorted(base_path.glob("ROCm*"), reverse=True):
                    candidates.append(child)
    elif system == "linux":
        candidates.extend(
            [
                Path("/opt/rocm"),
                Path("/usr/local/rocm"),
            ]
        )
        for pattern in ("/opt/rocm-*", "/usr/local/rocm-*"):
            for match in sorted(Path("/").glob(pattern.lstrip("/")), reverse=True):
                candidates.append(match)

    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve(strict=False)).lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def resolve_rocm_sdk_source(system: str) -> Path | None:
    for candidate in _candidate_rocm_sdk_sources(system):
        if candidate.exists() and describe_rocm_sdk(candidate)["valid"]:
            return candidate
    return None


def ensure_local_rocm_sdk(root: Path, profile: dict[str, Any], system: str) -> dict[str, Any]:
    configured_root = str(profile.get("rocm_sdk_root", "")).strip()
    if configured_root:
        target_root = Path(configured_root)
        if not target_root.is_absolute():
            target_root = root / target_root
    else:
        target_root = root / "toolchains" / "rocm-sdk" / system

    details = describe_rocm_sdk(target_root)
    if not details["valid"]:
        source_root = resolve_rocm_sdk_source(system)
        if source_root is not None:
            if source_root.resolve() != target_root.resolve():
                details = copy_rocm_sdk_subset(source_root, target_root)
                if details["valid"]:
                    return details
        raise RuntimeError(
            "Local ROCm SDK not available. Run 'python scripts/bootstrap_rocm_sdk.py' "
            "or set AUDIA_ROCM_SDK_SOURCE, ROCM_PATH, or HIP_PATH to an existing ROCm install "
            "that includes hipConfig.cmake."
        )
    return details


def rocm_sdk_build_env(root: Path, profile: dict[str, Any], system: str) -> tuple[dict[str, str], dict[str, Any]]:
    details = ensure_local_rocm_sdk(root, profile, system)
    env = {
        "ROCM_PATH": str(details["sdk_root"]),
        "HIP_PATH": str(details["sdk_root"]),
    }
    if details.get("hip_config_dir"):
        env["hip_DIR"] = str(details["hip_config_dir"])
    current_path = os.environ.get("PATH", "")
    if details["bin_dir"].exists():
        env["PATH"] = str(details["bin_dir"]) + os.pathsep + current_path if current_path else str(details["bin_dir"])
    current_prefix = os.environ.get("CMAKE_PREFIX_PATH", "")
    env["CMAKE_PREFIX_PATH"] = (
        str(details["sdk_root"]) + os.pathsep + current_prefix if current_prefix else str(details["sdk_root"])
    )
    return env, details


def _profile_toolchain_requirements(profile: dict[str, Any]) -> list[str]:
    requirements = profile.get("required_toolchains", [])
    if isinstance(requirements, str):
        requirements = [requirements]
    if not isinstance(requirements, list):
        requirements = []
    normalized = [str(item).strip().lower() for item in requirements if str(item).strip()]
    if bool(profile.get("requires_vulkan_sdk", False)) and "vulkan_sdk" not in normalized:
        normalized.append("vulkan_sdk")
    return normalized


def build_toolchain_env(root: Path, profile: dict[str, Any], system: str) -> tuple[dict[str, str], list[dict[str, Any]]]:
    env: dict[str, str] = {}
    details: list[dict[str, Any]] = []
    for requirement in _profile_toolchain_requirements(profile):
        if requirement == "vulkan_sdk":
            toolchain_env, toolchain_details = vulkan_sdk_build_env(root, profile, system)
        elif requirement == "rocm_sdk":
            toolchain_env, toolchain_details = rocm_sdk_build_env(root, profile, system)
        else:
            raise RuntimeError(f"Unsupported llama.cpp toolchain requirement: {requirement}")
        env.update(toolchain_env)
        details.append({"kind": requirement, **toolchain_details})
    return env, details


def ensure_python_runtime(root: Path, min_version: str) -> dict[str, Any]:
    system = detect_platform()
    py_exe = root / ".venv" / ("Scripts" if system == "windows" else "bin") / ("python.exe" if system == "windows" else "python3")
    if py_exe.exists():
        return {"path": str(py_exe), "version": min_version}
    # Candidate names in priority order; python3 is the standard name on Linux
    candidates = ["python3", "python"] if system == "linux" else ["python"]
    if system == "windows":
        candidates = ["python", "py"]
    python_cmd = next((shutil.which(c) for c in candidates if shutil.which(c)), None)
    if python_cmd:
        if system == "windows" and python_cmd.endswith("py.exe"):
            run_command([python_cmd, "-3", "-m", "venv", str(root / ".venv")], cwd=root)
        else:
            run_command([python_cmd, "-m", "venv", str(root / ".venv")], cwd=root)
    else:
        raise RuntimeError(f"Python was not found. Install Python {min_version}+ first or provide it via PATH.")
    return {"path": str(py_exe), "version": min_version}


def venv_python(root: Path) -> Path:
    return root / ".venv" / ("Scripts" if detect_platform() == "windows" else "bin") / ("python.exe" if detect_platform() == "windows" else "python3")


def ensure_gateway_python_deps(root: Path) -> dict[str, Any]:
    python_path = venv_python(root)
    run_command([str(python_path), "-m", "pip", "install", "--upgrade", "pip"], cwd=root)
    run_command([str(python_path), "-m", "pip", "install", "-r", "requirements.txt"], cwd=root)
    return {"venv_python": str(python_path)}


def package_manager_available(name: str) -> bool:
    return shutil.which(name) is not None


def ensure_llama_swap(root: Path) -> dict[str, Any]:
    from src.launcher.config_loader import load_stack_config

    if os.environ.get("LLAMA_SWAP_EXE"):
        return {"mode": "env", "path": os.environ["LLAMA_SWAP_EXE"]}
    if shutil.which("llama-swap"):
        return {"mode": "path", "path": shutil.which("llama-swap")}
    system = detect_platform()
    if system == "windows" and package_manager_available("winget"):
        run_command(["winget", "install", "llama-swap", "--accept-source-agreements", "--accept-package-agreements"])
    elif system == "macos" and package_manager_available("brew"):
        run_command(["brew", "install", "llama-swap"])
    else:
        # Attempt a GitHub release download for llama-swap
        stack = load_stack_config(root)
        swap_settings = stack.component_settings.get("llama_swap", {})
        owner = str(swap_settings.get("repo_owner", "mostlygeek"))
        repo = str(swap_settings.get("repo_name", "llama-swap"))
        version = str(swap_settings.get("version", "latest"))
        install_root = root / str(swap_settings.get("install_root", "tools/llama-swap"))
        try:
            metadata = get_release_metadata(owner, repo, version)
            exe_name = "llama-swap.exe" if system == "windows" else "llama-swap"
            # Common token patterns for GitHub release assets.
            # mostlygeek/llama-swap names assets as linux_amd64, windows_amd64, darwin_amd64.
            token_map = {
                "linux": ["linux", "amd64"],
                "windows": ["windows", "amd64"],
                "macos": ["darwin", "amd64"],
            }
            tokens = token_map.get(system, [system])
            asset = find_release_asset(metadata, tokens)
            asset_name = str(asset.get("name", "llama-swap-asset"))
            browser_url = str(asset.get("browser_download_url", ""))
            install_root.mkdir(parents=True, exist_ok=True)
            archive_path = download_file(browser_url, install_root / asset_name)
            extracted = extract_component_archive(archive_path, install_root / "bin")
            exe_path = extracted / exe_name if (extracted / exe_name).exists() else next(install_root.rglob(exe_name), None)
            if exe_path and exe_path.exists():
                if system != "windows":
                    exe_path.chmod(exe_path.stat().st_mode | 0o111)
                os.environ.setdefault("LLAMA_SWAP_EXE", str(exe_path))
                return {"mode": "github", "path": str(exe_path)}
        except Exception:
            pass
    if shutil.which("llama-swap"):
        return {"mode": "path", "path": shutil.which("llama-swap")}
    return {"mode": "manual", "path": ""}


def _resolve_llama_cpp_profiles(settings: dict[str, Any], system: str) -> list[tuple[str, dict[str, Any]]]:
    """Return ordered list of (profile_name, profile_dict) to install for the given platform.

    ``default_profiles.<system>`` may be a single string or a list of profile names.
    Profiles whose ``platform`` field doesn't match the current system are silently skipped.
    """
    profiles = settings.get("profiles", {})
    if not isinstance(profiles, dict) or not profiles:
        raise RuntimeError("llama.cpp settings do not define any install profiles")

    selected = settings.get("selected_profile", "auto")
    if str(selected).strip() in ("", "auto"):
        defaults = settings.get("default_profiles", {})
        selected = defaults.get(system, "")

    if isinstance(selected, str):
        selected = [selected] if selected.strip() else []
    elif not isinstance(selected, list):
        selected = [str(selected)]

    if not selected:
        raise RuntimeError(f"llama.cpp settings do not define a default profile for platform '{system}'")

    result: list[tuple[str, dict[str, Any]]] = []
    for name in selected:
        name = str(name).strip()
        p = profiles.get(name)
        if not isinstance(p, dict):
            print(f"  [warn] llama.cpp profile '{name}' not defined — skipping", flush=True)
            continue
        pp = str(p.get("platform", "")).strip()
        if pp and pp != system:
            continue
        result.append((name, p))
    return result


def _install_one_llama_cpp_profile(
    root: Path,
    settings: dict[str, Any],
    profile_name: str,
    profile: dict[str, Any],
    system: str,
) -> dict[str, Any]:
    """Install a single llama.cpp profile from a release asset or git source build."""
    backend = str(profile.get("backend", ""))
    version = str(profile.get("version", "latest"))
    source_type = str(profile.get("source_type", settings.get("provider", "github_release"))).strip() or "github_release"
    install_root = root / str(settings.get("install_root", "tools/llama.cpp"))
    executable_names = settings.get("executable_names", {})
    executable_name = str(executable_names.get(system, "llama-server.exe" if system == "windows" else "llama-server"))
    sidecar_files = [str(item) for item in profile.get("sidecar_files", [])]
    copy_sidecar_to_binary_dir = bool(settings.get("copy_sidecar_to_binary_dir", True))
    if source_type in {"github_release", "direct_url"} and version != "latest":
        local_install_dir = install_root / f"{version}-{backend}"
        cached_local = _local_llama_cpp_install_result(
            install_dir=local_install_dir,
            executable_name=executable_name,
            system=system,
            profile_name=profile_name,
            source_type=source_type,
            backend=backend,
            version=version,
            sidecar_files=sidecar_files,
            copy_sidecar_to_binary_dir=copy_sidecar_to_binary_dir,
        )
        if cached_local is not None:
            return cached_local
    signature = _llama_cpp_cache_signature(
        root=root,
        profile_name=profile_name,
        profile=profile,
        system=system,
        source_type=source_type,
        version=version,
        backend=backend,
    )

    if source_type == "github_release":
        owner = str(profile.get("repo_owner", settings.get("repo_owner", "ggml-org")))
        repo = str(profile.get("repo_name", settings.get("repo_name", "llama.cpp")))
        binary_subdir = str(settings.get("binary_subdir", "bin"))
        asset_tokens = [str(item) for item in profile.get("asset_match_tokens", [])]
        if not asset_tokens:
            raise RuntimeError(f"No asset-match tokens configured for llama.cpp profile '{profile_name}'")

        metadata = get_release_metadata(owner, repo, version)
        tag = str(metadata.get("tag_name", version))
        current_signature = {**signature, "version": tag}
        cached = _load_previous_llama_cpp_variant(root, profile_name)
        if cached and _llama_cpp_cache_matches(cached, current_signature):
            executable_path = Path(str(cached.get("executable_path", "")))
            if executable_path.exists():
                cached = {**cached, "cache_hit": True}
                return cached
        asset = find_release_asset(metadata, asset_tokens)
        asset_name = str(asset.get("name", "llama.cpp-asset"))
        browser_url = str(asset.get("browser_download_url", ""))
        if not browser_url:
            raise RuntimeError(f"llama.cpp asset '{asset_name}' does not expose browser_download_url")

        install_dir = install_root / f"{tag}-{backend}"
        with tempfile.TemporaryDirectory(prefix="audia-llamacpp-") as tmp_dir:
            tmp_root = Path(tmp_dir)
            archive_path = download_file(browser_url, tmp_root / asset_name)
            extracted_root = extract_component_archive(archive_path, tmp_root / "extract")
            if install_dir.exists():
                shutil.rmtree(install_dir)
            install_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(extracted_root, install_dir)

        executable_path = install_dir / binary_subdir / executable_name
        if not executable_path.exists():
            fallback = next(install_dir.rglob(executable_name), None)
            if fallback is None:
                raise RuntimeError(f"Installed llama.cpp asset did not contain {executable_name}")
            executable_path = fallback

        copied_sidecars: list[str] = []
        if copy_sidecar_to_binary_dir and sidecar_files:
            for source_file in sidecar_files:
                source_path = Path(source_file)
                if source_path.exists():
                    target_path = executable_path.parent / source_path.name
                    shutil.copy2(source_path, target_path)
                    copied_sidecars.append(str(target_path))

        result: dict[str, Any] = {
            "system": system,
            "provider": "github_release",
            "source_type": source_type,
            "profile": profile_name,
            "version": tag,
            "backend": backend,
            "install_dir": str(install_dir),
            "asset_name": asset_name,
            "executable_path": str(executable_path),
            "copied_sidecars": copied_sidecars,
        }
        if backend == "rocm":
            result["rocm_executable_path"] = str(executable_path)
        return result

    if source_type == "direct_url":
        download_url = str(profile.get("download_url", "")).strip()
        archive_type = str(profile.get("archive_type", "")).strip().lower()
        if not download_url:
            raise RuntimeError(f"llama.cpp direct_url profile '{profile_name}' is missing download_url")
        asset_name = Path(download_url.split("?", 1)[0]).name or f"{profile_name}.{archive_type or 'zip'}"
        cached = _load_previous_llama_cpp_variant(root, profile_name)
        if cached and _llama_cpp_cache_matches(cached, signature):
            executable_path = Path(str(cached.get("executable_path", "")))
            if executable_path.exists():
                cached = {**cached, "cache_hit": True}
                return cached
        install_dir = install_root / f"{version}-{backend}"
        with tempfile.TemporaryDirectory(prefix="audia-llamacpp-url-") as tmp_dir:
            tmp_root = Path(tmp_dir)
            archive_path = download_file(download_url, tmp_root / asset_name)
            extracted_root = extract_component_archive(archive_path, tmp_root / "extract")
            if install_dir.exists():
                shutil.rmtree(install_dir)
            install_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(extracted_root, install_dir)

        executable_path = next(install_dir.rglob(executable_name), None)
        if executable_path is None:
            raise RuntimeError(f"Installed llama.cpp archive did not contain {executable_name}")

        copied_sidecars: list[str] = []
        if copy_sidecar_to_binary_dir and sidecar_files:
            for source_file in sidecar_files:
                source_path = Path(source_file)
                if source_path.exists():
                    target_path = executable_path.parent / source_path.name
                    shutil.copy2(source_path, target_path)
                    copied_sidecars.append(str(target_path))

        result = {
            "system": system,
            "provider": "direct_url",
            "source_type": source_type,
            "profile": profile_name,
            "version": version,
            "backend": backend,
            "install_dir": str(install_dir),
            "asset_name": asset_name,
            "download_url": download_url,
            "executable_path": str(executable_path),
            "copied_sidecars": copied_sidecars,
        }
        if backend == "rocm":
            result["rocm_executable_path"] = str(executable_path)
        return result

    if source_type != "git":
        raise RuntimeError(f"Unsupported llama.cpp source_type: {source_type}")

    git_url = str(profile.get("git_url", "")).strip()
    git_ref = str(profile.get("git_ref", version)).strip() or version
    git_commit = str(profile.get("git_commit", "")).strip() or None
    configure_command = str(profile.get("configure_command", "")).strip()
    build_command = str(profile.get("build_command", "")).strip()
    binary_glob = profile.get("binary_glob")
    library_glob = profile.get("library_glob")
    build_env = {str(k): str(v) for k, v in dict(profile.get("build_env", {}) or {}).items()}
    toolchain_details: list[dict[str, Any]] = []
    if not git_url:
        raise RuntimeError(f"llama.cpp git profile '{profile_name}' is missing git_url")
    if not configure_command or not build_command:
        raise RuntimeError(f"llama.cpp git profile '{profile_name}' must define configure_command and build_command")
    if not binary_glob:
        raise RuntimeError(f"llama.cpp git profile '{profile_name}' must define binary_glob")
    git_executable = shutil.which("git")
    if not git_executable:
        raise RuntimeError("git is required to install git-backed llama.cpp profiles")

    install_dir = install_root / f"{version}-{backend}"
    cached = _load_previous_llama_cpp_variant(root, profile_name)
    if cached and _llama_cpp_cache_matches(cached, signature):
        executable_path = Path(str(cached.get("executable_path", "")))
        if executable_path.exists():
            cached = {**cached, "cache_hit": True}
            return cached
    with tempfile.TemporaryDirectory(prefix="audia-llamacpp-git-") as tmp_dir:
        tmp_root = Path(tmp_dir)
        source_dir = tmp_root / "source"
        git_checkout_ref(git_executable, git_url, git_ref, source_dir, git_commit=git_commit)
        env = os.environ.copy()
        env.update(build_env)
        toolchain_env, toolchain_details = build_toolchain_env(root, profile, system)
        env.update(toolchain_env)
        run_shell_command(configure_command, cwd=source_dir, env=env)
        run_shell_command(build_command, cwd=source_dir, env=env)

        binary_matches = [path for path in _glob_matches(source_dir, binary_glob) if path.is_file()]
        if not binary_matches:
            raise RuntimeError(f"llama.cpp git profile '{profile_name}' did not produce a binary matching {binary_glob!r}")
        executable_path = binary_matches[0]

        if install_dir.exists():
            shutil.rmtree(install_dir)
        binary_dir = install_dir / "bin"
        binary_dir.mkdir(parents=True, exist_ok=True)
        installed_executable = binary_dir / executable_path.name
        shutil.copy2(executable_path, installed_executable)

        copied_sidecars: list[str] = []
        for source_path in _glob_matches(source_dir, library_glob):
            if source_path.is_file():
                target_path = binary_dir / source_path.name
                shutil.copy2(source_path, target_path)
                copied_sidecars.append(str(target_path))
        if copy_sidecar_to_binary_dir and sidecar_files:
            for source_file in sidecar_files:
                source_path = Path(source_file)
                if source_path.exists():
                    target_path = binary_dir / source_path.name
                    shutil.copy2(source_path, target_path)
                    copied_sidecars.append(str(target_path))
        if system != "windows":
            installed_executable.chmod(installed_executable.stat().st_mode | 0o111)

    result = {
        "system": system,
        "provider": "git",
        "source_type": source_type,
        "profile": profile_name,
        "version": version,
        "backend": backend,
        "install_dir": str(install_dir),
        "asset_name": "",
        "executable_path": str(installed_executable),
        "copied_sidecars": copied_sidecars,
        "git_url": git_url,
        "git_ref": git_ref,
        "git_commit": git_commit,
    }
    if toolchain_details:
        result["toolchains"] = [
            {"kind": item["kind"], "sdk_root": str(item["sdk_root"])} for item in toolchain_details
        ]
        result["toolchain_root"] = str(toolchain_details[0]["sdk_root"])
    if backend == "rocm":
        result["rocm_executable_path"] = str(installed_executable)
    return result


def ensure_llama_cpp(root: Path) -> dict[str, Any]:
    from src.launcher.config_loader import load_stack_config

    stack = load_stack_config(root)
    settings = stack.component_settings.get("llama_cpp", {})

    system = detect_platform()
    executable_name = str(settings.get("executable_names", {}).get(
        system, "llama-server.exe" if system == "windows" else "llama-server"
    ))

    # Fast path: if executable is already in PATH (system package or test stub)
    found_in_path = shutil.which(executable_name)
    if found_in_path:
        return {
            "provider": "path",
            "profile": "system",
            "version": "system",
            "backend": "cpu",
            "install_dir": str(Path(found_in_path).parent.parent),
            "asset_name": "",
            "executable_path": found_in_path,
            "copied_sidecars": [],
            "variants": {"system": {
                "provider": "path",
                "profile": "system",
                "version": "system",
                "backend": "cpu",
                "executable_path": found_in_path,
            }},
        }

    profiles_to_install = _resolve_llama_cpp_profiles(settings, system)
    installed_variants: dict[str, Any] = {}
    primary_result: dict[str, Any] | None = None

    for pname, profile in profiles_to_install:
        try:
            print(f"  Installing llama.cpp profile: {pname}", flush=True)
            r = _install_one_llama_cpp_profile(root, settings, pname, profile, system)
            installed_variants[pname] = r
            # Prefer the cpu build as the default llama-server; otherwise first success
            if primary_result is None or str(r.get("backend", "")) == "cpu":
                primary_result = r
        except Exception as exc:
            print(f"  [warn] llama.cpp profile '{pname}' skipped: {exc}", flush=True)

    if primary_result is None:
        raise RuntimeError("No llama.cpp profiles could be installed")

    return {**primary_result, "variants": installed_variants}


def resolve_llama_cpp_profile(settings: dict[str, Any], system: str) -> tuple[str, dict[str, Any]]:
    profiles = settings.get("profiles", {})
    if not isinstance(profiles, dict) or not profiles:
        raise RuntimeError("llama.cpp settings do not define any install profiles")

    selected_profile = str(settings.get("selected_profile", "auto")).strip() or "auto"
    if selected_profile == "auto":
        defaults = settings.get("default_profiles", {})
        if not isinstance(defaults, dict):
            defaults = {}
        selected_profile = str(defaults.get(system, "")).strip()
        if not selected_profile:
            raise RuntimeError(f"llama.cpp settings do not define a default profile for platform '{system}'")

    profile = profiles.get(selected_profile)
    if not isinstance(profile, dict):
        raise RuntimeError(f"llama.cpp profile '{selected_profile}' is not defined")

    profile_platform = str(profile.get("platform", "")).strip()
    if profile_platform and profile_platform != system:
        raise RuntimeError(
            f"llama.cpp profile '{selected_profile}' targets platform '{profile_platform}', not '{system}'"
        )
    return selected_profile, profile


def _find_nginx() -> str:
    """Return the absolute path to nginx, checking PATH and well-known system locations."""
    found = shutil.which("nginx")
    if found:
        return found
    # Package managers on Linux install nginx to /usr/sbin/nginx or /usr/bin/nginx;
    # these may not appear in the PATH of the current non-login process.
    for candidate in ["/usr/sbin/nginx", "/usr/bin/nginx", "/usr/local/bin/nginx", "/opt/homebrew/bin/nginx"]:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return ""


def ensure_nginx(root: Path) -> dict[str, Any]:
    found = _find_nginx()
    if found:
        return {"mode": "path", "path": found}
    system = detect_platform()
    if system == "windows" and package_manager_available("winget"):
        run_command(["winget", "install", "nginxinc.nginx", "--accept-source-agreements", "--accept-package-agreements"])
    elif system == "macos" and package_manager_available("brew"):
        run_command(["brew", "install", "nginx"])
    elif system == "linux":
        if package_manager_available("apt-get"):
            run_command(["sudo", "apt-get", "update"])
            run_command(["sudo", "apt-get", "install", "-y", "nginx"])
        elif package_manager_available("zypper"):
            run_command(["sudo", "zypper", "--non-interactive", "install", "nginx"])
        elif package_manager_available("dnf"):
            run_command(["sudo", "dnf", "install", "-y", "nginx"])
        elif package_manager_available("yum"):
            run_command(["sudo", "yum", "install", "-y", "nginx"])
        elif package_manager_available("pacman"):
            run_command(["sudo", "pacman", "-Sy", "--noconfirm", "nginx"])
        else:
            raise RuntimeError("No supported Linux package manager found for nginx. Install it manually: apt-get/zypper/dnf/yum/pacman install nginx")
    else:
        raise RuntimeError("nginx could not be installed automatically on this machine.")
    found = _find_nginx()
    if not found:
        raise RuntimeError("nginx was installed but could not be located. Check your PATH or install it manually.")
    return {"mode": "path", "path": found}


def _detect_firewall_manager() -> str:
    """Return the active firewall manager name, or '' if none found."""
    system = detect_platform()
    if system == "windows":
        return "netsh" if shutil.which("netsh") else ""
    if system == "linux":
        if shutil.which("firewall-cmd"):
            return "firewalld"
        if shutil.which("ufw"):
            return "ufw"
        if shutil.which("iptables"):
            return "iptables"
    return ""


def ensure_firewall(root: Path) -> dict[str, Any]:
    """Open gateway service ports in the system firewall.

    Only opens ports whose bound host is not loopback (127.x.x.x).
    Skips silently on platforms with no recognised firewall manager.
    """
    from src.launcher.config_loader import load_stack_config

    stack = load_stack_config(root)
    manager = _detect_firewall_manager()
    if not manager:
        return {"manager": "none", "opened": [], "skipped": []}

    ports_to_open: list[int] = []
    skipped: list[str] = []

    def _consider(host: str, port: int, label: str) -> None:
        if host and not host.startswith("127."):
            ports_to_open.append(port)
        else:
            skipped.append(f"{label}:{port} (loopback)")

    _consider(stack.network.litellm_host, stack.network.litellm_port, "litellm")
    _consider(stack.network.llamaswap_host, stack.network.llamaswap_port, "llama-swap")
    if stack.nginx.enabled:
        _consider(stack.network.nginx_host, stack.network.nginx_port, "nginx")

    opened: list[str] = []
    for port in sorted(set(ports_to_open)):
        try:
            if manager == "firewalld":
                run_command(["firewall-cmd", "--permanent", f"--add-port={port}/tcp"])
            elif manager == "ufw":
                run_command(["ufw", "allow", f"{port}/tcp"])
            elif manager == "iptables":
                run_command(["iptables", "-C", "INPUT", "-p", "tcp", "--dport", str(port), "-j", "ACCEPT"])
            elif manager == "netsh":
                run_command(["netsh", "advfirewall", "firewall", "add", "rule",
                             "name=AUDiaLLMGateway", "dir=in", "action=allow",
                             "protocol=TCP", f"localport={port}"])
            opened.append(str(port))
        except subprocess.CalledProcessError as exc:
            print(f"  [warn] firewall: failed to open port {port}: {exc}", flush=True)

    if manager == "firewalld" and opened:
        try:
            run_command(["firewall-cmd", "--reload"])
        except subprocess.CalledProcessError as exc:
            print(f"  [warn] firewall: reload failed: {exc}", flush=True)

    return {"manager": manager, "opened": opened, "skipped": skipped}


def ensure_models(root: Path, model_names: list[str] | None = None) -> dict[str, Any]:
    """Download model files to workspace/models/ based on the model catalog.

    Each labeled model deployment that matches ``model_names`` (or all labeled
    deployments when ``model_names`` is ``None``) is downloaded using the URLs
    declared in the model catalog's ``artifacts`` section. Files are skipped
    when they already exist so re-runs only fetch missing files.

    The returned dict includes ``model_dir`` (the absolute path of the models
    root directory) which ``build_llama_swap_config`` reads to inject the
    ``model-path`` / ``mmproj-path`` macros automatically.
    """
    from src.launcher.config_loader import load_stack_config, load_model_catalog

    stack = load_stack_config(root)
    models_settings = stack.component_settings.get("models", {})
    models_root = root / str(models_settings.get("install_root", "models"))
    models_root.mkdir(parents=True, exist_ok=True)

    _, _, catalog = load_model_catalog(root)
    profiles = catalog.get("model_profiles", {})

    results: dict[str, Any] = {}
    for _, profile in profiles.items():
        if not isinstance(profile, dict):
            continue
        deployments = profile.get("deployments", {})
        if not isinstance(deployments, dict):
            continue
        labels = [
            str(deployment.get("label", "")).strip()
            for deployment in deployments.values()
            if isinstance(deployment, dict)
        ]
        labels = [label for label in labels if label]
        if not labels:
            continue
        if model_names is not None and not any(label in model_names for label in labels):
            continue

        artifacts = profile.get("artifacts", {})
        source_type = str(artifacts.get("source_type", "download")).strip().lower() or "download"
        source_path_raw = str(artifacts.get("source_path", "")).strip()
        source_path = Path(source_path_raw).expanduser()
        if source_path_raw and not source_path.is_absolute():
            source_path = (root / source_path).resolve()
        if source_type == "local_path" and (not source_path_raw or not source_path.exists()):
            raise RuntimeError("Model profile declares source_type=local_path but source_path is missing or invalid")

        model_file = str(artifacts.get("model_file", "")).replace("\\", "/")
        model_url = str(artifacts.get("model_url", ""))
        additional_model_urls = [str(item) for item in artifacts.get("additional_model_urls", []) if str(item).strip()]
        mmproj_file = str(artifacts.get("mmproj_file", "")).replace("\\", "/")
        mmproj_url = str(artifacts.get("mmproj_url", ""))

        entry: dict[str, Any] = {"source_type": source_type}
        if source_path_raw:
            entry["source_path"] = str(source_path)
        materialized = False

        def _materialize_file(relative_path: str, url: str) -> str | None:
            nonlocal materialized
            if not relative_path:
                return None
            dest = models_root / relative_path
            local_source = _resolve_local_artifact_source(source_path, relative_path) if source_path_raw else None
            if source_type in {"local_path", "auto"} and local_source and local_source.exists():
                _copy_artifact_if_needed(local_source, dest)
                materialized = True
                return str(dest)
            if url:
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.exists():
                    download_file(url, dest)
                materialized = True
                return str(dest)
            if local_source and local_source.exists():
                _copy_artifact_if_needed(local_source, dest)
                materialized = True
                return str(dest)
            return None

        model_path = _materialize_file(model_file, model_url)
        if model_path:
            entry["model_path"] = model_path
        for extra_url in additional_model_urls:
            relative_name = Path(extra_url.split("?", 1)[0]).name
            extra_relative = str(Path(model_file).with_name(relative_name)) if model_file else relative_name
            extra_path = _materialize_file(extra_relative, extra_url)
            if extra_path:
                entry.setdefault("additional_model_paths", []).append(extra_path)
        mmproj_path = _materialize_file(mmproj_file, mmproj_url)
        if mmproj_path:
            entry["mmproj_path"] = mmproj_path
        if materialized:
            for label in labels:
                if model_names is None or label in model_names:
                    results[label] = entry

    return {"model_dir": str(models_root), "models": results}


COMPONENT_INSTALLERS = {
    "python_runtime": ensure_python_runtime,
    "gateway_python_deps": ensure_gateway_python_deps,
    "llama_cpp": ensure_llama_cpp,
    "llama_swap": ensure_llama_swap,
    "nginx": ensure_nginx,
    "firewall": ensure_firewall,
    "models": ensure_models,
}


def resolve_component_selection(manifest: dict[str, Any], requested: list[str] | None, previous: list[str] | None = None) -> list[str]:
    components = manifest.get("components", {})
    selected = set(previous or [])
    if requested:
        selected.update(requested)
    for name, definition in components.items():
        if definition.get("required") or definition.get("default_enabled"):
            selected.add(name)
    resolved = []
    for name in components:
        if name in selected:
            resolved.append(name)
    return resolved


def install_components(root: Path, manifest: dict[str, Any], selected_components: list[str]) -> dict[str, Any]:
    from src.launcher.config_loader import load_stack_config

    stack = load_stack_config(root)
    results: dict[str, Any] = {}
    for component in selected_components:
        installer = COMPONENT_INSTALLERS.get(component)
        if installer is None:
            continue
        if component == "python_runtime":
            results[component] = installer(root, stack.install.python_min_version)
        else:
            results[component] = installer(root)
    return results


def load_state(root: Path) -> dict[str, Any]:
    from src.launcher.config_loader import load_stack_config

    stack = load_stack_config(root)
    path = root / stack.project.state_path
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_state(root: Path, payload: dict[str, Any]) -> Path:
    from src.launcher.config_loader import load_stack_config

    stack = load_stack_config(root)
    path = root / stack.project.state_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _merge_llama_cpp_result(previous: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Merge a new llama_cpp installer result into the accumulated state dict.

    Preserves all previously-installed variants and adds/updates with new ones.
    The top-level fields (executable_path, profile, etc.) come from ``new``.
    """
    if not isinstance(previous, dict):
        previous = {}
    merged_variants: dict[str, Any] = dict(previous.get("variants", {}) or {})
    # Absorb all variants reported by the new result
    for vname, vinfo in (new.get("variants", {}) or {}).items():
        merged_variants[vname] = {k: v for k, v in vinfo.items() if k != "variants"}
    # Ensure the primary profile is also in variants
    primary = new.get("profile")
    if primary and primary not in merged_variants:
        merged_variants[primary] = {k: v for k, v in new.items() if k != "variants"}
    top = {k: v for k, v in new.items() if k != "variants"}
    return {**top, "variants": merged_variants}


def install_or_update_from_bundle(bundle_root: Path, install_root: Path, version: str, requested_components: list[str] | None, previous_state: dict[str, Any] | None = None) -> dict[str, Any]:
    manifest = load_manifest(bundle_root)
    sync_release_tree(
        bundle_root,
        install_root,
        [str(item) for item in manifest.get("paths", {}).get("managed", [])],
        [str(item) for item in manifest.get("paths", {}).get("seed_if_missing", [])],
    )
    installed_manifest = load_manifest(install_root)
    selected_components = resolve_component_selection(installed_manifest, requested_components, previous_state.get("selected_components") if previous_state else None)
    new_results = install_components(install_root, installed_manifest, selected_components)

    # Merge results into previous state to preserve variants (like multiple llama.cpp profiles)
    component_results = (previous_state or {}).get("component_results", {}).copy()
    for k, v in new_results.items():
        if k == "llama_cpp" and isinstance(v, dict):
            component_results["llama_cpp"] = _merge_llama_cpp_result(
                component_results.get("llama_cpp", {}), v
            )
        else:
            component_results[k] = v

    from src.launcher.config_loader import validate_layered_configs

    warnings = validate_layered_configs(install_root)
    state = {
        "product": "AUDiaLLMGateway",
        "version": version,
        "install_root": str(install_root),
        "updated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "selected_components": selected_components,
        "component_results": component_results,
        "config_validation": warnings,
        "available_updates": check_available_updates(install_root, component_results),
    }
    write_state(install_root, state)
    return state


def install_release(owner: str, repo: str, install_dir: str, version: str, requested_components: list[str] | None = None) -> dict[str, Any]:
    metadata = get_release_metadata(owner, repo, version)
    archive_kind = "zipball" if detect_platform() == "windows" else "tarball"
    archive_url, suffix = choose_archive_url(metadata, archive_kind)
    with tempfile.TemporaryDirectory(prefix="audia-install-") as tmp_dir:
        tmp_root = Path(tmp_dir)
        archive_path = download_file(archive_url, tmp_root / f"release{suffix}")
        bundle_root = extract_archive(archive_path, tmp_root / "bundle")
        return install_or_update_from_bundle(
            bundle_root=bundle_root,
            install_root=Path(install_dir).resolve(),
            version=str(metadata.get("tag_name", version)),
            requested_components=requested_components,
        )


def update_release(root: str | Path, version: str = "latest", requested_components: list[str] | None = None) -> dict[str, Any]:
    install_root = Path(root).resolve()
    from src.launcher.config_loader import load_stack_config

    stack = load_stack_config(install_root)
    metadata = get_release_metadata(stack.project.github_owner, stack.project.github_repo, version)
    archive_kind = "zipball" if detect_platform() == "windows" else "tarball"
    archive_url, suffix = choose_archive_url(metadata, archive_kind)
    previous_state = load_state(install_root)
    with tempfile.TemporaryDirectory(prefix="audia-update-") as tmp_dir:
        tmp_root = Path(tmp_dir)
        archive_path = download_file(archive_url, tmp_root / f"release{suffix}")
        bundle_root = extract_archive(archive_path, tmp_root / "bundle")
        return install_or_update_from_bundle(
            bundle_root=bundle_root,
            install_root=install_root,
            version=str(metadata.get("tag_name", version)),
            requested_components=requested_components,
            previous_state=previous_state,
        )


def parse_component_args(values: list[str] | None) -> list[str] | None:
    if not values:
        return None
    components: list[str] = []
    for value in values:
        components.extend([item.strip() for item in value.split(",") if item.strip()])
    return components


def install_components_on_root(root: str | Path, requested_components: list[str] | None = None) -> dict[str, Any]:
    """Run component installers on an already-installed root without re-syncing files.

    Used by postinstall scripts after an RPM/DEB package install where the source
    files are already in place and only the binary dependencies need downloading.
    """
    from src.launcher.config_loader import validate_layered_configs, write_generated_configs

    install_root = Path(root).resolve()
    manifest = load_manifest(install_root)
    previous_state = load_state(install_root)
    selected_components = resolve_component_selection(
        manifest,
        requested_components,
        previous_state.get("selected_components"),
    )
    new_results = install_components(install_root, manifest, selected_components)

    component_results = previous_state.get("component_results", {}).copy()
    for k, v in new_results.items():
        if k == "llama_cpp" and isinstance(v, dict):
            component_results["llama_cpp"] = _merge_llama_cpp_result(
                component_results.get("llama_cpp", {}), v
            )
        else:
            component_results[k] = v

    write_generated_configs(install_root)
    warnings = validate_layered_configs(install_root)
    state = {
        "product": "AUDiaLLMGateway",
        "version": previous_state.get("version", "package-install"),
        "install_root": str(install_root),
        "updated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "selected_components": selected_components,
        "component_results": component_results,
        "config_validation": warnings,
        "available_updates": {},
    }
    write_state(install_root, state)
    return state


def check_available_updates(root: str | Path, component_results: dict[str, Any] | None = None) -> dict[str, Any]:
    from src.launcher.config_loader import load_stack_config

    install_root = Path(root).resolve()
    stack = load_stack_config(install_root)
    state = load_state(install_root) if component_results is None else {"component_results": component_results}
    updates: dict[str, Any] = {}

    updates["gateway_release"] = release_summary(stack.project.github_owner, stack.project.github_repo, "latest")

    llama_cpp_settings = stack.component_settings.get("llama_cpp", {})
    updates["llama_cpp_release"] = release_summary(
        str(llama_cpp_settings.get("repo_owner", "ggml-org")),
        str(llama_cpp_settings.get("repo_name", "llama.cpp")),
        "latest",
    )
    installed_llama_cpp = state.get("component_results", {}).get("llama_cpp", {})
    if installed_llama_cpp:
        updates["llama_cpp_release"]["installed_version"] = installed_llama_cpp.get("version")

    return updates


def main() -> int:
    parser = argparse.ArgumentParser(description="Install or update AUDiaLLMGateway from GitHub releases.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install-release", help="Install from a GitHub release archive")
    install_parser.add_argument("--owner", default="ExampleOrg")
    install_parser.add_argument("--repo", default="AUDiaLLMGateway")
    install_parser.add_argument("--install-dir", required=True)
    install_parser.add_argument("--version", default="latest")
    install_parser.add_argument("--component", action="append", default=[])

    bundle_parser = subparsers.add_parser("install-bundle", help="Install from an already unpacked local release bundle")
    bundle_parser.add_argument("--bundle-root", required=True)
    bundle_parser.add_argument("--install-dir", required=True)
    bundle_parser.add_argument("--version", default="local-bundle")
    bundle_parser.add_argument("--component", action="append", default=[])

    update_parser = subparsers.add_parser("update-release", help="Update an existing installation from the latest release")
    update_parser.add_argument("--root", default=".")
    update_parser.add_argument("--version", default="latest")
    update_parser.add_argument("--component", action="append", default=[])

    components_parser = subparsers.add_parser("install-components", help="Run component installers on an already-installed root (no file sync)")
    components_parser.add_argument("--root", default=".")
    components_parser.add_argument("--component", action="append", default=[])

    check_updates_parser = subparsers.add_parser("check-updates", help="Check upstream release availability for the gateway and managed components")
    check_updates_parser.add_argument("--root", default=".")

    validate_parser = subparsers.add_parser("validate-configs", help="Validate project and local config layering")
    validate_parser.add_argument("--root", default=".")

    stack_parser = subparsers.add_parser("install-stack", help="Create Python venv and install pip dependencies")
    stack_parser.add_argument("--root", default=".")

    firewall_parser = subparsers.add_parser("install-firewall", help="Open gateway service ports in the system firewall")
    firewall_parser.add_argument("--root", default=".")

    args = parser.parse_args()

    if args.command == "install-release":
        result = install_release(args.owner, args.repo, args.install_dir, args.version, parse_component_args(args.component))
    elif args.command == "install-bundle":
        result = install_or_update_from_bundle(
            bundle_root=Path(args.bundle_root).resolve(),
            install_root=Path(args.install_dir).resolve(),
            version=args.version,
            requested_components=parse_component_args(args.component),
        )
    elif args.command == "update-release":
        result = update_release(args.root, args.version, parse_component_args(args.component))
    elif args.command == "install-components":
        result = install_components_on_root(args.root, parse_component_args(args.component))
    elif args.command == "check-updates":
        result = check_available_updates(args.root)
    elif args.command == "validate-configs":
        from src.launcher.config_loader import validate_layered_configs

        result = validate_layered_configs(args.root)
    elif args.command == "install-stack":
        root = Path(args.root).resolve()
        from src.launcher.config_loader import load_stack_config

        stack = load_stack_config(root)
        runtime = ensure_python_runtime(root, stack.install.python_min_version)
        deps = ensure_gateway_python_deps(root)
        result = {**runtime, **deps}
    elif args.command == "install-firewall":
        result = ensure_firewall(Path(args.root).resolve())
    else:
        parser.error(f"Unsupported command: {args.command}")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
