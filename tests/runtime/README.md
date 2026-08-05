# Patched-wheel integration test

`test_direct_weasyprint_wheel.py` is run in a clean virtual environment that
contains the generated bundled WeasyPrint wheel, `pytest` and `pypdf`.

Local full test:

```bash
make local-test
```

Test an existing wheel:

```bash
make local-test-wheel
```

The test deliberately calls `write_pdf` without `full_fonts=True`, so the
HarfBuzz subset path is exercised.
