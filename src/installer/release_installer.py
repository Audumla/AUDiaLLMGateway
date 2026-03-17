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
    """Download, extract, and install a single llama.cpp build profile."""
    backend = str(profile.get("backend", ""))
    version = str(profile.get("version", "latest"))
    owner = str(settings.get("repo_owner", "ggml-org"))
    repo = str(settings.get("repo_name", "llama.cpp"))
    install_root = root / str(settings.get("install_root", "tools/llama.cpp"))
    binary_subdir = str(settings.get("binary_subdir", "bin"))
    executable_names = settings.get("executable_names", {})
    executable_name = str(executable_names.get(system, "llama-server.exe" if system == "windows" else "llama-server"))
    asset_tokens = [str(item) for item in profile.get("asset_match_tokens", [])]
    if not asset_tokens:
        raise RuntimeError(f"No asset-match tokens configured for llama.cpp profile '{profile_name}'")
    sidecar_files = [str(item) for item in profile.get("sidecar_files", [])]
    copy_sidecar_to_binary_dir = bool(settings.get("copy_sidecar_to_binary_dir", True))

    metadata = get_release_metadata(owner, repo, version)
    tag = str(metadata.get("tag_name", version))
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
        "provider": "github_release",
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


def ensure_llama_cpp(root: Path) -> dict[str, Any]:
    from src.launcher.config_loader import load_stack_config

    stack = load_stack_config(root)
    settings = stack.component_settings.get("llama_cpp", {})
    provider = str(settings.get("provider", "github_release"))
    if provider != "github_release":
        raise RuntimeError(f"Unsupported llama.cpp provider: {provider}")

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


def ensure_models(root: Path, model_names: list[str] | None = None) -> dict[str, Any]:
    """Download model files to workspace/models/ based on the model catalog.

    Each model exposure that matches ``model_names`` (or all exposures when
    ``model_names`` is ``None``) is downloaded using the URLs declared in the
    model catalog's ``artifacts`` section.  Files are skipped when they already
    exist so re-runs only fetch missing files.

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
    exposures = catalog.get("exposures", [])
    profiles = catalog.get("model_profiles", {})

    results: dict[str, Any] = {}
    for exposure in exposures:
        stable_name = str(exposure.get("stable_name", ""))
        if model_names is not None and stable_name not in model_names:
            continue
        profile_name = str(exposure.get("model_profile", ""))
        profile = profiles.get(profile_name, {})
        artifacts = profile.get("artifacts", {})
        model_file = str(artifacts.get("model_file", "")).replace("\\", "/")
        model_url = str(artifacts.get("model_url", ""))
        mmproj_file = str(artifacts.get("mmproj_file", "")).replace("\\", "/")
        mmproj_url = str(artifacts.get("mmproj_url", ""))

        entry: dict[str, Any] = {}
        if model_url and model_file:
            dest = models_root / model_file
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                download_file(model_url, dest)
            entry["model_path"] = str(dest)
        if mmproj_url and mmproj_file:
            dest = models_root / mmproj_file
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                download_file(mmproj_url, dest)
            entry["mmproj_path"] = str(dest)
        if entry:
            results[stable_name] = entry

    return {"model_dir": str(models_root), "models": results}


COMPONENT_INSTALLERS = {
    "python_runtime": ensure_python_runtime,
    "gateway_python_deps": ensure_gateway_python_deps,
    "llama_cpp": ensure_llama_cpp,
    "llama_swap": ensure_llama_swap,
    "nginx": ensure_nginx,
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
    else:
        parser.error(f"Unsupported command: {args.command}")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
