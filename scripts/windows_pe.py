from __future__ import annotations

import os
from pathlib import Path

_SYSTEM_DLLS = {
    "advapi32.dll",
    "bcrypt.dll",
    "bcryptprimitives.dll",
    "cabinet.dll",
    "cfgmgr32.dll",
    "comctl32.dll",
    "comdlg32.dll",
    "crypt32.dll",
    "cryptbase.dll",
    "cryptsp.dll",
    "d2d1.dll",
    "d3d11.dll",
    "dbghelp.dll",
    "dwrite.dll",
    "dxgi.dll",
    "dnsapi.dll",
    "dwmapi.dll",
    "gdi32.dll",
    "gdiplus.dll",
    "hid.dll",
    "imm32.dll",
    "iphlpapi.dll",
    "kernel32.dll",
    "msimg32.dll",
    "msvcrt.dll",
    "ncrypt.dll",
    "netapi32.dll",
    "normaliz.dll",
    "ntdll.dll",
    "ole32.dll",
    "oleaut32.dll",
    "pathcch.dll",
    "powrprof.dll",
    "psapi.dll",
    "rpcrt4.dll",
    "secur32.dll",
    "setupapi.dll",
    "shell32.dll",
    "shlwapi.dll",
    "ucrtbase.dll",
    "user32.dll",
    "userenv.dll",
    "usp10.dll",
    "version.dll",
    "windowscodecs.dll",
    "winhttp.dll",
    "wininet.dll",
    "winmm.dll",
    "winspool.drv",
    "ws2_32.dll",
    "wtsapi32.dll",
}


def _read_uint(data: bytes, offset: int, size: int, path: Path) -> int:
    end = offset + size
    if offset < 0 or end > len(data):
        raise RuntimeError(f"Truncated PE structure in {path}")
    return int.from_bytes(data[offset:end], "little")


def _read_c_string(data: bytes, offset: int, path: Path) -> str:
    if offset < 0 or offset >= len(data):
        raise RuntimeError(f"Invalid PE string offset in {path}")
    end = data.find(b"\0", offset, min(len(data), offset + 4096))
    if end < 0:
        raise RuntimeError(f"Unterminated PE string in {path}")
    try:
        return data[offset:end].decode("ascii")
    except UnicodeDecodeError as error:
        raise RuntimeError(f"Non-ASCII DLL name in {path}") from error


