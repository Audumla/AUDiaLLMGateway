from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.request
import zipfile
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


def extract_archive(archive_path: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    if archive_path.suffix == ".zip":
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(destination)
    else:
        with tarfile.open(archive_path, "r:*") as tf:
            tf.extractall(destination)
    children = [child for child in destination.iterdir() if child.is_dir()]
    if len(children) != 1:
        raise RuntimeError(f"Expected one top-level extracted directory in {destination}")
    return children[0]


def extract_component_archive(archive_path: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    if archive_path.suffix == ".zip":
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(destination)
    else:
        with tarfile.open(archive_path, "r:*") as tf:
            tf.extractall(destination)
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
    py_exe = root / ".venv" / ("Scripts" if detect_platform() == "windows" else "bin") / ("python.exe" if detect_platform() == "windows" else "python3")
    if py_exe.exists():
        return {"path": str(py_exe), "version": min_version}
    python_cmd = shutil.which("python")
    if not python_cmd and detect_platform() == "windows":
        python_cmd = shutil.which("py")
        if python_cmd:
            run_command([python_cmd, "-3", "-m", "venv", str(root / ".venv")], cwd=root)
    elif python_cmd:
        run_command([python_cmd, "-m", "venv", str(root / ".venv")], cwd=root)
    else:
        raise RuntimeError("Python was not found. Install Python first or provide it via PATH.")
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
        raise RuntimeError("llama-swap could not be installed automatically on this machine. Set LLAMA_SWAP_EXE or install it manually.")
    if shutil.which("llama-swap"):
        return {"mode": "path", "path": shutil.which("llama-swap")}
    return {"mode": "manual", "path": ""}


def ensure_llama_cpp(root: Path) -> dict[str, Any]:
    from src.launcher.config_loader import load_stack_config

    stack = load_stack_config(root)
    settings = stack.component_settings.get("llama_cpp", {})
    provider = str(settings.get("provider", "github_release"))
    if provider != "github_release":
        raise RuntimeError(f"Unsupported llama.cpp provider: {provider}")

    system = detect_platform()
    backend_default = "vulkan" if system == "windows" else ("metal" if system == "macos" else "cpu")
    backend = str(settings.get("backend", backend_default))
    version = str(settings.get("version", "latest"))
    owner = str(settings.get("repo_owner", "ggml-org"))
    repo = str(settings.get("repo_name", "llama.cpp"))
    install_root = root / str(settings.get("install_root", "tools/llama.cpp"))
    binary_subdir = str(settings.get("binary_subdir", "bin"))
    executable_names = settings.get("executable_names", {})
    executable_name = str(executable_names.get(system, "llama-server.exe" if system == "windows" else "llama-server"))
    asset_tokens = [str(item) for item in settings.get("asset_match", {}).get(system, {}).get(backend, [])]
    if not asset_tokens:
        raise RuntimeError(f"No asset-match tokens configured for llama.cpp backend '{backend}' on {system}")
    sidecar_files = [str(item) for item in settings.get("sidecar_files", [])]
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

    result = {
        "provider": provider,
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


def ensure_nginx(root: Path) -> dict[str, Any]:
    if shutil.which("nginx"):
        return {"mode": "path", "path": shutil.which("nginx")}
    system = detect_platform()
    if system == "windows" and package_manager_available("winget"):
        run_command(["winget", "install", "nginx", "--accept-source-agreements", "--accept-package-agreements"])
    elif system == "macos" and package_manager_available("brew"):
        run_command(["brew", "install", "nginx"])
    elif system == "linux":
        if package_manager_available("apt-get"):
            run_command(["sudo", "apt-get", "update"])
            run_command(["sudo", "apt-get", "install", "-y", "nginx"])
        elif package_manager_available("dnf"):
            run_command(["sudo", "dnf", "install", "-y", "nginx"])
        else:
            raise RuntimeError("No supported Linux package manager found for nginx.")
    else:
        raise RuntimeError("nginx could not be installed automatically on this machine.")
    return {"mode": "path", "path": shutil.which("nginx") or ""}


COMPONENT_INSTALLERS = {
    "python_runtime": ensure_python_runtime,
    "gateway_python_deps": ensure_gateway_python_deps,
    "llama_cpp": ensure_llama_cpp,
    "llama_swap": ensure_llama_swap,
    "nginx": ensure_nginx,
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
    component_results = install_components(install_root, installed_manifest, selected_components)
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
    install_parser.add_argument("--owner", default="Audumla")
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
