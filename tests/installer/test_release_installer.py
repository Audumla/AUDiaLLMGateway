import json
from pathlib import Path

import yaml

from src.installer.release_installer import (
    build_toolchain_env,
    _install_one_llama_cpp_profile,
    ensure_local_rocm_sdk,
    ensure_local_vulkan_sdk,
    find_release_asset,
    resolve_component_selection,
    resolve_llama_cpp_profile,
    vulkan_sdk_build_env,
)
from src.launcher.config_loader import validate_layered_configs


def test_resolve_component_selection_includes_required_and_defaults() -> None:
    manifest = {
        "components": {
            "python_runtime": {"required": True, "default_enabled": True},
            "gateway_python_deps": {"required": True, "default_enabled": True},
            "llama_cpp": {"required": True, "default_enabled": True},
            "nginx": {"required": False, "default_enabled": False},
        }
    }
    selected = resolve_component_selection(manifest, ["nginx"])
    assert selected == ["python_runtime", "gateway_python_deps", "llama_cpp", "nginx"]


def test_find_release_asset_matches_all_tokens() -> None:
    metadata = {
        "assets": [
            {"name": "llama-b9999-bin-win-vulkan-x64.zip", "browser_download_url": "https://example.invalid/vulkan.zip"},
            {"name": "llama-b9999-bin-win-cpu-x64.zip", "browser_download_url": "https://example.invalid/cpu.zip"},
        ]
    }
    asset = find_release_asset(metadata, ["win", "vulkan", "x64"])
    assert asset["browser_download_url"] == "https://example.invalid/vulkan.zip"


def test_resolve_llama_cpp_profile_uses_platform_default() -> None:
    settings = {
        "selected_profile": "auto",
        "default_profiles": {
            "windows": "windows-vulkan",
            "linux": "linux-rocm",
            "macos": "macos-metal",
        },
        "profiles": {
            "windows-vulkan": {
                "platform": "windows",
                "backend": "vulkan",
                "asset_match_tokens": ["win", "vulkan", "x64"],
            },
            "linux-rocm": {
                "platform": "linux",
                "backend": "rocm",
                "asset_match_tokens": ["linux", "rocm", "x64"],
            },
            "macos-metal": {
                "platform": "macos",
                "backend": "metal",
                "asset_match_tokens": ["macos", "metal"],
            },
        },
    }

    profile_name, profile = resolve_llama_cpp_profile(settings, "linux")
    assert profile_name == "linux-rocm"
    assert profile["backend"] == "rocm"


def test_resolve_llama_cpp_profile_rejects_wrong_platform() -> None:
    settings = {
        "selected_profile": "windows-vulkan",
        "profiles": {
            "windows-vulkan": {
                "platform": "windows",
                "backend": "vulkan",
                "asset_match_tokens": ["win", "vulkan", "x64"],
            }
        },
    }

    try:
        resolve_llama_cpp_profile(settings, "macos")
    except RuntimeError as exc:
        assert "targets platform 'windows'" in str(exc)
    else:
        raise AssertionError("Expected wrong-platform llama.cpp profile selection to fail")


def test_validate_layered_configs_reports_type_conflicts(tmp_path: Path) -> None:
    for rel_path, payload in {
        "config/project/stack.base.yaml": {
            "models": {
                "project_config_path": "config/project/models.base.yaml",
                "local_override_path": "config/local/models.override.yaml",
            }
        },
        "config/local/stack.override.yaml": {"models": ["bad-type"]},
        "config/project/llama-swap.base.yaml": {"models": {}},
        "config/local/llama-swap.override.yaml": {"models": []},
        "config/project/models.base.yaml": {"model_profiles": {}},
        "config/local/models.override.yaml": {"model_profiles": []},
        "config/project/backend-runtime.base.yaml": {"variants": {}},
        "config/local/backend-runtime.override.yaml": {"variants": []},
        "config/project/mcp.base.yaml": {"servers": []},
        "config/local/mcp.override.yaml": {"servers": {"bad": "type"}},
    }.items():
        target = tmp_path / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(yaml.safe_dump(payload), encoding="utf-8")

    report = validate_layered_configs(tmp_path)
    assert "models" in report["type_conflicts"]["stack"]
    assert "models" in report["type_conflicts"]["llama_swap"]
    assert "model_profiles" in report["type_conflicts"]["models"]
    assert "variants" in report["type_conflicts"]["backend_runtime"]
    assert "servers" in report["type_conflicts"]["mcp"]


