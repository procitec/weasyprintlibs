#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def is_elf(path: Path) -> bool:
    try:
        return path.read_bytes()[:4] == b"\x7fELF"
    except OSError:
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("src/weasyprint_libs/lib"))
    args = parser.parse_args()
    root = args.root.resolve()
    for path in root.rglob("*"):
        if path.is_file() and is_elf(path):
            subprocess.run(["patchelf", "--set-rpath", "$ORIGIN", str(path)], check=True)


if __name__ == "__main__":
    main()
