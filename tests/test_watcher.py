import subprocess
from pathlib import Path

from src.launcher import watcher


def test_watcher_detects_expected_config_files() -> None:
    assert watcher._is_watched_config_path("/app/config/local/stack.override.yaml")
    assert watcher._is_watched_config_path("/app/config/local/models.override.yml")
    assert watcher._is_watched_config_path("/app/config/local/env")
    assert watcher._is_watched_config_path("/app/config/local/env.private")
    assert not watcher._is_watched_config_path("/app/config/generated/nginx/nginx.conf.bak")


def test_changed_outputs_only_returns_modified_entries() -> None:
    before = {"nginx": "a", "litellm": "b", "llama_swap": "c"}
    after = {"nginx": "a", "litellm": "z", "llama_swap": "c"}

    assert watcher._changed_outputs(before, after) == {"litellm"}


def test_watcher_prefers_polling_in_docker(monkeypatch) -> None:
    monkeypatch.delenv("AUDIA_WATCHER_MODE", raising=False)
    monkeypatch.setenv("AUDIA_DOCKER", "true")

    expected = watcher.PollingObserver or watcher.Observer
    assert watcher._observer_class() is expected


def test_regenerate_and_reload_keeps_watcher_alive_on_generate_failure(monkeypatch) -> None:
    handler = watcher.ConfigChangeHandler(root=Path.cwd())
    actions: list[str] = []

    def _raise_called_process_error(*_args, **_kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=["python3"])

    monkeypatch.setattr(watcher.subprocess, "run", _raise_called_process_error)
    monkeypatch.setattr(handler, "_safe_action", lambda label, _action: actions.append(label))

    handler._regenerate_and_reload(["/app/config/local/models.override.yaml"])

    assert actions == []


def test_regenerate_and_reload_applies_expected_actions(monkeypatch) -> None:
    handler = watcher.ConfigChangeHandler(root=Path.cwd())
    actions: list[str] = []

    monkeypatch.setattr(watcher.subprocess, "run", lambda *_args, **_kwargs: None)
    snapshots = [
        {"nginx": "a", "nginx_index": "a", "litellm": "a", "vllm": "a", "llama_swap": "a", "mcp_client": "a", "systemd": "a"},
        {"nginx": "b", "nginx_index": "a", "litellm": "b", "vllm": "a", "llama_swap": "a", "mcp_client": "a", "systemd": "a"},
    ]
    monkeypatch.setattr(watcher, "_snapshot_generated", lambda _root: snapshots.pop(0))
    monkeypatch.setattr(handler, "_safe_action", lambda label, _action: actions.append(label))

    handler._regenerate_and_reload(["/app/config/local/models.override.yaml"])

    assert actions == ["reload nginx", "restart gateway"]


def test_regenerate_and_reload_restarts_gateway_and_vllm_on_env_change(monkeypatch) -> None:
    handler = watcher.ConfigChangeHandler(root=Path.cwd())
    actions: list[str] = []

    monkeypatch.setattr(watcher.subprocess, "run", lambda *_args, **_kwargs: None)
    snapshot = {"nginx": "a", "nginx_index": "a", "litellm": "a", "vllm": "a", "llama_swap": "a", "mcp_client": "a", "systemd": "a"}
    monkeypatch.setattr(watcher, "_snapshot_generated", lambda _root: snapshot)
    monkeypatch.setattr(handler, "_safe_action", lambda label, _action: actions.append(label))

    handler._regenerate_and_reload(["/app/config/local/env"])

    assert actions == ["restart gateway", "restart llama-cpp", "restart vllm"]


def test_regenerate_and_reload_restarts_gateway_and_vllm_on_env_private_change(monkeypatch) -> None:
    handler = watcher.ConfigChangeHandler(root=Path.cwd())
    actions: list[str] = []

    monkeypatch.setattr(watcher.subprocess, "run", lambda *_args, **_kwargs: None)
    snapshot = {"nginx": "a", "nginx_index": "a", "litellm": "a", "vllm": "a", "llama_swap": "a", "mcp_client": "a", "systemd": "a"}
    monkeypatch.setattr(watcher, "_snapshot_generated", lambda _root: snapshot)
    monkeypatch.setattr(handler, "_safe_action", lambda label, _action: actions.append(label))

    handler._regenerate_and_reload(["/app/config/local/env.private"])

    assert actions == ["restart gateway", "restart llama-cpp", "restart vllm"]
