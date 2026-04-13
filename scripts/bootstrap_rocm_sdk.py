from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.installer.release_installer import copy_rocm_sdk_subset, describe_rocm_sdk, resolve_rocm_sdk_source


def _normalize_platform_name(value: str | None = None) -> str:
    system = (value or platform.system()).strip().lower()
    if system == "darwin":
        return "macos"
    return system


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create or validate a workspace-local ROCm SDK cache for sandboxed HIP source builds."
    )
    parser.add_argument("--root", default=".", help="Workspace root used to resolve the default sdk root")
    parser.add_argument(
        "--sdk-root",
        default="",
        help="Target local ROCm SDK root. Defaults to <root>/toolchains/rocm-sdk/<platform>.",
    )
    parser.add_argument(
        "--source-dir",
        default="",
        help="Existing ROCm SDK directory to copy from. If omitted, searches ROCM_PATH / HIP_PATH and common install paths.",
    )
    parser.add_argument(
        "--platform",
        default="",
        help="Target platform layout to validate (windows or linux). Defaults to the current host platform.",
    )
    parser.add_argument("--force", action="store_true", help="Re-copy the source SDK even if the local cache is already valid")
    args = parser.parse_args()

    platform_name = _normalize_platform_name(args.platform)
    root = Path(args.root).resolve()
    sdk_root = Path(args.sdk_root).resolve() if args.sdk_root else root / "toolchains" / "rocm-sdk" / platform_name

    existing = describe_rocm_sdk(sdk_root)
    if existing["valid"] and not args.force:
        result = {
            "mode": "existing",
            "platform": platform_name,
            "sdk_root": str(existing["sdk_root"]),
            "bin_dir": str(existing["bin_dir"]),
            "include_dir": str(existing["include_dir"]),
            "hip_config": str(existing["hip_config"]) if existing.get("hip_config") else None,
        }
        print(json.dumps(result, indent=2))
        return 0

    source_root = Path(args.source_dir).resolve() if args.source_dir else resolve_rocm_sdk_source(platform_name)
    if source_root is None:
        raise SystemExit(
            "No ROCm SDK source directory was found. Use --source-dir or set AUDIA_ROCM_SDK_SOURCE / ROCM_PATH / HIP_PATH."
        )

    copied = copy_rocm_sdk_subset(source_root, sdk_root)
    result = {
        "mode": "copied",
        "platform": platform_name,
        "source_root": str(source_root),
        "sdk_root": str(copied["sdk_root"]),
        "bin_dir": str(copied["bin_dir"]),
        "include_dir": str(copied["include_dir"]),
        "hip_config": str(copied["hip_config"]) if copied.get("hip_config") else None,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
