from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from runtime_config import load_runtime_config
from verify_runtime_payload import verify_payload
from windows_config import load_windows_profile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT / "_build" / "runtime"


def reset(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)


def copy_tree(source: Path, destination: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile")
    args = parser.parse_args()

    load_runtime_config()
    profile = load_windows_profile(args.profile)
    msys_root = ROOT / profile["extract_dir"] / profile["prefix"]
    bin_source = msys_root / "bin"
    if not bin_source.is_dir():
        raise RuntimeError(f"Missing extracted MSYS2 prefix: {msys_root}")

    bin_destination = RUNTIME_ROOT / "bin"
    etc_destination = RUNTIME_ROOT / "etc"
    share_destination = RUNTIME_ROOT / "share"
    lib_destination = RUNTIME_ROOT / "lib"

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

    required = verify_payload(
        RUNTIME_ROOT,
        "windows",
        architecture=profile["architecture"],
    )
    print(
        f"Staged {len(dlls)} DLLs for {profile['profile']} into {bin_destination}; "
        f"verified {len(required)} runtime entry DLLs"
    )


if __name__ == "__main__":
    main()
