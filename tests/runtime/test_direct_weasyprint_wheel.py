from __future__ import annotations

import importlib.metadata
import importlib.util
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
        importlib.metadata.distribution("procitec-weasyprint-libs")

    assert importlib.util.find_spec("weasyprintlibs_native") is None


def _loaded_native_paths() -> set[Path]:
    if sys.platform == "win32":
        return set()

    paths: set[Path] = set()
    maps = Path("/proc/self/maps")
    if not maps.is_file():
        return paths

    for line in maps.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if fields and fields[-1].startswith("/"):
            paths.add(Path(fields[-1]).resolve())
    return paths


def test_direct_weasyprint_wheel_builds_document_without_legacy_wheel() -> None:
    _assert_legacy_runtime_is_absent()

    from weasyprint import HTML, _procitec_native_loader
    from weasyprint import __version__ as weasyprint_version

    package_dir = Path(__import__("weasyprint").__file__).resolve().parent
    runtime_dir = package_dir / "_procitec_native"

    assert _procitec_native_loader._ACTIVATED is True
    assert runtime_dir.is_dir()

    if sys.platform == "win32":
        native_dir = runtime_dir / "bin"
        assert os.environ.get("WEASYPRINT_DLL_DIRECTORIES") == str(native_dir)
        assert any(native_dir.glob("*.dll"))
    else:
        native_dir = runtime_dir / "lib"
        assert any(native_dir.glob("*.so*"))

        loaded = _loaded_native_paths()
        bundled_loaded = {path for path in loaded if native_dir.resolve() in path.parents}
        bundled_names = {path.name for path in bundled_loaded}
        assert any("pango" in name for name in bundled_names), bundled_names
        assert any("cairo" in name for name in bundled_names), bundled_names
        assert any("fontconfig" in name for name in bundled_names), bundled_names

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_pdf = OUTPUT_DIR / "direct-wheel-runtime-test.pdf"

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

    _assert_legacy_runtime_is_absent()

    print(f"platform={platform.platform()}")
    print(f"python={platform.python_version()}")
    print(f"weasyprint={weasyprint_version}")
    print(f"runtime={runtime_dir}")
    print(f"pdf={output_pdf} ({output_pdf.stat().st_size} bytes)")
