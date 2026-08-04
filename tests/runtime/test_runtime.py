from __future__ import annotations

import os
import platform
import sys
from pathlib import Path

from pypdf import PdfReader


HERE = Path(__file__).resolve().parent
OUTPUT_DIR = HERE / "_output"


def dump_loaded_libraries() -> None:
    if sys.platform == "win32":
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


def test_weasyprint_runtime() -> None:
    dump_loaded_libraries()

    from weasyprint import HTML, __version__ as weasyprint_version

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
