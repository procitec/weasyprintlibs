#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from runtime_config import load_runtime_config

PE_MACHINES = {
    "x86_64": 0x8664,
    "arm64": 0xAA64,
}
ELF_MACHINES = {
    "x86_64": 62,
    "arm64": 183,
    "aarch64": 183,
}


def _require_files(directory: Path, names: list[str]) -> list[Path]:
    missing = [directory / name for name in names if not (directory / name).is_file()]
    if missing:
        formatted = "\n".join(f"  - {path}" for path in missing)
        raise RuntimeError(f"Required runtime libraries are missing:\n{formatted}")
    return [directory / name for name in names]


def _read_pe_machine(path: Path) -> int:
    data = path.read_bytes()
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise RuntimeError(f"Not a PE file: {path}")
    pe_offset = int.from_bytes(data[0x3C:0x40], "little")
    if len(data) < pe_offset + 6 or data[pe_offset : pe_offset + 4] != b"PE\0\0":
        raise RuntimeError(f"Invalid PE header: {path}")
    return int.from_bytes(data[pe_offset + 4 : pe_offset + 6], "little")


def _read_elf_machine(path: Path) -> int:
    data = path.read_bytes()[:20]
    if len(data) < 20 or data[:4] != b"\x7fELF":
        raise RuntimeError(f"Not an ELF file: {path}")
    endian = data[5]
    if endian == 1:
        byteorder = "little"
    elif endian == 2:
        byteorder = "big"
    else:
        raise RuntimeError(f"Invalid ELF byte order in {path}")
    return int.from_bytes(data[18:20], byteorder)


def _verify_macos_architecture(paths: list[Path], architecture: str) -> None:
    lipo = shutil.which("lipo")
    if lipo is None:
        if sys.platform == "darwin":
            raise RuntimeError("lipo is required for macOS architecture verification")
        return

    for path in paths:
        result = subprocess.run(
            [lipo, "-archs", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        architectures = result.stdout.split()
        if architecture not in architectures:
            raise RuntimeError(
                f"{path.name} has architectures {architectures}, expected {architecture}"
            )


def _verify_architecture(platform: str, paths: list[Path], architecture: str) -> None:
    if platform == "windows":
        expected = PE_MACHINES.get(architecture)
        if expected is None:
            raise RuntimeError(f"Unsupported Windows architecture: {architecture}")
        for path in paths:
            actual = _read_pe_machine(path)
            if actual != expected:
                raise RuntimeError(
                    f"{path.name} has PE machine 0x{actual:04x}, expected 0x{expected:04x}"
                )
        return

    if platform == "linux":
        expected = ELF_MACHINES.get(architecture)
        if expected is None:
            raise RuntimeError(f"Unsupported Linux architecture: {architecture}")
        for path in paths:
            actual = _read_elf_machine(path)
            if actual != expected:
                raise RuntimeError(f"{path.name} has ELF machine {actual}, expected {expected}")
        return

    if platform == "macos":
        _verify_macos_architecture(paths, architecture)
        return

    raise RuntimeError(f"Unsupported platform: {platform}")


def verify_payload(
    root: Path,
    platform: str,
    *,
    architecture: str | None = None,
) -> list[Path]:
    config = load_runtime_config()
    section = config[platform]
    library_dir = root / section["directory"]
    paths = _require_files(library_dir, section["preload"])

    fonts_conf = root / "etc" / "fonts" / "fonts.conf"
    if not fonts_conf.is_file():
        raise RuntimeError(f"Bundled Fontconfig configuration is missing: {fonts_conf}")

    if architecture:
        _verify_architecture(platform, paths, architecture)

    return paths


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify the staged native runtime against config/runtime-libraries.toml."
    )
    parser.add_argument("--root", type=Path, default=Path("_build/runtime"))
    parser.add_argument("--platform", choices=("windows", "linux", "macos"), required=True)
    parser.add_argument("--architecture")
    args = parser.parse_args()

    root = args.root.resolve()
    paths = verify_payload(root, args.platform, architecture=args.architecture)
    suffix = f" for {args.architecture}" if args.architecture else ""
    print(f"Verified {len(paths)} {args.platform} runtime entry libraries{suffix} in {root}")


if __name__ == "__main__":
    main()
