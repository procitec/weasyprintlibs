from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path
from typing import Any

from ._weasyprint_libs_config import (
    LINUX_LIBRARIES,
    LINUX_LIBRARY_DIRECTORY,
    MACOS_LIBRARIES,
    MACOS_LIBRARY_ALIASES,
    MACOS_LIBRARY_DIRECTORY,
    WINDOWS_LIBRARIES,
    WINDOWS_LIBRARY_DIRECTORY,
)

_ACTIVATED = False
_LOADED_LIBRARIES: list[object] = []
_DLL_DIRECTORY_HANDLES: list[object] = []

_CFFI_DLOPEN_PATCHED = False
_ORIGINAL_CFFI_DLOPEN: Any = None


def _runtime_root() -> Path:
    module_dir = Path(__file__).resolve().parent
    embedded_runtime = module_dir / "_weasyprint_libs"

    if embedded_runtime.is_dir():
        return embedded_runtime

    return module_dir


def activate() -> None:
    global _ACTIVATED

    if _ACTIVATED:
        return

    root = _runtime_root()

    if sys.platform == "win32":
        _activate_windows(root)
    elif sys.platform == "darwin":
        _activate_macos(root)
    elif sys.platform.startswith("linux"):
        _activate_linux(root)
    else:
        raise RuntimeError(f"Unsupported platform: {sys.platform}")

    _ACTIVATED = True


def _require_libraries(
    directory: Path,
    names: tuple[str, ...],
) -> list[Path]:
    if not directory.is_dir():
        raise RuntimeError(f"Bundled library directory is missing: {directory}")

    paths = [directory / name for name in names]
    missing = [path for path in paths if not path.is_file()]

    if missing:
        formatted = "\n".join(f"  - {path}" for path in missing)
        raise RuntimeError(f"Bundled native libraries are missing:\n{formatted}")

    return paths


def _load_windows_library(path: Path) -> None:
    try:
        handle = ctypes.WinDLL(str(path))
    except OSError as error:
        raise RuntimeError(f"Failed to load bundled Windows library: {path}") from error

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
        raise RuntimeError(f"Failed to load bundled native library: {path}") from error

    _LOADED_LIBRARIES.append(handle)


def _configure_fontconfig(root: Path) -> None:
    fonts_dir = root / "etc" / "fonts"
    fonts_conf = fonts_dir / "fonts.conf"

    if not fonts_conf.is_file():
        raise RuntimeError(f"Bundled Fontconfig configuration is missing: {fonts_conf}")

    os.environ.setdefault("FONTCONFIG_FILE", str(fonts_conf))
    os.environ.setdefault("FONTCONFIG_PATH", str(fonts_dir))

    cache_root = root / "cache"
    (cache_root / "fontconfig").mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("XDG_CACHE_HOME", str(cache_root))


def _activate_windows(root: Path) -> None:
    bin_dir = root / WINDOWS_LIBRARY_DIRECTORY
    paths = _require_libraries(bin_dir, WINDOWS_LIBRARIES)

    os.environ.setdefault("WEASYPRINT_DLL_DIRECTORIES", str(bin_dir))
    _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(bin_dir)))

    for path in paths:
        _load_windows_library(path)


def _activate_linux(root: Path) -> None:
    _configure_fontconfig(root)

    lib_dir = root / LINUX_LIBRARY_DIRECTORY
    for path in _require_libraries(lib_dir, LINUX_LIBRARIES):
        _load_local(path)


def _patch_cffi_dlopen(lib_dir: Path) -> None:
    global _CFFI_DLOPEN_PATCHED
    global _ORIGINAL_CFFI_DLOPEN

    if _CFFI_DLOPEN_PATCHED:
        return

    try:
        import cffi
    except ImportError:
        # The package can be inspected before WeasyPrint and cffi are installed.
        return

    original_dlopen = cffi.FFI.dlopen
    _ORIGINAL_CFFI_DLOPEN = original_dlopen

    def bundled_dlopen(
        ffi_instance: cffi.FFI,
        name: str | bytes | None,
        flags: int = 0,
    ) -> Any:
        if isinstance(name, bytes):
            lookup_name = name.decode(
                sys.getfilesystemencoding(),
                errors="surrogateescape",
            )
        else:
            lookup_name = name

        if isinstance(lookup_name, str):
            bundled_name = MACOS_LIBRARY_ALIASES.get(lookup_name)

            if bundled_name is not None:
                bundled_path = lib_dir / bundled_name

                if bundled_path.is_file():
                    return original_dlopen(
                        ffi_instance,
                        str(bundled_path),
                        flags,
                    )

        return original_dlopen(
            ffi_instance,
            name,
            flags,
        )

    cffi.FFI.dlopen = bundled_dlopen
    _CFFI_DLOPEN_PATCHED = True


def _activate_macos(root: Path) -> None:
    _configure_fontconfig(root)

    lib_dir = root / MACOS_LIBRARY_DIRECTORY
    for path in _require_libraries(lib_dir, MACOS_LIBRARIES):
        _load_local(path)

    _patch_cffi_dlopen(lib_dir)
