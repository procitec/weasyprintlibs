from __future__ import annotations

import os
import platform
import sys
from pathlib import Path

import pytest
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
OUTPUT_DIR = HERE / "_output"


def dump_loaded_libraries() -> None:
    if sys.platform in {"win32", "darwin"}:
        return

    interesting = (
        "pango",
        "harfbuzz",
        "fontconfig",
        "freetype",
        "glib",
        "gobject",
        "gio",
        "ffi",
        "cairo",
        "pixman",
        "expat",
        "png",
        "zlib",
    )

    paths: set[str] = set()

    for line in Path("/proc/self/maps").read_text().splitlines():
        fields = line.split()
        if not fields:
            continue

        path = fields[-1]
        lower = path.lower()

        if path.startswith("/") and any(name in lower for name in interesting):
            paths.add(path)

    print("\nLoaded native libraries:")
    for path in sorted(paths):
        print(f"  {path}")


@pytest.mark.skipif(
    sys.platform != "darwin",
    reason="macOS-specific test",
)
def test_macos_cffi_uses_bundled_gobject() -> None:

    import cffi

    import weasyprint_libs
    import weasyprint_libs.loader as loader

    root = Path(weasyprint_libs.__file__).resolve().parent
    expected = root / "lib" / "libgobject-2.0.0.dylib"

    assert loader._ACTIVATED
    assert expected.is_file()

    ffi = cffi.FFI()
    library = ffi.dlopen("libgobject-2.0-0")

    assert library is not None


def test_weasyprint_runtime() -> None:
    dump_loaded_libraries()

    from weasyprint import HTML
    from weasyprint import __version__ as weasyprint_version

    dump_loaded_libraries()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_pdf = OUTPUT_DIR / "runtime-smoke-test.pdf"

    HTML(
        filename=str(HERE / "document.html"),
        base_url=str(HERE),
    ).write_pdf(output_pdf)

    dump_loaded_libraries()

    assert output_pdf.is_file()
    assert output_pdf.stat().st_size > 2_000
    assert output_pdf.read_bytes().startswith(b"%PDF-")

    reader = PdfReader(output_pdf)
    assert len(reader.pages) == 2

    extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "WeasyPrint native runtime test" in extracted_text
    assert "Second page" in extracted_text

    if sys.platform == "win32":
        assert os.environ.get("WEASYPRINT_DLL_DIRECTORIES")

    print(f"platform={platform.platform()}")
    print(f"python={platform.python_version()}")
    print(f"weasyprint={weasyprint_version}")
    print(f"fontconfig_file={os.environ.get('FONTCONFIG_FILE')}")
    print(f"pdf={output_pdf} ({output_pdf.stat().st_size} bytes)")
