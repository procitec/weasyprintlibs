# Runtime smoke test

This test installs a built platform wheel together with a selected WeasyPrint
version in a clean virtual environment. It activates `weasyprintlibs_native`,
renders a two-page PDF, validates the PDF structure, and verifies that native
runtime files are present inside the installed wheel.

The CI test environments intentionally do not install system Pango, Cairo,
HarfBuzz or Fontconfig libraries. Rocky Linux jobs install only basic tools and
a font package so the bundled native runtime is exercised.

Local execution after building a wheel:

```bash
uv venv .test-venv --python 3.13
uv pip install --python .test-venv/bin/python dist/*.whl weasyprint==69.0 pytest pypdf
.test-venv/bin/python -m pytest tests/runtime/test_runtime.py -v -s
```

## Direct WeasyPrint wheel

`test_direct_weasyprint_wheel.py` installs and tests only the patched WeasyPrint wheel.
It verifies that `weasyprint-libs` is not installed, that
`weasyprintlibs_native` cannot be imported, and that the native libraries bundled
inside the WeasyPrint package are used to build the same two-page test document.
