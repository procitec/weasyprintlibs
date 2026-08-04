#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLED_DIR = "_procitec_native"
BOOTSTRAP_MODULE = "_procitec_native_loader.py"


def download_wheel(version: str, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    expected_name = f"weasyprint-{version}-py3-none-any.whl"
    cached = destination / expected_name
    if cached.is_file():
        return cached

    metadata_url = f"https://pypi.org/pypi/weasyprint/{version}/json"
    print(f"+ download metadata {metadata_url}", flush=True)
    with urllib.request.urlopen(metadata_url) as response:
        metadata = json.load(response)

    candidates = [
        entry
        for entry in metadata.get("urls", [])
        if entry.get("packagetype") == "bdist_wheel" and entry.get("filename") == expected_name
    ]
    if len(candidates) != 1:
        available = [entry.get("filename") for entry in metadata.get("urls", [])]
        raise RuntimeError(
            f"Expected upstream wheel {expected_name!r}; available files: {available}"
        )

    entry = candidates[0]
    print(f"+ download {entry['url']}", flush=True)
    temporary = cached.with_suffix(cached.suffix + ".part")
    urllib.request.urlretrieve(entry["url"], temporary)
    expected_digest = entry.get("digests", {}).get("sha256")
    if expected_digest:
        actual_digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
        if actual_digest != expected_digest:
            temporary.unlink(missing_ok=True)
            raise RuntimeError(
                f"Downloaded wheel checksum mismatch: {actual_digest} != {expected_digest}"
            )
    temporary.replace(cached)
    return cached


def copy_runtime(runtime: Path, package: Path) -> None:
    target = package / BUNDLED_DIR
    target.mkdir(parents=True, exist_ok=True)
    for name in ("lib", "bin", "etc", "share"):
        source = runtime / name
        if source.is_dir():
            shutil.copytree(source, target / name, dirs_exist_ok=True, symlinks=False)


def bootstrap_source() -> str:
    return """from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

_ACTIVATED = False
_DLL_DIRECTORY_HANDLES: list[object] = []
_DLL_HANDLES: list[object] = []


def _load(path: Path, *, windows: bool = False) -> None:
    if not path.is_file():
        return
    if windows:
        _DLL_HANDLES.append(ctypes.WinDLL(str(path)))
    else:
        mode = getattr(ctypes, "RTLD_GLOBAL", 0) | getattr(os, "RTLD_NOW", 0)
        _DLL_HANDLES.append(ctypes.CDLL(str(path), mode=mode))


def activate() -> None:
    global _ACTIVATED
    if _ACTIVATED:
        return

    root = Path(__file__).resolve().parent / "_procitec_native"
    fonts_dir = root / "etc" / "fonts"
    fonts_conf = fonts_dir / "fonts.conf"
    if fonts_conf.is_file():
        os.environ.setdefault("FONTCONFIG_FILE", str(fonts_conf))
        os.environ.setdefault("FONTCONFIG_PATH", str(fonts_dir))
        cache_root = root / "cache"
        (cache_root / "fontconfig").mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("XDG_CACHE_HOME", str(cache_root))

    if sys.platform == "win32":
        bin_dir = root / "bin"
        if bin_dir.is_dir():
            _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(bin_dir)))
            os.environ.setdefault("WEASYPRINT_DLL_DIRECTORIES", str(bin_dir))
        for name in (
            "libglib-2.0-0.dll", "libgobject-2.0-0.dll", "libgio-2.0-0.dll",
            "libfontconfig-1.dll", "libfreetype-6.dll", "libharfbuzz-0.dll",
            "libcairo-2.dll", "libpango-1.0-0.dll", "libpangoft2-1.0-0.dll",
            "libpangocairo-1.0-0.dll",
        ):
            _load(bin_dir / name, windows=True)
    else:
        lib_dir = root / "lib"
        for name in (
            "libffi.so.8", "libglib-2.0.so.0", "libgobject-2.0.so.0",
            "libgio-2.0.so.0", "libfontconfig.so.1", "libfreetype.so.6",
            "libharfbuzz.so.0", "libcairo.so.2", "libpango-1.0.so.0",
            "libpangoft2-1.0.so.0", "libpangocairo-1.0.so.0",
        ):
            _load(lib_dir / name)

    _ACTIVATED = True
"""


def patch_init(package: Path) -> None:
    init = package / "__init__.py"
    original = init.read_text(encoding="utf-8")
    marker = "from ._procitec_native_loader import activate as _activate_procitec_native"
    if marker in original:
        return
    prefix = f"{marker}\n_activate_procitec_native()\ndel _activate_procitec_native\n\n"
    init.write_text(prefix + original, encoding="utf-8")
    (package / BOOTSTRAP_MODULE).write_text(bootstrap_source(), encoding="utf-8")


def patch_wheel_metadata(root: Path, platform_tag: str) -> Path:
    dist_infos = list(root.glob("weasyprint-*.dist-info"))
    if len(dist_infos) != 1:
        raise RuntimeError(f"Expected one WeasyPrint dist-info directory, got: {dist_infos}")
    dist_info = dist_infos[0]
    wheel_file = dist_info / "WHEEL"
    lines = wheel_file.read_text(encoding="utf-8").splitlines()
    patched: list[str] = []
    tag_written = False
    root_written = False
    for line in lines:
        if line.startswith("Root-Is-Purelib:"):
            patched.append("Root-Is-Purelib: false")
            root_written = True
        elif line.startswith("Tag:"):
            if not tag_written:
                patched.append(f"Tag: py3-none-{platform_tag}")
                tag_written = True
        else:
            patched.append(line)
    if not root_written:
        patched.append("Root-Is-Purelib: false")
    if not tag_written:
        patched.append(f"Tag: py3-none-{platform_tag}")
    wheel_file.write_text("\n".join(patched) + "\n", encoding="utf-8")
    return dist_info


def record_hash(path: Path) -> tuple[str, int]:
    data = path.read_bytes()
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode("ascii")
    return f"sha256={digest}", len(data)


def write_record(root: Path, dist_info: Path) -> None:
    record = dist_info / "RECORD"
    rows: list[tuple[str, str, str]] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p != record):
        digest, size = record_hash(path)
        rows.append((path.relative_to(root).as_posix(), digest, str(size)))
    rows.append((record.relative_to(root).as_posix(), "", ""))
    with record.open("w", encoding="utf-8", newline="") as stream:
        csv.writer(stream, lineterminator="\n").writerows(rows)


