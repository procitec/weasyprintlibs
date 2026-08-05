#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import zipfile
from email.parser import Parser
from pathlib import Path


def find_wheel(path: Path) -> Path:
    if path.is_file():
        return path
    wheels = sorted(path.glob("weasyprint-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"Expected exactly one patched WeasyPrint wheel in {path}, got {wheels}")
    return wheels[0]


def verify_wheel(wheel: Path) -> None:
    filename_match = re.fullmatch(
        r"weasyprint-(?P<version>.+)-py3-none-(?P<platform>[^-]+(?:_[^-]+)*)\.whl",
        wheel.name,
    )
    if not filename_match:
        raise RuntimeError(f"Unexpected patched wheel filename: {wheel.name}")
    filename_version = filename_match.group("version")
    platform_tag = filename_match.group("platform")
    if "+bundled." not in filename_version:
        raise RuntimeError(f"Wheel version has no bundled local version: {filename_version}")
    if platform_tag == "any":
        raise RuntimeError("Patched wheel must have a platform-specific tag")

    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
        wheel_names = [name for name in names if name.endswith(".dist-info/WHEEL")]
        record_names = [name for name in names if name.endswith(".dist-info/RECORD")]
        runtime_metadata_names = [
            name for name in names if name.endswith(".dist-info/BUNDLED-RUNTIME.json")
        ]
        if not all(
            len(items) == 1
            for items in (
                metadata_names,
                wheel_names,
                record_names,
                runtime_metadata_names,
            )
        ):
            raise RuntimeError("Wheel metadata layout is incomplete or ambiguous")

        metadata = Parser().parsestr(archive.read(metadata_names[0]).decode("utf-8"))
        if metadata.get("Name", "").lower() != "weasyprint":
            raise RuntimeError(f"Unexpected distribution name: {metadata.get('Name')}")
        if metadata.get("Version") != filename_version:
            raise RuntimeError(
                "Filename/METADATA version mismatch: "
                f"{filename_version} != {metadata.get('Version')}"
            )

        wheel_metadata = archive.read(wheel_names[0]).decode("utf-8")
        if "Root-Is-Purelib: false" not in wheel_metadata:
            raise RuntimeError("Patched wheel still declares Root-Is-Purelib: true")
        if f"Tag: py3-none-{platform_tag}" not in wheel_metadata:
            raise RuntimeError("WHEEL tag does not match the wheel filename")

        runtime_metadata = json.loads(archive.read(runtime_metadata_names[0]))
        if runtime_metadata.get("bundled_version") != filename_version:
            raise RuntimeError("BUNDLED-RUNTIME.json version does not match the wheel")
        if runtime_metadata.get("platform_tag") != platform_tag:
            raise RuntimeError("BUNDLED-RUNTIME.json platform does not match the wheel")

        required = {
            "weasyprint/_weasyprint_libs_loader.py",
            "weasyprint/_weasyprint_libs_config.py",
        }
        missing = sorted(required - names)
        if missing:
            raise RuntimeError(f"Patched wheel is missing bootstrap files: {missing}")
        has_libs = any(name.startswith("weasyprint/_weasyprint_libs/lib/") for name in names)
        has_dlls = any(name.startswith("weasyprint/_weasyprint_libs/bin/") for name in names)
        if not has_libs and not has_dlls:
            raise RuntimeError("Patched wheel contains no native runtime payload")
        if any(name.startswith("weasyprint_libs/") for name in names):
            raise RuntimeError("Legacy standalone package is still present in the wheel")
        if any(name.endswith("weasyprint_libs.pth") for name in names):
            raise RuntimeError("Legacy activation .pth file is still present in the wheel")

        record_rows = list(csv.reader(io.StringIO(archive.read(record_names[0]).decode("utf-8"))))
        recorded = {row[0] for row in record_rows}
        missing_from_record = sorted(names - recorded)
        if missing_from_record:
            raise RuntimeError(f"Wheel files are missing from RECORD: {missing_from_record[:10]}")

    print(f"Verified patched wheel: {wheel}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify a directly patched WeasyPrint wheel.")
    parser.add_argument("path", type=Path, nargs="?", default=Path("dist"))
    args = parser.parse_args()
    verify_wheel(find_wheel(args.path.resolve()))


if __name__ == "__main__":
    main()
