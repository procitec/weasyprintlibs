#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def is_elf(path: Path) -> bool:
    try:
        return path.read_bytes()[:4] == b"\x7fELF"
    except OSError:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Set a relative RPATH on staged ELF libraries.")
    parser.add_argument("root", type=Path, nargs="?", default=Path("_build/runtime/lib"))
    args = parser.parse_args()
    root = args.root if args.root.is_absolute() else ROOT / args.root
    root = root.resolve()
    if not root.is_dir():
        raise RuntimeError(f"Staged Linux library directory is missing: {root}")

    patched = 0
    for path in root.rglob("*"):
        if path.is_file() and is_elf(path):
            subprocess.run(["patchelf", "--set-rpath", "$ORIGIN", str(path)], check=True)
            patched += 1
    print(f"Patched RPATH on {patched} ELF files in {root}")


if __name__ == "__main__":
    main()
