from __future__ import annotations

import shutil
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "windows-packages.toml"
PACKAGE_ROOT = ROOT / "src" / "weasyprint_libs"


def load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        return tomllib.load(stream)


def reset(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)


def copy_tree(source: Path, destination: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True)


def main() -> None:
    config = load_toml(CONFIG_PATH)["windows"]
    msys_root = ROOT / config["extract_dir"] / config["prefix"]
    bin_source = msys_root / "bin"
    if not bin_source.is_dir():
        raise RuntimeError(f"Missing extracted MinGW prefix: {msys_root}")

    bin_destination = PACKAGE_ROOT / "bin"
    etc_destination = PACKAGE_ROOT / "etc"
    share_destination = PACKAGE_ROOT / "share"
    lib_destination = PACKAGE_ROOT / "lib"

    for path in (bin_destination, etc_destination, share_destination, lib_destination):
        reset(path)

    dlls = sorted(bin_source.glob("*.dll"))
    if not dlls:
        raise RuntimeError(f"No DLLs found in {bin_source}")
    for dll in dlls:
        shutil.copy2(dll, bin_destination / dll.name)

    # pango-view is useful for diagnostics but is not required by WeasyPrint.
    pango_view = bin_source / "pango-view.exe"
    if pango_view.is_file():
        shutil.copy2(pango_view, bin_destination / pango_view.name)

    copy_tree(msys_root / "etc" / "fonts", etc_destination / "fonts")
    copy_tree(msys_root / "share" / "fontconfig", share_destination / "fontconfig")
    copy_tree(msys_root / "share" / "glib-2.0", share_destination / "glib-2.0")

    print(f"Staged {len(dlls)} DLLs into {bin_destination}")


if __name__ == "__main__":
    main()