def test_install_one_llama_cpp_profile_supports_git_sources(tmp_path: Path, monkeypatch) -> None:
    created_files: dict[str, Path] = {}

    def fake_run_command(command, cwd=None):
        if command[:2] == ["git", "init"]:
            source_dir = Path(command[-1])
            source_dir.mkdir(parents=True, exist_ok=True)
        elif command[:4] == ["git", "-C", str(Path(command[2])), "remote"]:
            return
        elif command[:4] == ["git", "-C", str(Path(command[2])), "fetch"]:
            source_dir = Path(command[2])
            build_dir = source_dir / "build" / "Release"
            build_dir.mkdir(parents=True, exist_ok=True)
            exe_path = build_dir / "llama-server.exe"
            dll_path = build_dir / "ggml.dll"
            exe_path.write_text("binary", encoding="utf-8")
            dll_path.write_text("library", encoding="utf-8")
            created_files["exe"] = exe_path
            created_files["dll"] = dll_path
        elif command[:4] == ["git", "-C", str(Path(command[2])), "checkout"]:
            return
        else:
            raise AssertionError(f"Unexpected command: {command}")

    def fake_run_shell_command(command, cwd=None, env=None):
        assert "cmake" in command
        assert cwd is not None
        assert env is not None
        assert env["CMAKE_BUILD_PARALLEL_LEVEL"] == "2"

    monkeypatch.setattr("src.installer.release_installer.run_command", fake_run_command)
    monkeypatch.setattr("src.installer.release_installer.run_shell_command", fake_run_shell_command)
    monkeypatch.setattr("src.installer.release_installer.shutil.which", lambda name: "git" if name == "git" else None)

    result = _install_one_llama_cpp_profile(
        tmp_path,
        {
            "install_root": "tools/llama.cpp",
            "executable_names": {"windows": "llama-server.exe"},
            "copy_sidecar_to_binary_dir": True,
        },
        "windows-vulkan-turboquant",
        {
            "backend": "vulkan",
            "version": "8590cbff961dbaf1d3a9793fd11d402e248869b9",
            "source_type": "git",
            "git_url": "https://example.invalid/turboquant.git",
            "git_ref": "feature/turboquant-kv-cache",
            "git_commit": "8590cbff961dbaf1d3a9793fd11d402e248869b9",
            "configure_command": "cmake -S . -B build",
            "build_command": "cmake --build build --config Release --parallel",
            "binary_glob": "build/**/llama-server.exe",
            "library_glob": ["build/**/*.dll"],
            "build_env": {"CMAKE_BUILD_PARALLEL_LEVEL": 2},
        },
        "windows",
    )

    assert result["provider"] == "git"
    assert result["version"] == "8590cbff961dbaf1d3a9793fd11d402e248869b9"
    assert result["git_ref"] == "feature/turboquant-kv-cache"
    assert result["git_commit"] == "8590cbff961dbaf1d3a9793fd11d402e248869b9"
    assert result["executable_path"].endswith(
        "tools\\llama.cpp\\8590cbff961dbaf1d3a9793fd11d402e248869b9-vulkan\\bin\\llama-server.exe"
    )
    assert any(path.endswith("ggml.dll") for path in result["copied_sidecars"])


def test_install_one_llama_cpp_profile_reuses_matching_install_state(tmp_path: Path, monkeypatch) -> None:
    install_dir = tmp_path / "tools" / "llama.cpp" / "8590cbff961dbaf1d3a9793fd11d402e248869b9-vulkan"
    executable = install_dir / "bin" / "llama-server.exe"
    executable.parent.mkdir(parents=True, exist_ok=True)
    executable.write_text("cached", encoding="utf-8")

    cached_result = {
        "system": "windows",
        "provider": "git",
        "source_type": "git",
        "profile": "windows-vulkan-turboquant",
        "version": "8590cbff961dbaf1d3a9793fd11d402e248869b9",
        "backend": "vulkan",
        "install_dir": str(install_dir),
        "asset_name": "",
        "executable_path": str(executable),
        "copied_sidecars": [],
        "download_url": "",
        "git_url": "https://example.invalid/turboquant.git",
        "git_ref": "feature/turboquant-kv-cache",
        "git_commit": "8590cbff961dbaf1d3a9793fd11d402e248869b9",
        "configure_command": "cmake -S . -B build",
        "build_command": "cmake --build build --config Release --parallel",
        "required_toolchains": [],
        "toolchains": [],
    }
    state = {
        "component_results": {
            "llama_cpp": {
                **cached_result,
                "variants": {
                    "windows-vulkan-turboquant": cached_result,
                },
            }
        }
    }
    state_path = tmp_path / "state" / "install-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    monkeypatch.setattr("src.installer.release_installer.shutil.which", lambda name: "git" if name == "git" else None)
    monkeypatch.setattr("src.installer.release_installer.run_command", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("run_command should not be called")))
    monkeypatch.setattr("src.installer.release_installer.run_shell_command", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("run_shell_command should not be called")))

    result = _install_one_llama_cpp_profile(
        tmp_path,
        {
            "install_root": "tools/llama.cpp",
            "executable_names": {"windows": "llama-server.exe"},
            "copy_sidecar_to_binary_dir": True,
        },
        "windows-vulkan-turboquant",
        {
            "backend": "vulkan",
            "version": "8590cbff961dbaf1d3a9793fd11d402e248869b9",
            "source_type": "git",
            "git_url": "https://example.invalid/turboquant.git",
            "git_ref": "feature/turboquant-kv-cache",
            "git_commit": "8590cbff961dbaf1d3a9793fd11d402e248869b9",
            "configure_command": "cmake -S . -B build",
            "build_command": "cmake --build build --config Release --parallel",
            "binary_glob": "build/**/llama-server.exe",
            "library_glob": ["build/**/*.dll"],
        },
        "windows",
    )

    assert result["cache_hit"] is True
    assert result["executable_path"] == str(executable)


