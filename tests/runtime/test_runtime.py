from __future__ import annotations

import os
import platform
import sys
from pathlib import Path

from pypdf import PdfReader


HERE = Path(__file__).resolve().parent
OUTPUT_DIR = HERE / "_output"


def test_weasyprint_runtime() -> None:
    # The native runtime must be activated before importing WeasyPrint.
    import weasyprintlibs_native

    weasyprintlibs_native.activate()

    from weasyprint import HTML, __version__ as weasyprint_version

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_pdf = OUTPUT_DIR / "runtime-smoke-test.pdf"

    HTML(
        filename=str(HERE / "document.html"),
        base_url=str(HERE),
    ).write_pdf(output_pdf)

    assert output_pdf.is_file()
    assert output_pdf.stat().st_size > 2_000
    assert output_pdf.read_bytes().startswith(b"%PDF-")

    reader = PdfReader(output_pdf)
    assert len(reader.pages) == 2

    extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "WeasyPrint native runtime test" in extracted_text
    assert "Second page" in extracted_text

    package_dir = Path(weasyprintlibs_native.__file__).resolve().parent
    assert package_dir.is_dir()

    if sys.platform == "win32":
        assert (package_dir / "bin").is_dir()
        assert list((package_dir / "bin").glob("*.dll"))
        assert os.environ.get("WEASYPRINT_DLL_DIRECTORIES")
    else:
        assert (package_dir / "lib").is_dir()
        assert list((package_dir / "lib").glob("*.so*"))

    print(f"platform={platform.platform()}")
    print(f"python={platform.python_version()}")
    print(f"weasyprint={weasyprint_version}")
    print(f"native_package={package_dir}")
    print(f"fontconfig_file={os.environ.get('FONTCONFIG_FILE')}")
    print(f"pdf={output_pdf} ({output_pdf.stat().st_size} bytes)")
