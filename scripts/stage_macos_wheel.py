#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE_ROOT = ROOT / "src" / "weasyprint_libs"

SEED_LIBRARY_PATTERNS = (
    "libpango-1.0*.dylib",
    "libpangoft2-1.0*.dylib",
    "libpangocairo-1.0*.dylib",
    "libcairo*.dylib",
    "libfontconfig*.dylib",
    "libfreetype*.dylib",
    "libharfbuzz*.dylib",
)

SYSTEM_PREFIXES = (
    "/System/Library/",
    "/usr/lib/",
)

FONTCONFIG_XML = """<?xml version=\"1.0\"?>
<!DOCTYPE fontconfig SYSTEM \"urn:fontconfig:fonts.dtd\">
<fontconfig>
  <dir>/System/Library/Fonts</dir>
  <dir>/Library/Fonts</dir>
  <dir prefix=\"xdg\">fonts</dir>
  <dir>~/Library/Fonts</dir>
  <include ignore_missing=\"yes\">conf.d</include>
  <cachedir prefix=\"xdg\">fontconfig</cachedir>
</fontconfig>
"""


def run(*args: str) -> str:
    result = subprocess.run(
        args,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def require_macos() -> None:
    if sys.platform != "darwin":
        raise RuntimeError("The macOS staging script must run on macOS")


def homebrew_prefix() -> Path:
    return Path(run("brew", "--prefix").strip()).resolve()


def parse_otool_dependencies(path: Path) -> list[str]:
    dependencies: list[str] = []
    for line in run("otool", "-L", str(path)).splitlines()[1:]:
        match = re.match(r"\s*(\S+)\s+\(", line)
        if match:
            dependencies.append(match.group(1))
    return dependencies


def is_system_dependency(value: str) -> bool:
    return value.startswith(SYSTEM_PREFIXES)


def resolve_seed(prefix: Path, pattern: str) -> Path:
    candidates = sorted((prefix / "lib").glob(pattern))
    preferred = [path for path in candidates if path.is_symlink()]
    selected = preferred[0] if preferred else (candidates[0] if candidates else None)
    if selected is None:
        raise RuntimeError(f"No Homebrew library matches {prefix / 'lib' / pattern}")
    return selected


def collect_libraries(prefix: Path) -> dict[str, Path]:
    pending: deque[Path] = deque(resolve_seed(prefix, pattern) for pattern in SEED_LIBRARY_PATTERNS)
    collected: dict[str, Path] = {}

    while pending:
        source = pending.popleft()
        destination_name = source.name
        resolved = source.resolve()

        existing = collected.get(destination_name)
        if existing is not None:
            if existing.resolve() != resolved:
                raise RuntimeError(
                    f"Conflicting Homebrew libraries named {destination_name}: "
                    f"{existing} and {source}"
                )
            continue

        try:
            resolved.relative_to(prefix)
        except ValueError as error:
            raise RuntimeError(f"Library is outside the Homebrew prefix: {resolved}") from error

        collected[destination_name] = source

        for dependency in parse_otool_dependencies(resolved):
            if dependency.startswith("@") or is_system_dependency(dependency):
                continue

            dependency_path = Path(dependency)
            if not dependency_path.is_absolute():
                continue

            resolved_dependency = dependency_path.resolve()
            try:
                resolved_dependency.relative_to(prefix)
            except ValueError:
                raise RuntimeError(f"Unexpected non-system dependency of {resolved}: {dependency}")

            pending.append(dependency_path)

    return collected


def copy_fontconfig(prefix: Path, package_root: Path) -> None:
    source = prefix / "etc" / "fonts"
    destination = package_root / "etc" / "fonts"
    if not source.is_dir():
        raise RuntimeError(f"Homebrew Fontconfig directory is missing: {source}")

    shutil.rmtree(destination, ignore_errors=True)
    shutil.copytree(source, destination, symlinks=False)
    (destination / "fonts.conf").write_text(FONTCONFIG_XML, encoding="utf-8")


def patch_library(path: Path, bundled_names: set[str]) -> None:
    dependencies = parse_otool_dependencies(path)

    run("install_name_tool", "-id", f"@loader_path/{path.name}", str(path))

    for dependency in dependencies:
        if dependency.startswith("@") or is_system_dependency(dependency):
            continue
        dependency_name = Path(dependency).name
        if dependency_name not in bundled_names:
            raise RuntimeError(f"Dependency {dependency!r} of {path.name} was not bundled")
        run(
            "install_name_tool",
            "-change",
            dependency,
            f"@loader_path/{dependency_name}",
            str(path),
        )

    run("codesign", "--force", "--sign", "-", str(path))


def stage(package_root: Path) -> None:
    require_macos()
    prefix = homebrew_prefix()
    libraries = collect_libraries(prefix)

    lib_destination = package_root / "lib"
    shutil.rmtree(lib_destination, ignore_errors=True)
    lib_destination.mkdir(parents=True, exist_ok=True)

    for destination_name, source in sorted(libraries.items()):
        shutil.copy2(source.resolve(), lib_destination / destination_name)

    bundled_names = set(libraries)
    for library in sorted(lib_destination.glob("*.dylib")):
        patch_library(library, bundled_names)

    copy_fontconfig(prefix, package_root)

    print(f"Staged {len(libraries)} Homebrew libraries from {prefix} into {lib_destination}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage and relocate the Homebrew runtime for a macOS wheel."
    )
    parser.add_argument(
        "--package-root",
        type=Path,
        default=DEFAULT_PACKAGE_ROOT,
        help="Destination package directory",
    )
    args = parser.parse_args()
    package_root = args.package_root
    if not package_root.is_absolute():
        package_root = (ROOT / package_root).resolve()
    stage(package_root)


if __name__ == "__main__":
    main()
