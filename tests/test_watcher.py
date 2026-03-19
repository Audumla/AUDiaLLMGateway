from src.launcher import watcher


def test_watcher_detects_expected_config_files() -> None:
    assert watcher._is_watched_config_path("/app/config/local/stack.override.yaml")
    assert watcher._is_watched_config_path("/app/config/local/models.override.yml")
    assert watcher._is_watched_config_path("/app/config/local/env")
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