def imported_dlls(path: Path) -> set[str]:
    data = path.read_bytes()
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise RuntimeError(f"Not a PE file: {path}")

    pe_offset = _read_uint(data, 0x3C, 4, path)
    if data[pe_offset : pe_offset + 4] != b"PE\0\0":
        raise RuntimeError(f"Invalid PE signature: {path}")

    coff_offset = pe_offset + 4
    section_count = _read_uint(data, coff_offset + 2, 2, path)
    optional_size = _read_uint(data, coff_offset + 16, 2, path)
    optional_offset = coff_offset + 20
    optional_end = optional_offset + optional_size
    if optional_end > len(data):
        raise RuntimeError(f"Truncated PE optional header: {path}")

    magic = _read_uint(data, optional_offset, 2, path)
    if magic == 0x10B:
        data_directories_offset = optional_offset + 96
        directory_count_offset = optional_offset + 92
        image_base = _read_uint(data, optional_offset + 28, 4, path)
    elif magic == 0x20B:
        data_directories_offset = optional_offset + 112
        directory_count_offset = optional_offset + 108
        image_base = _read_uint(data, optional_offset + 24, 8, path)
    else:
        raise RuntimeError(f"Unsupported PE optional-header magic 0x{magic:04x}: {path}")

    directory_count = _read_uint(data, directory_count_offset, 4, path)
    section_offset = optional_end
    sections: list[tuple[int, int, int, int]] = []
    for index in range(section_count):
        offset = section_offset + index * 40
        virtual_size = _read_uint(data, offset + 8, 4, path)
        virtual_address = _read_uint(data, offset + 12, 4, path)
        raw_size = _read_uint(data, offset + 16, 4, path)
        raw_offset = _read_uint(data, offset + 20, 4, path)
        sections.append((virtual_address, max(virtual_size, raw_size), raw_offset, raw_size))

    def rva_to_offset(rva: int) -> int:
        for virtual_address, mapped_size, raw_offset, raw_size in sections:
            if virtual_address <= rva < virtual_address + mapped_size:
                relative = rva - virtual_address
                if relative >= raw_size:
                    raise RuntimeError(f"PE RVA points outside raw section data in {path}")
                return raw_offset + relative
        if rva < optional_end:
            return rva
        raise RuntimeError(f"Cannot map PE RVA 0x{rva:x} in {path}")

    imports: set[str] = set()

    def directory(index: int) -> tuple[int, int]:
        if index >= directory_count:
            return 0, 0
        offset = data_directories_offset + index * 8
        if offset + 8 > optional_end:
            return 0, 0
        return _read_uint(data, offset, 4, path), _read_uint(data, offset + 4, 4, path)

    import_rva, import_size = directory(1)
    if import_rva:
        descriptor_offset = rva_to_offset(import_rva)
        limit = max(1, import_size // 20) if import_size else 4096
        for index in range(min(limit, 4096)):
            offset = descriptor_offset + index * 20
            values = tuple(_read_uint(data, offset + part * 4, 4, path) for part in range(5))
            if not any(values):
                break
            name_rva = values[3]
            imports.add(_read_c_string(data, rva_to_offset(name_rva), path))
        else:
            raise RuntimeError(f"Unterminated PE import directory in {path}")

    delay_rva, delay_size = directory(13)
    if delay_rva:
        descriptor_offset = rva_to_offset(delay_rva)
        limit = max(1, delay_size // 32) if delay_size else 4096
        for index in range(min(limit, 4096)):
            offset = descriptor_offset + index * 32
            values = tuple(_read_uint(data, offset + part * 4, 4, path) for part in range(8))
            if not any(values):
                break
            attributes, name_value = values[:2]
            name_rva = name_value if attributes & 1 else name_value - image_base
            imports.add(_read_c_string(data, rva_to_offset(name_rva), path))
        else:
            raise RuntimeError(f"Unterminated PE delay-import directory in {path}")

    return imports


def is_windows_system_library(name: str) -> bool:
    lowered = name.casefold()
    if (
        lowered in _SYSTEM_DLLS
        or lowered.startswith("api-ms-win-")
        or lowered.startswith("ext-ms-win-")
    ):
        return True

    system_root = os.environ.get("SystemRoot")
    if system_root:
        return (Path(system_root) / "System32" / name).is_file()
    return False


def resolve_dll_closure(bin_directory: Path, seeds: list[str]) -> list[Path]:
    available: dict[str, Path] = {}
    for path in sorted(bin_directory.glob("*.dll")):
        key = path.name.casefold()
        previous = available.setdefault(key, path)
        if previous != path:
            raise RuntimeError(
                f"Duplicate case-insensitive DLL name in {bin_directory}: "
                f"{previous.name}, {path.name}"
            )

    missing_seeds = [name for name in seeds if name.casefold() not in available]
    if missing_seeds:
        raise RuntimeError(f"Required Windows runtime DLLs are missing: {missing_seeds}")

    pending = [name.casefold() for name in seeds]
    selected: dict[str, Path] = {}
    unresolved: dict[str, set[str]] = {}

    while pending:
        key = pending.pop()
        if key in selected:
            continue
        path = available[key]
        selected[key] = path
        for dependency in sorted(imported_dlls(path)):
            dependency_key = dependency.casefold()
            if dependency_key in available:
                if dependency_key not in selected:
                    pending.append(dependency_key)
            elif not is_windows_system_library(dependency):
                unresolved.setdefault(path.name, set()).add(dependency)

    if unresolved:
        details = "; ".join(
            f"{owner}: {sorted(names)}" for owner, names in sorted(unresolved.items())
        )
        raise RuntimeError(f"Unresolved non-system DLL imports: {details}")

    return sorted(selected.values(), key=lambda path: path.name.casefold())
