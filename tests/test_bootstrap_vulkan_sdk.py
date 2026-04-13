from __future__ import annotations

import json
from pathlib import Path

import scripts.bootstrap_vulkan_sdk as bootstrap


def test_bootstrap_vulkan_sdk_copies_from_source_dir(tmp_path: Path, monkeypatch, capsys) -> None:
    source_root = tmp_path / "source-sdk"
    (source_root / "Include" / "vulkan").mkdir(parents=True)
    (source_root / "Lib").mkdir(parents=True)
    (source_root / "Bin").mkdir(parents=True)
    (source_root / "Include" / "vulkan" / "vulkan.h").write_text("header", encoding="utf-8")
    (source_root / "Lib" / "vulkan-1.lib").write_text("lib", encoding="utf-8")
    (source_root / "Bin" / "glslc.exe").write_text("exe", encoding="utf-8")

    sdk_root = tmp_path / "workspace" / "toolchains" / "vulkan-sdk" / "windows"
    monkeypatch.setattr(
        "sys.argv",
        [
            "bootstrap_vulkan_sdk.py",
            "--root",
            str(tmp_path / "workspace"),
            "--sdk-root",
            str(sdk_root),
            "--source-dir",
            str(source_root),
            "--platform",
            "windows",
        ],
    )

    assert bootstrap.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result["mode"] == "copied"
    assert result["sdk_root"] == str(sdk_root)
    assert (sdk_root / "Include" / "vulkan" / "vulkan.h").exists()
    assert (sdk_root / "Lib" / "vulkan-1.lib").exists()
    assert (sdk_root / "Bin" / "glslc.exe").exists()
