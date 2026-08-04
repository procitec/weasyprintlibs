from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

_ACTIVATED = False
_DLL_DIRECTORY_HANDLES: list[object] = []
_DLL_HANDLES: list[object] = []


def activate() -> None:
    global _ACTIVATED
    if _ACTIVATED:
        return

    root = Path(__file__).resolve().parent
    if sys.platform == "win32":
        _activate_windows(root)
    else:
        _activate_linux(root)

    fonts_conf = root / "etc" / "fonts" / "fonts.conf"
    if fonts_conf.exists():
        os.environ.setdefault("FONTCONFIG_FILE", str(fonts_conf))

    _ACTIVATED = True


def _activate_windows(root: Path) -> None:
    bin_dir = root / "bin"
    if not bin_dir.is_dir():
        raise RuntimeError(f"Missing bundled DLL directory: {bin_dir}")

    _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(bin_dir)))
    os.environ.setdefault("WEASYPRINT_DLL_DIRECTORIES", str(bin_dir))

    for name in (
        "libglib-2.0-0.dll",
        "libgobject-2.0-0.dll",
        "libgio-2.0-0.dll",
        "libfontconfig-1.dll",
        "libfreetype-6.dll",
        "libharfbuzz-0.dll",
        "libcairo-2.dll",
        "libpango-1.0-0.dll",
        "libpangoft2-1.0-0.dll",
        "libpangocairo-1.0-0.dll",
    ):
        path = bin_dir / name
        if path.exists():
            _DLL_HANDLES.append(ctypes.WinDLL(str(path)))


def _configure_fontconfig(root: Path) -> None:
    fonts_dir = root / "etc" / "fonts"
    fonts_conf = fonts_dir / "fonts.conf"

    if not fonts_conf.is_file():
        raise RuntimeError(
            f"Bundled Fontconfig configuration is missing: {fonts_conf}"
        )

    # FONTCONFIG_FILE may be absolute.
    os.environ.setdefault("FONTCONFIG_FILE", str(fonts_conf))

    # Required for relative includes such as:
    #   <include>conf.d</include>
    os.environ.setdefault("FONTCONFIG_PATH", str(fonts_dir))

    # Ensure Fontconfig has a writable cache location in minimal containers.
    cache_dir = root / "cache" / "fontconfig"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("XDG_CACHE_HOME", str(root / "cache"))


def _activate_linux(root: Path) -> None:
    _configure_fontconfig(root)

    lib_dir = root / "lib"

    for name in (
        "libffi.so.8",
        "libglib-2.0.so.0",
        "libgobject-2.0.so.0",
        "libgio-2.0.so.0",
        "libfontconfig.so.1",
        "libfreetype.so.6",
        "libharfbuzz.so.0",
        "libcairo.so.2",
        "libpango-1.0.so.0",
        "libpangoft2-1.0.so.0",
        "libpangocairo-1.0.so.0",
    ):
        path = lib_dir / name
        if path.exists():
            _DLL_HANDLES.append(ctypes.CDLL(str(path), mode=ctypes.RTLD_GLOBAL))
