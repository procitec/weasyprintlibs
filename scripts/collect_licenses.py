#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from license_bundle import (
        collect_linux,
        collect_macos,
        collect_windows,
        reset_directory,
        write_bundle,
    )
except ModuleNotFoundError:
    from scripts.license_bundle import (
        collect_linux,
        collect_macos,
        collect_windows,
        reset_directory,
        write_bundle,
    )

ROOT = Path(__file__).resolve().parents[1]


def detected_platform() -> str:
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    raise RuntimeError(f"Unsupported host platform: {sys.platform}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect exact third-party license texts for the staged native runtime."
    )
    parser.add_argument("--platform", choices=("linux", "windows", "macos"))
    parser.add_argument("--platform-tag", required=True)
    parser.add_argument("--profile", default="x86_64")
    parser.add_argument("--runtime", type=Path, default=Path("_build/runtime"))
    parser.add_argument("--output", type=Path, default=Path("_build/licenses"))
    parser.add_argument("--archive", type=Path)
    parser.add_argument(
        "--provenance",
        type=Path,
        default=Path("_build/runtime-provenance.json"),
    )
    args = parser.parse_args()

    platform_name = args.platform or detected_platform()
    runtime_root = args.runtime if args.runtime.is_absolute() else ROOT / args.runtime
    output = args.output if args.output.is_absolute() else ROOT / args.output
    archive = None if args.archive is None else (
        args.archive if args.archive.is_absolute() else ROOT / args.archive
    )
    provenance = args.provenance if args.provenance.is_absolute() else ROOT / args.provenance

    reset_directory(output)
    if platform_name == "linux":
        manifest = collect_linux(
            root=ROOT,
            runtime_root=runtime_root,
            output=output,
            platform_tag=args.platform_tag,
        )
    elif platform_name == "windows":
        manifest = collect_windows(
            root=ROOT,
            runtime_root=runtime_root,
            output=output,
            platform_tag=args.platform_tag,
            profile=args.profile,
        )
    else:
        manifest = collect_macos(
            root=ROOT,
            runtime_root=runtime_root,
            output=output,
            platform_tag=args.platform_tag,
            provenance_path=provenance,
        )

    write_bundle(root=ROOT, output=output, manifest=manifest, archive_path=archive)
    print(f"Collected {len(manifest['components'])} third-party license records in {output}")
    if archive is not None:
        print(f"Created release license archive: {archive}")


if __name__ == "__main__":
    main()
