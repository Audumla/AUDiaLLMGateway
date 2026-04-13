from __future__ import annotations

import json
from pathlib import Path

import scripts.bootstrap_rocm_sdk as bootstrap


def test_bootstrap_rocm_sdk_copies_from_source_dir(tmp_path: Path, monkeypatch, capsys) -> None:
    source_root = tmp_path / "source-sdk"
    (source_root / "bin").mkdir(parents=True)
    (source_root / "include").mkdir(parents=True)
    (source_root / "lib" / "cmake" / "hip").mkdir(parents=True)
    (source_root / "lib" / "cmake" / "hip" / "hipConfig.cmake").write_text("hip", encoding="utf-8")

    sdk_root = tmp_path / "workspace" / "toolchains" / "rocm-sdk" / "windows"
    monkeypatch.setattr(
        "sys.argv",
        [
            "bootstrap_rocm_sdk.py",
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
    assert (sdk_root / "lib" / "cmake" / "hip" / "hipConfig.cmake").exists()
