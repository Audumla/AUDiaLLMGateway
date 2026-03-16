from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

from .config_loader import LiteLLMRuntime, LlamaSwapRuntime, NginxRuntime, load_stack_config, write_generated_configs
from .health import wait_for_any


def _resolve_exe(name: str) -> str:
    """Resolve a bare executable name to an absolute path if possible.

    Resolution order:
    1. Already absolute — return as-is.
    2. Next to sys.executable (venv Scripts/ or bin/ without shell activation).
    3. shutil.which() against PATH.
    4. Return the bare name and let the OS resolve it at Popen time.

    For tools installed outside the venv (nginx, litellm installed via pipx, etc.)
    the caller should resolve the path from install-state.json before calling this
    function, so that the absolute path is passed in directly.
    """
    import shutil
    if os.path.isabs(name):
        return name
    scripts_dir = Path(sys.executable).parent
    exts = [".exe", ".cmd", ".bat", ""] if os.name == "nt" else [""]
    for ext in exts:
        full = scripts_dir / (name + ext)
        if full.exists():
            return str(full)
    found = shutil.which(name)
    if found:
        return found
    return name


DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_NO_WINDOW = 0x08000000


def runtime_dir(root: Path) -> Path:
    return root / ".runtime"


def services_dir(root: Path) -> Path:
    return runtime_dir(root) / "services"


def logs_dir(root: Path) -> Path:
    return runtime_dir(root) / "logs"


def ensure_runtime_dirs(root: Path) -> None:
    services_dir(root).mkdir(parents=True, exist_ok=True)
    logs_dir(root).mkdir(parents=True, exist_ok=True)
    # nginx writes temp files here (client_body_temp, proxy_temp, etc.)
    (runtime_dir(root) / "temp").mkdir(parents=True, exist_ok=True)


def metadata_path(root: Path, service_name: str) -> Path:
    return services_dir(root) / f"{service_name}.json"


def is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        if os.name == "nt":
            result = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True, check=False)
            return str(pid) in result.stdout
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_metadata(root: Path, service_name: str) -> dict[str, Any] | None:
    path = metadata_path(root, service_name)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_metadata(root: Path, service_name: str, payload: dict[str, Any]) -> None:
    with metadata_path(root, service_name).open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def remove_metadata(root: Path, service_name: str) -> None:
    path = metadata_path(root, service_name)
    if path.exists():
        path.unlink()


def launch_detached(root: Path, service_name: str, command: list[str], env: dict[str, str] | None = None) -> int:
    ensure_runtime_dirs(root)
    log_path = logs_dir(root) / f"{service_name}.log"
    with log_path.open("ab") as log_handle:
        kwargs: dict[str, Any] = {
            "stdout": log_handle,
            "stderr": subprocess.STDOUT,
            "stdin": subprocess.DEVNULL,
            "cwd": str(root),
        }
        if env is not None:
            kwargs["env"] = env
        if os.name == "nt":
            kwargs["creationflags"] = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
        else:
            kwargs["start_new_session"] = True
        process = subprocess.Popen(command, **kwargs)
    write_metadata(root, service_name, {"pid": process.pid, "command": command, "log_path": str(log_path)})
    return process.pid


def stop_service(root: Path, service_name: str) -> bool:
    metadata = read_metadata(root, service_name)
    if not metadata:
        return False
    pid = int(metadata.get("pid", 0))
    if is_pid_running(pid):
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False)
        else:
            os.kill(pid, signal.SIGTERM)
    remove_metadata(root, service_name)
    return True


def llama_swap_command(root: Path, runtime: LlamaSwapRuntime) -> list[str]:
    config_path = str((root / runtime.generated_config_path).resolve())
    return [
        runtime.executable,
        "--config",
        config_path,
        "--listen",
        f"{runtime.host}:{runtime.port}",
        *runtime.extra_args,
    ]


def litellm_command(root: Path, runtime: LiteLLMRuntime) -> list[str]:
    config_path = str((root / runtime.generated_config_path).resolve())
    return [
        _resolve_exe(runtime.executable),
        "--config",
        config_path,
        "--host",
        runtime.host,
        "--port",
        str(runtime.port),
        *runtime.extra_args,
    ]


def start_llama_swap(root: Path) -> None:
    stack = load_stack_config(root)
    write_generated_configs(root)
    existing = read_metadata(root, "llama-swap")
    if existing and is_pid_running(int(existing.get("pid", 0))):
        return
    launch_detached(root, "llama-swap", llama_swap_command(root, stack.llama_swap))
    urls = [f"http://{stack.llama_swap.host}:{stack.llama_swap.port}{path}" for path in stack.llama_swap.health_paths]
    wait_for_any(urls, timeout=300.0, interval=3.0)


def start_gateway(root: Path) -> None:
    stack = load_stack_config(root)
    write_generated_configs(root)
    existing = read_metadata(root, "gateway")
    if existing and is_pid_running(int(existing.get("pid", 0))):
        return
    gateway_env = os.environ.copy()
    gateway_env.pop("DEBUG", None)
    gateway_env.setdefault("PYTHONIOENCODING", "utf-8")
    launch_detached(root, "gateway", litellm_command(root, stack.litellm), env=gateway_env)
    headers = {}
    if stack.litellm.master_key_env in os.environ:
        headers["Authorization"] = f"Bearer {os.environ[stack.litellm.master_key_env]}"
    urls = [f"http://{stack.litellm.host}:{stack.litellm.port}{path}" for path in stack.litellm.health_paths]
    wait_for_any(urls, headers=headers, timeout=180.0, interval=3.0)


