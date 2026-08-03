#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def copy_tree(source: Path, destination: Path) -> None:
    if source.exists():
        shutil.copytree(source, destination, dirs_exist_ok=True, symlinks=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", type=Path, default=Path("_build/prefix"))
    parser.add_argument("--package", type=Path, default=Path("src/weasyprintlibs_native"))
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    prefix = (root / args.prefix).resolve()
    package = (root / args.package).resolve()
    for name in ("lib", "bin", "etc", "share"):
        shutil.rmtree(package / name, ignore_errors=True)
        copy_tree(prefix / name, package / name)

    # Headers, pkg-config files, static archives, libtool files and executables
    # not needed at runtime are deliberately removed from the Wheel payload.
    for pattern in ("lib/**/*.a", "lib/**/*.la", "lib/pkgconfig", "share/pkgconfig", "include"):
        for path in package.glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()


if __name__ == "__main__":
    main()
