#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from runtime_config import load_runtime_config
from verify_runtime_payload import verify_payload

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_ROOT = ROOT / "_build" / "runtime"


def copy_tree(source: Path, destination: Path) -> None:
    if source.exists():
        shutil.copytree(source, destination, dirs_exist_ok=True, symlinks=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage the built Linux native runtime for the patched WeasyPrint wheel."
    )
    parser.add_argument("--prefix", type=Path, default=Path("_build/prefix"))
    parser.add_argument("--runtime", type=Path, default=Path("_build/runtime"))
    args = parser.parse_args()

    load_runtime_config()
    prefix = args.prefix if args.prefix.is_absolute() else ROOT / args.prefix
    runtime = args.runtime if args.runtime.is_absolute() else ROOT / args.runtime
    prefix = prefix.resolve()
    runtime = runtime.resolve()

    shutil.rmtree(runtime, ignore_errors=True)
    runtime.mkdir(parents=True, exist_ok=True)

    runtime_lib = runtime / "lib"
    copy_tree(prefix / "lib", runtime_lib)
    copy_tree(prefix / "lib64", runtime_lib)
    copy_tree(prefix / "bin", runtime / "bin")
    copy_tree(prefix / "etc", runtime / "etc")
    copy_tree(prefix / "share", runtime / "share")

    for pattern in (
        "lib/**/*.a",
        "lib/**/*.la",
        "lib/pkgconfig",
        "share/pkgconfig",
        "include",
    ):
        for path in runtime.glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()

    required = verify_payload(runtime, "linux")
    print(f"Verified {len(required)} Linux runtime entry libraries in {runtime}")


if __name__ == "__main__":
    main()
