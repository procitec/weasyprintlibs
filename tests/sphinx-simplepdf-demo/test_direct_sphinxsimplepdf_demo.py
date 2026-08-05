from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import os
import platform
import sys
from pathlib import Path

import pytest
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
OUTPUT_DIR = HERE / "_output_direct"


def _assert_legacy_runtime_is_absent() -> None:
    with pytest.raises(importlib.metadata.PackageNotFoundError):
        importlib.metadata.distribution("weasyprint-libs")
    assert importlib.util.find_spec("weasyprint_libs") is None


def _loaded_native_paths() -> set[Path]:
    if sys.platform == "win32":
        return set()

    maps = Path("/proc/self/maps")
    if not maps.is_file():
        return set()

    paths: set[Path] = set()
    for line in maps.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if fields and fields[-1].startswith("/"):
            paths.add(Path(fields[-1]).resolve())
    return paths


def _assert_linux_runtime_is_isolated(native_dir: Path) -> None:
    loaded = _loaded_native_paths()
    native_dir = native_dir.resolve()
    bundled = {path for path in loaded if native_dir in path.parents}
    bundled_names = {path.name.lower() for path in bundled}

    for expected in ("pango", "harfbuzz", "harfbuzz-subset", "fontconfig", "freetype"):
        assert any(expected in name for name in bundled_names), (expected, bundled_names)

    isolated_names = ("pango", "harfbuzz", "fontconfig", "freetype")
    external = {
        path
        for path in loaded
        if any(name in path.name.lower() for name in isolated_names)
        and native_dir not in path.parents
    }
    assert not external, f"System native libraries were loaded: {sorted(map(str, external))}"


def test_direct_sphinx_simplepdf_demo_wheel_builds_document() -> None:
    _assert_legacy_runtime_is_absent()

    from weasyprint import HTML, _weasyprint_libs_loader
    from weasyprint import __version__ as weasyprint_version

    distribution = importlib.metadata.distribution("weasyprint")
    assert "+bundled." in distribution.version

    runtime_metadata_file = next(
        path for path in distribution.files or () if path.name == "BUNDLED-RUNTIME.json"
    )
    runtime_metadata = json.loads(distribution.locate_file(runtime_metadata_file).read_text())
    assert runtime_metadata["bundled_version"] == distribution.version

    package_dir = Path(__import__("weasyprint").__file__).resolve().parent
    runtime_dir = package_dir / "_weasyprint_libs"

    assert _weasyprint_libs_loader._ACTIVATED is True
    assert runtime_dir.is_dir()

    if sys.platform == "win32":
        native_dir = runtime_dir / "bin"
        assert os.environ.get("WEASYPRINT_DLL_DIRECTORIES") == str(native_dir)
        assert any(native_dir.glob("*.dll"))
        assert any(native_dir.glob("*harfbuzz-subset*.dll"))
    elif sys.platform == "darwin":
        native_dir = runtime_dir / "lib"
        assert any(native_dir.glob("*.dylib"))
        assert any(native_dir.glob("*harfbuzz-subset*.dylib"))
        assert _weasyprint_libs_loader._CFFI_DLOPEN_PATCHED is True

        import cffi

        ffi = cffi.FFI()
        assert ffi.dlopen("libgobject-2.0-0") is not None
        assert ffi.dlopen("libharfbuzz-subset.so.0") is not None
    else:
        native_dir = runtime_dir / "lib"
        assert any(native_dir.glob("*.so*"))
        assert any(native_dir.glob("libharfbuzz-subset.so*"))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_pdf = OUTPUT_DIR / "sphinx-simple-pdf-demo.pdf"

    HTML(
        filename=str(HERE / "html" / "index.html"),
        base_url=str(HERE / "html"),
    ).write_pdf(output_pdf)  # , full_fonts=True,)

    assert output_pdf.is_file()
    assert output_pdf.stat().st_size > 8_000_000
    assert output_pdf.read_bytes().startswith(b"%PDF-")

    reader = PdfReader(output_pdf)
    # pdf length depends on installed packages number, printed on last pages.
    # size may vary therefore
    assert len(reader.pages) >= 72 # last page starting with non-dynamic content
    # may be lower on some future platforms
    assert len(reader.pages) >= 80

    if sys.platform.startswith("linux"):
        _assert_linux_runtime_is_isolated(native_dir)

    _assert_legacy_runtime_is_absent()
    print(f"platform={platform.platform()}")
    print(f"python={platform.python_version()}")
    print(f"weasyprint={weasyprint_version}")
    print(f"distribution={distribution.version}")
    print(f"runtime={runtime_dir}")
    print(f"pdf={output_pdf} ({output_pdf.stat().st_size} bytes)")
