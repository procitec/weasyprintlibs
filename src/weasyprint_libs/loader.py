from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

_ACTIVATED = False
_LOADED_LIBRARIES: list[ctypes.CDLL] = []

_WINDOWS_LIBRARIES = (
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
)

_LINUX_LIBRARIES = (
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
)

_MACOS_LIBRARIES = (
    "libffi.8.dylib",
    "libintl.8.dylib",
    "libglib-2.0.0.dylib",
    "libgobject-2.0.0.dylib",
    "libgio-2.0.0.dylib",
    "libfontconfig.1.dylib",
    "libfreetype.6.dylib",
    "libharfbuzz.0.dylib",
    "libcairo.2.dylib",
    "libpango-1.0.0.dylib",
    "libpangoft2-1.0.0.dylib",
    "libpangocairo-1.0.0.dylib",
)


def activate() -> None:
    global _ACTIVATED

    if _ACTIVATED:
        return

    root = Path(__file__).resolve().parent

    if sys.platform == "win32":
        _activate_windows(root)
    elif sys.platform == "darwin":
        _activate_macos(root)
    elif sys.platform.startswith("linux"):
        _activate_linux(root)
    else:
        raise RuntimeError(
            f"Unsupported platform: {sys.platform}"
        )

    _ACTIVATED = True


def _require_libraries(
    directory: Path,
    names: tuple[str, ...],
) -> list[Path]:
    if not directory.is_dir():
        raise RuntimeError(
            f"Bundled library directory is missing: {directory}"
        )

    paths = [directory / name for name in names]
    missing = [path for path in paths if not path.is_file()]

    if missing:
        formatted = "\n".join(f"  - {path}" for path in missing)
        raise RuntimeError(
            "Bundled native libraries are missing:\n"
            f"{formatted}"
        )

    return paths


def _load_windows_library(path: Path) -> None:
    try:
        handle = ctypes.WinDLL(str(path))
    except OSError as error:
        raise RuntimeError(
            f"Failed to load bundled Windows library: {path}"
        ) from error

    _LOADED_LIBRARIES.append(handle)


def _load_local(path: Path) -> None:
    mode = getattr(os, "RTLD_NOW", 0)

    if sys.platform == "darwin":
        mode |= getattr(ctypes, "RTLD_GLOBAL", 0)
    else:
        mode |= ctypes.RTLD_LOCAL

    try:
        handle = ctypes.CDLL(str(path), mode=mode)
    except OSError as error:
        raise RuntimeError(
            f"Failed to load bundled native library: {path}"
        ) from error

    _LOADED_LIBRARIES.append(handle)


def _configure_fontconfig(root: Path) -> None:
    fonts_dir = root / "etc" / "fonts"
    fonts_conf = fonts_dir / "fonts.conf"

    if not fonts_conf.is_file():
        raise RuntimeError(
            "Bundled Fontconfig configuration is missing: "
            f"{fonts_conf}"
        )

    os.environ.setdefault("FONTCONFIG_FILE", str(fonts_conf))
    os.environ.setdefault("FONTCONFIG_PATH", str(fonts_dir))

    cache_root = root / "cache"
    cache_dir = cache_root / "fontconfig"
    cache_dir.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("XDG_CACHE_HOME", str(cache_root))


def _activate_windows(root: Path) -> None:
    bin_dir = root / "bin"
    paths = _require_libraries(bin_dir, _WINDOWS_LIBRARIES)

    os.environ.setdefault(
        "WEASYPRINT_DLL_DIRECTORIES",
        str(bin_dir),
    )

    with os.add_dll_directory(str(bin_dir)):
        for path in paths:
            _load_windows_library(path)


def _activate_linux(root: Path) -> None:
    _configure_fontconfig(root)

    lib_dir = root / "lib"
    for path in _require_libraries(lib_dir, _LINUX_LIBRARIES):
        _load_local(path)


def _activate_macos(root: Path) -> None:
    _configure_fontconfig(root)

    lib_dir = root / "lib"
    for path in _require_libraries(lib_dir, _MACOS_LIBRARIES):
        _load_local(path)