def output_name(source: Path, platform_tag: str) -> str:
    parts = source.name[:-4].split("-")
    if len(parts) < 5:
        raise RuntimeError(f"Unexpected wheel filename: {source.name}")
    return "-".join(parts[:-3] + ["py3", "none", platform_tag]) + ".whl"


def build_wheel(source: Path, runtime: Path, destination: Path, platform_tag: str) -> Path:
    if not source.is_file():
        raise FileNotFoundError(source)
    if not (runtime / "lib").is_dir() and not (runtime / "bin").is_dir():
        raise RuntimeError(f"No staged native runtime found below {runtime}")

    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="weasyprint-wheel-") as temporary:
        unpacked = Path(temporary)
        with zipfile.ZipFile(source) as archive:
            archive.extractall(unpacked)

        package = unpacked / "weasyprint"
        if not package.is_dir():
            raise RuntimeError(f"Wheel does not contain a weasyprint package: {source}")
        copy_runtime(runtime, package)
        patch_init(package)
        dist_info = patch_wheel_metadata(unpacked, platform_tag)
        write_record(unpacked, dist_info)

        output = destination / output_name(source, platform_tag)
        output.unlink(missing_ok=True)
        with zipfile.ZipFile(
            output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for path in sorted(p for p in unpacked.rglob("*") if p.is_file()):
                archive.write(path, path.relative_to(unpacked).as_posix())
    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bundle the staged native runtime directly into a WeasyPrint wheel."
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--wheel", type=Path, help="Existing upstream WeasyPrint wheel")
    source.add_argument(
        "--version", help="WeasyPrint version to download from the configured package index"
    )
    parser.add_argument("--runtime", type=Path, default=Path("src/weasyprintlibs_native"))
    parser.add_argument("--download-dir", type=Path, default=Path("downloads/weasyprint"))
    parser.add_argument("--output-dir", type=Path, default=Path("dist"))
    parser.add_argument("--platform-tag", required=True)
    args = parser.parse_args()

    runtime = (ROOT / args.runtime).resolve()
    output_dir = (ROOT / args.output_dir).resolve()
    if args.wheel:
        wheel = args.wheel if args.wheel.is_absolute() else (ROOT / args.wheel)
    else:
        version = args.version or os.environ.get("WEASYPRINT_VERSION")
        if not version:
            raise SystemExit("Pass --version/--wheel or set WEASYPRINT_VERSION")
        wheel = download_wheel(version, (ROOT / args.download_dir).resolve())

    output = build_wheel(wheel.resolve(), runtime, output_dir, args.platform_tag)
    print(f"Created patched WeasyPrint wheel: {output}")


if __name__ == "__main__":
    main()