def test_install_one_llama_cpp_profile_reuses_existing_local_release_install_without_network(
    tmp_path: Path, monkeypatch
) -> None:
    install_dir = tmp_path / "tools" / "llama.cpp" / "b8763-vulkan"
    executable = install_dir / "bin" / "llama-server.exe"
    executable.parent.mkdir(parents=True, exist_ok=True)
    executable.write_text("cached", encoding="utf-8")

    monkeypatch.setattr("src.installer.release_installer.get_release_metadata", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network should not be used")))
    monkeypatch.setattr("src.installer.release_installer.shutil.which", lambda name: "git" if name == "git" else None)

    result = _install_one_llama_cpp_profile(
        tmp_path,
        {
            "install_root": "tools/llama.cpp",
            "executable_names": {"windows": "llama-server.exe"},
            "copy_sidecar_to_binary_dir": True,
        },
        "windows-vulkan",
        {
            "backend": "vulkan",
            "version": "b8763",
            "source_type": "github_release",
            "repo_owner": "ggml-org",
            "repo_name": "llama.cpp",
            "asset_match_tokens": ["win", "vulkan"],
        },
        "windows",
    )

    assert result["cache_hit"] is True
    assert result["version"] == "b8763"
    assert result["install_dir"] == str(install_dir)
    assert result["executable_path"] == str(executable)


def test_ensure_local_vulkan_sdk_copies_from_env_source(tmp_path: Path, monkeypatch) -> None:
    source_root = tmp_path / "source-sdk"
    (source_root / "Include" / "vulkan").mkdir(parents=True)
    (source_root / "Lib").mkdir(parents=True)
    (source_root / "Bin").mkdir(parents=True)
    (source_root / "Include" / "vulkan" / "vulkan.h").write_text("header", encoding="utf-8")
    (source_root / "Lib" / "vulkan-1.lib").write_text("lib", encoding="utf-8")
    (source_root / "Bin" / "glslc.exe").write_text("exe", encoding="utf-8")
    monkeypatch.setenv("AUDIA_VULKAN_SDK_SOURCE", str(source_root))

    details = ensure_local_vulkan_sdk(
        tmp_path,
        {"vulkan_sdk_root": "toolchains/vulkan-sdk/windows"},
        "windows",
    )

    assert str(details["sdk_root"]).endswith("toolchains\\vulkan-sdk\\windows")
    assert details["glslc_path"].exists()


def test_vulkan_sdk_build_env_uses_local_toolchain_root(tmp_path: Path) -> None:
    sdk_root = tmp_path / "toolchains" / "vulkan-sdk" / "windows"
    (sdk_root / "Include" / "vulkan").mkdir(parents=True)
    (sdk_root / "Lib").mkdir(parents=True)
    (sdk_root / "Bin").mkdir(parents=True)
    (sdk_root / "Include" / "vulkan" / "vulkan.h").write_text("header", encoding="utf-8")
    (sdk_root / "Lib" / "vulkan-1.lib").write_text("lib", encoding="utf-8")
    (sdk_root / "Bin" / "glslc.exe").write_text("exe", encoding="utf-8")

    env, details = vulkan_sdk_build_env(
        tmp_path,
        {"vulkan_sdk_root": "toolchains/vulkan-sdk/windows"},
        "windows",
    )

    assert env["VULKAN_SDK"].endswith("toolchains\\vulkan-sdk\\windows")
    assert env["Vulkan_LIBRARY"].endswith("Lib\\vulkan-1.lib")
    assert details["valid"] is True


def test_build_toolchain_env_uses_declared_rocm_sdk_root(tmp_path: Path) -> None:
    sdk_root = tmp_path / "toolchains" / "rocm-sdk" / "windows"
    (sdk_root / "lib" / "cmake" / "hip").mkdir(parents=True)
    (sdk_root / "lib" / "cmake" / "hip" / "hipConfig.cmake").write_text("hip", encoding="utf-8")
    (sdk_root / "bin").mkdir(parents=True)

    env, details = build_toolchain_env(
        tmp_path,
        {
            "required_toolchains": ["rocm_sdk"],
            "rocm_sdk_root": "toolchains/rocm-sdk/windows",
        },
        "windows",
    )

    assert env["ROCM_PATH"].endswith("toolchains\\rocm-sdk\\windows")
    assert env["HIP_PATH"].endswith("toolchains\\rocm-sdk\\windows")
    assert env["hip_DIR"].endswith("lib\\cmake\\hip")
    assert details[0]["kind"] == "rocm_sdk"
    assert details[0]["valid"] is True


def test_ensure_local_rocm_sdk_copies_from_env_source(tmp_path: Path, monkeypatch) -> None:
    source_root = tmp_path / "source-sdk"
    (source_root / "bin").mkdir(parents=True)
    (source_root / "include").mkdir(parents=True)
    (source_root / "lib" / "cmake" / "hip").mkdir(parents=True)
    (source_root / "lib" / "cmake" / "hip" / "hipConfig.cmake").write_text("hip", encoding="utf-8")

    monkeypatch.setenv("ROCM_PATH", str(source_root))

    details = ensure_local_rocm_sdk(
        tmp_path,
        {"rocm_sdk_root": "toolchains/rocm-sdk/windows"},
        "windows",
    )

    assert str(details["sdk_root"]).endswith("toolchains\\rocm-sdk\\windows")
    assert details["hip_config"].exists()


def test_ensure_models_uses_local_source_directory_when_available(tmp_path: Path, monkeypatch) -> None:
    from src.installer.release_installer import ensure_models

    source_root = tmp_path / "mounted-models"
    (source_root / "Qwen3.5-27B").mkdir(parents=True)
    model_source = source_root / "Qwen3.5-27B" / "Qwen3.5-27B-Q6_K.gguf"
    model_source.write_text("local model", encoding="utf-8")
    monkeypatch.setenv("AUDIA_MODEL_SOURCE_ROOT", str(source_root))

    (tmp_path / "config" / "project").mkdir(parents=True)
    (tmp_path / "config" / "local").mkdir(parents=True)
    (tmp_path / "config" / "project" / "stack.base.yaml").write_text(
        """
project:
  installer:
    state_path: state/install-state.json
install:
  venv_path: .venv
  python_min_version: "3.11"
network:
  backend_bind_host: 127.0.0.1
  base_path: /audia/llmgateway
  services:
    llama_swap:
      host: 127.0.0.1
      port: 41080
    litellm:
      host: 127.0.0.1
      port: 4000
    vllm:
      host: 127.0.0.1
      port: 8000
    nginx:
      port: 8080
models:
  project_config_path: config/project/models.base.yaml
  local_override_path: config/local/models.override.yaml
backend_runtime:
  project_config_path: config/project/backend-runtime.base.yaml
  local_override_path: config/local/backend-runtime.override.yaml
backend_support:
  project_config_path: config/project/backend-support.base.yaml
  local_override_path: config/local/backend-support.override.yaml
component_settings:
  models:
    install_root: models
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "config" / "project" / "models.base.yaml").write_text(
        """
model_profiles:
  qwen27_fast:
    mode: chat
    artifacts:
      source_type: auto
      source_path: ${AUDIA_MODEL_SOURCE_ROOT:-}
      model_file: Qwen3.5-27B/Qwen3.5-27B-Q6_K.gguf
      model_url: https://example.invalid/model.gguf
    deployments:
      llama:
        label: local/qwen27_fast
""".strip(),
        encoding="utf-8",
    )
    for rel in ["stack.override.yaml", "models.override.yaml", "backend-runtime.override.yaml", "backend-support.override.yaml"]:
        (tmp_path / "config" / "local" / rel).write_text("{}", encoding="utf-8")

    details = ensure_models(tmp_path)

    assert details["models"]["local/qwen27_fast"]["source_type"] == "auto"
    assert Path(details["models"]["local/qwen27_fast"]["model_path"]).read_text(encoding="utf-8") == "local model"
