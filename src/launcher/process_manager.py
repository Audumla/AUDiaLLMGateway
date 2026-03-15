from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

from .config_loader import LiteLLMRuntime, LlamaSwapRuntime, load_stack_config, write_generated_configs
from .health import wait_for_any


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


def launch_detached(root: Path, service_name: str, command: list[str]) -> int:
    ensure_runtime_dirs(root)
    log_path = logs_dir(root) / f"{service_name}.log"
    with log_path.open("ab") as log_handle:
        kwargs: dict[str, Any] = {
            "stdout": log_handle,
            "stderr": subprocess.STDOUT,
            "stdin": subprocess.DEVNULL,
            "cwd": str(root),
        }
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
        runtime.executable,
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
    launch_detached(root, "gateway", litellm_command(root, stack.litellm))
    headers = {}
    if stack.litellm.master_key_env in os.environ:
        headers["Authorization"] = f"Bearer {os.environ[stack.litellm.master_key_env]}"
    urls = [f"http://{stack.litellm.host}:{stack.litellm.port}{path}" for path in stack.litellm.health_paths]
    wait_for_any(urls, headers=headers, timeout=180.0, interval=3.0)


def stop_llama_swap(root: Path) -> None:
    stop_service(root, "llama-swap")


def stop_gateway(root: Path) -> None:
    stop_service(root, "gateway")


def print_status(root: Path) -> None:
    services = ["llama-swap", "gateway"]
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
        elif args.command == "start-all":
            start_llama_swap(root)
            start_gateway(root)
        elif args.command == "stop-all":
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
