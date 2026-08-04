from __future__ import annotations

import json
import subprocess
import sys


def test_pth_activates_native_runtime_before_weasyprint_import() -> None:
    code = r"""
import json
import os

import weasyprint_libs.loader as loader
from weasyprint import HTML

pdf = HTML(string="<h1>PTH activation works</h1>").write_pdf()
print(json.dumps({
    "activated": loader._ACTIVATED,
    "fontconfig_file": os.environ.get("FONTCONFIG_FILE"),
    "pdf_header": pdf[:4].decode("ascii"),
    "pdf_size": len(pdf),
}))
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout.strip().splitlines()[-1])

    assert payload["activated"] is True
    assert payload["pdf_header"] == "%PDF"
    assert payload["pdf_size"] > 1000
