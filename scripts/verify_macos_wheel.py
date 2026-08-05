#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

FORBIDDEN_PREFIXES = (
    "/opt/homebrew/",
    "/usr/local/Cellar/",
    "/usr/local/opt/",
)
ALLOWED_ABSOLUTE_PREFIXES = (
    "/System/Library/",
    "/usr/lib/",
)


def run(*args: str) -> str:
    result = subprocess.run(
        args,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def dependencies(path: Path) -> list[str]:
    result: list[str] = []
    for line in run("otool", "-L", str(path)).splitlines()[1:]:
        match = re.match(r"\s*(\S+)\s+\(", line)
        if match:
            result.append(match.group(1))
    return result


def verify_architecture(path: Path, expected_arch: str) -> None:
    output = run("lipo", "-archs", str(path)).split()
    if expected_arch not in output:
        raise RuntimeError(f"{path.name} has architectures {output}, expected {expected_arch}")


def verify_wheel(wheel: Path, expected_arch: str) -> None:
    if sys.platform != "darwin":
        raise RuntimeError("The macOS wheel verifier must run on macOS")

    with tempfile.TemporaryDirectory(prefix="verify-macos-wheel-") as temporary:
        root = Path(temporary)
        with zipfile.ZipFile(wheel) as archive:
            archive.extractall(root)

        libraries = sorted(root.rglob("*.dylib"))
        if not libraries:
            raise RuntimeError(f"Wheel contains no dylibs: {wheel}")

        for library in libraries:
            verify_architecture(library, expected_arch)
            for dependency in dependencies(library):
                if dependency.startswith(FORBIDDEN_PREFIXES):
                    raise RuntimeError(
                        f"Forbidden Homebrew reference in {library.name}: {dependency}"
                    )
                if dependency.startswith("/") and not dependency.startswith(
                    ALLOWED_ABSOLUTE_PREFIXES
                ):
                    raise RuntimeError(
                        f"Unexpected absolute dependency in {library.name}: {dependency}"
                    )
                if not dependency.startswith(("@loader_path/", "/")):
                    raise RuntimeError(f"Unexpected dependency in {library.name}: {dependency}")

        print(f"Verified {len(libraries)} dylibs in {wheel.name} for architecture {expected_arch}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify relocated libraries in a macOS wheel.")
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--arch", required=True, choices=("arm64", "x86_64"))
    args = parser.parse_args()
    verify_wheel(args.wheel.resolve(), args.arch)


if __name__ == "__main__":
    main()
