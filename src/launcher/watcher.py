from __future__ import annotations

import os
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
    from watchdog.observers.polling import PollingObserver
except ImportError:  # pragma: no cover - exercised in lightweight local test envs
    class FileSystemEventHandler:  # type: ignore[no-redef]
        pass

    Observer = None  # type: ignore[assignment]
    PollingObserver = None  # type: ignore[assignment]


DOCKER_SOCKET_PATH = "/var/run/docker.sock"
GENERATED_PATHS = {
    "llama_swap": "config/generated/llama-swap/llama-swap.generated.yaml",
    "litellm": "config/generated/litellm/litellm.config.yaml",
    "vllm": "config/generated/vllm/vllm.config.json",
    "nginx": "config/generated/nginx/nginx.conf",
    "nginx_index": "config/generated/nginx/index.html",
    "mcp_client": "config/generated/mcp/litellm.mcp.client.json",
    "systemd": "config/generated/systemd/audia-gateway.service",
}
WATCHED_SUFFIXES = {".yaml", ".yml", ".json"}
WATCHED_FILENAMES = {"env"}


def _file_hash(path: Path) -> str:
    if not path.exists():
        return ""
    return str(hash(path.read_text(encoding="utf-8")))


def _snapshot_generated(root: Path) -> dict[str, str]:
    return {
        name: _file_hash(root / rel_path)
        for name, rel_path in GENERATED_PATHS.items()
    }


def _changed_outputs(before: dict[str, str], after: dict[str, str]) -> set[str]:
    return {name for name, old_hash in before.items() if after.get(name, "") != old_hash}


def _is_watched_config_path(path: str) -> bool:
    candidate = Path(path)
    return candidate.suffix.lower() in WATCHED_SUFFIXES or candidate.name in WATCHED_FILENAMES


def _observer_class() -> type[Any]:
    watcher_mode = os.getenv("AUDIA_WATCHER_MODE", "").strip().lower()
    if watcher_mode == "observer":
        return Observer
    if watcher_mode == "polling":
        return PollingObserver or Observer
    if os.getenv("AUDIA_DOCKER", "false").lower() == "true":
        return PollingObserver or Observer
    return Observer


@dataclass
class DockerSocketClient:
    socket_path: str = DOCKER_SOCKET_PATH

    def available(self) -> bool:
        return Path(self.socket_path).exists()

    def post(self, request_path: str) -> None:
        if not self.available():
            raise FileNotFoundError(self.socket_path)

        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(self.socket_path)
            request = (
                f"POST {request_path} HTTP/1.1\r\n"
                "Host: docker\r\n"
                "Content-Length: 0\r\n"
                "Connection: close\r\n\r\n"
            )
            client.sendall(request.encode("utf-8"))

            response = b""
            while True:
                chunk = client.recv(4096)
                if not chunk:
                    break
                response += chunk

        status_line = response.split(b"\r\n", 1)[0].decode("utf-8", errors="replace")
        if " 2" not in status_line and " 3" not in status_line:
            raise RuntimeError(f"Docker API request failed: {status_line}")

    def restart_container(self, name: str) -> None:
        self.post(f"/containers/{name}/restart")

    def signal_container(self, name: str, signal_name: str) -> None:
        self.post(f"/containers/{name}/kill?signal={signal_name}")


class ConfigChangeHandler(FileSystemEventHandler):
    def __init__(self, root: Path, debounce_seconds: float = 2.0, startup_grace_seconds: float = 5.0):
        self.root = root
        self.debounce_seconds = debounce_seconds
        self.startup_grace_seconds = startup_grace_seconds
        self.last_run = 0.0
        self.started_at = time.time()
        self.docker = DockerSocketClient()

    def on_any_event(self, event: Any) -> None:
        if event.is_directory or event.event_type == "opened":
            return

        src_path = getattr(event, "src_path", "")
        dest_path = getattr(event, "dest_path", "")
        changed_paths = [path for path in (src_path, dest_path) if path]
        if not any(_is_watched_config_path(path) for path in changed_paths):
            return

        now = time.time()
        if now - self.started_at < self.startup_grace_seconds:
            return
        if now - self.last_run < self.debounce_seconds:
            return
        self.last_run = now

        print(f"Detected config change: {', '.join(changed_paths)}", flush=True)
        self._regenerate_and_reload(changed_paths)

    def _regenerate_and_reload(self, changed_paths: list[str]) -> None:
        before = _snapshot_generated(self.root)
        try:
            subprocess.run(
                ["python3", "-m", "src.launcher.process_manager", "--root", str(self.root), "generate-configs"],
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            print(
                "Config regeneration failed; keeping watcher alive for subsequent changes. "
                f"changed_paths={changed_paths} exit_code={exc.returncode}",
                flush=True,
            )
            return
        after = _snapshot_generated(self.root)
        changed_outputs = _changed_outputs(before, after)

        print(f"Generated outputs changed: {sorted(changed_outputs)}", flush=True)

        changed_names = {Path(path).name for path in changed_paths}
        should_reload_nginx = bool({"nginx", "nginx_index"} & changed_outputs)
        should_restart_gateway = "litellm" in changed_outputs or "env" in changed_names
        should_restart_vllm = "vllm" in changed_outputs or "env" in changed_names
        if should_reload_nginx:
            self._safe_action("reload nginx", lambda: self.docker.signal_container("audia-nginx", "HUP"))
        if should_restart_gateway:
            self._safe_action("restart gateway", lambda: self.docker.restart_container("audia-gateway"))
        if should_restart_vllm:
            self._safe_action("restart vllm", lambda: self.docker.restart_container("audia-vllm"))

    @staticmethod
    def _safe_action(label: str, action: callable) -> None:
        try:
            print(f"Applying action: {label}", flush=True)
            action()
        except FileNotFoundError:
            print(f"Skipping action '{label}' because Docker socket is unavailable", flush=True)
        except Exception as exc:
            print(f"Action '{label}' failed: {exc}", flush=True)


def main() -> int:
    if Observer is None:
        raise RuntimeError("watchdog is required to run the config watcher")

    root = Path(os.getenv("AUDIA_ROOT", "/app")).resolve()
    config_root = Path(os.getenv("CONFIG_ROOT", root / "config")).resolve()
    print(f"Watcher started. Monitoring {config_root / 'project'} and {config_root / 'local'}", flush=True)

    observer = _observer_class()()
    handler = ConfigChangeHandler(root=root)

    for watch_path in (config_root / "project", config_root / "local"):
        if watch_path.exists():
            observer.schedule(handler, str(watch_path), recursive=False)

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
