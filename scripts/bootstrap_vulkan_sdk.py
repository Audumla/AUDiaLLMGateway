from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.installer.release_installer import copy_vulkan_sdk_subset, describe_vulkan_sdk, resolve_vulkan_sdk_source


def _normalize_platform_name(value: str | None = None) -> str:
    system = (value or platform.system()).strip().lower()
    if system == "darwin":
        return "macos"
    return system


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create or validate a workspace-local Vulkan SDK cache for sandboxed Vulkan source builds."
    )
    parser.add_argument("--root", default=".", help="Workspace root used to resolve the default sdk root")
    parser.add_argument(
        "--sdk-root",
        default="",
        help="Target local Vulkan SDK root. Defaults to <root>/toolchains/vulkan-sdk/<platform>.",
    )
    parser.add_argument(
        "--source-dir",
        default="",
        help="Existing Vulkan SDK directory to copy from. If omitted, uses AUDIA_VULKAN_SDK_SOURCE or VULKAN_SDK.",
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
    sdk_root = Path(args.sdk_root).resolve() if args.sdk_root else root / "toolchains" / "vulkan-sdk" / platform_name
    existing = describe_vulkan_sdk(sdk_root, platform_name)
    if existing["valid"] and not args.force:
        result = {
            "mode": "existing",
            "platform": platform_name,
            "sdk_root": str(existing["sdk_root"]),
            "include_dir": str(existing["include_dir"]),
            "library_path": str(existing["library_path"]),
            "glslc_path": str(existing["glslc_path"]),
            "bin_dir": str(existing["bin_dir"]),
        }
        print(json.dumps(result, indent=2))
        return 0

    source_root = Path(args.source_dir).resolve() if args.source_dir else resolve_vulkan_sdk_source(platform_name)
    if source_root is None:
        raise SystemExit(
            "No Vulkan SDK source directory was found. Use --source-dir or set AUDIA_VULKAN_SDK_SOURCE / VULKAN_SDK."
        )

    copied = copy_vulkan_sdk_subset(source_root, sdk_root, platform_name)
    result = {
        "mode": "copied",
        "platform": platform_name,
        "source_root": str(source_root),
        "sdk_root": str(copied["sdk_root"]),
        "include_dir": str(copied["include_dir"]),
        "library_path": str(copied["library_path"]),
        "glslc_path": str(copied["glslc_path"]),
        "bin_dir": str(copied["bin_dir"]),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