def stop_llama_swap(root: Path) -> None:
    stop_service(root, "llama-swap")


def stop_gateway(root: Path) -> None:
    stop_service(root, "gateway")


def _nginx_supports_e_flag(exe: str) -> bool:
    """Return True if the nginx binary supports the -e <errorlog> flag (added in 1.19.5)."""
    import re
    try:
        result = subprocess.run([exe, "-v"], capture_output=True, text=True, check=False)
        # nginx -v writes to stderr: "nginx version: nginx/1.18.0"
        output = result.stderr + result.stdout
        m = re.search(r"nginx/(\d+)\.(\d+)", output)
        if m:
            major, minor = int(m.group(1)), int(m.group(2))
            return (major, minor) >= (1, 19)
    except Exception:
        pass
    return False


def nginx_command(root: Path, runtime: NginxRuntime) -> list[str]:
    exe = _resolve_exe(runtime.executable)
    config_path = str((root / runtime.config_path).resolve())
    cmd = [exe, "-c", config_path, "-p", str(root)]
    if _nginx_supports_e_flag(exe):
        error_log = str((root / ".runtime" / "logs" / "nginx-error.log").resolve())
        cmd += ["-e", error_log]
    return cmd


def nginx_stop_command(root: Path, runtime: NginxRuntime) -> list[str]:
    exe = _resolve_exe(runtime.executable)
    config_path = str((root / runtime.config_path).resolve())
    cmd = [exe, "-c", config_path, "-p", str(root)]
    if _nginx_supports_e_flag(exe):
        error_log = str((root / ".runtime" / "logs" / "nginx-error.log").resolve())
        cmd += ["-e", error_log]
    cmd += ["-s", "stop"]
    return cmd


def start_nginx(root: Path) -> None:
    stack = load_stack_config(root)
    if not stack.nginx.enabled:
        return
    write_generated_configs(root)
    ensure_runtime_dirs(root)
    existing = read_metadata(root, "nginx")
    if existing and is_pid_running(int(existing.get("pid", 0))):
        return
    pid = launch_detached(root, "nginx", nginx_command(root, stack.nginx))
    urls = [f"http://{stack.nginx.host}:{stack.nginx.port}{path}" for path in stack.nginx.health_paths]
    try:
        wait_for_any(urls, timeout=30.0, interval=1.0)
    except TimeoutError:
        pass  # nginx may be up but upstream not ready; PID is tracked


def stop_nginx(root: Path) -> None:
    stack = load_stack_config(root)
    if stack.nginx.enabled:
        subprocess.run(nginx_stop_command(root, stack.nginx), check=False, capture_output=True)
    stop_service(root, "nginx")


def print_status(root: Path) -> None:
    services = ["llama-swap", "gateway", "nginx"]
    statuses = []
    for service_name in services:
        metadata = read_metadata(root, service_name)
        statuses.append(
            {
                "service": service_name,
                "running": bool(metadata and is_pid_running(int(metadata.get("pid", 0)))),
                "metadata": metadata,
            }
        )
    print(json.dumps(statuses, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage a llama-swap backend and LiteLLM gateway.")
    parser.add_argument("--root", default=".", help="Repository root")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("generate-configs", help="Generate llama-swap, LiteLLM, and MCP client config")
    subparsers.add_parser("start-llama-swap", help="Start llama-swap")
    subparsers.add_parser("stop-llama-swap", help="Stop llama-swap")
    subparsers.add_parser("start-backends", help="Compatibility alias for start-llama-swap")
    subparsers.add_parser("stop-backends", help="Compatibility alias for stop-llama-swap")
    subparsers.add_parser("start-gateway", help="Start the LiteLLM gateway")
    subparsers.add_parser("stop-gateway", help="Stop the LiteLLM gateway")
    subparsers.add_parser("start-nginx", help="Start nginx reverse proxy (if enabled)")
    subparsers.add_parser("stop-nginx", help="Stop nginx reverse proxy")
    subparsers.add_parser("start-all", help="Start llama-swap and gateway")
    subparsers.add_parser("stop-all", help="Stop gateway and llama-swap")
    subparsers.add_parser("status", help="Show runtime process status")

    args = parser.parse_args()
    root = Path(args.root).resolve()

    try:
        if args.command == "generate-configs":
            for name, path in write_generated_configs(root).items():
                print(f"{name}: {path}")
        elif args.command in {"start-llama-swap", "start-backends"}:
            start_llama_swap(root)
        elif args.command in {"stop-llama-swap", "stop-backends"}:
            stop_llama_swap(root)
        elif args.command == "start-gateway":
            start_gateway(root)
        elif args.command == "stop-gateway":
            stop_gateway(root)
        elif args.command == "start-nginx":
            start_nginx(root)
        elif args.command == "stop-nginx":
            stop_nginx(root)
        elif args.command == "start-all":
            start_llama_swap(root)
            start_gateway(root)
            start_nginx(root)
        elif args.command == "stop-all":
            stop_nginx(root)
            stop_gateway(root)
            stop_llama_swap(root)
        elif args.command == "status":
            print_status(root)
        else:
            parser.error(f"Unsupported command: {args.command}")
    except TimeoutError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
