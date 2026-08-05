# Build and test workflow

## Linux wheel

The reproducible Linux build runs in the manylinux container:

```bash
docker build \
  -f containers/Dockerfile.manylinux_2_28 \
  -t weasyprintlibs-manylinux .

docker run --rm \
  -v "$PWD:/io" \
  -w /io \
  weasyprintlibs-manylinux \
  make wheel WEASYPRINT_VERSION=69.0
```

The build performs these steps:

1. download and verify the pinned native sources;
2. build the native stack into `_build/prefix`;
3. stage the redistributable runtime in `_build/runtime`;
4. patch Linux RPATHs;
5. download the selected upstream WeasyPrint wheel;
6. inject the runtime loader and native payload;
7. change the wheel version and platform metadata;
8. regenerate `RECORD` and verify the completed wheel.

Useful targets:

```text
make sync              Install all development dependency groups
make fetch             Download and verify native sources
make source-lock       Record observed source checksums
make native-build      Build the Linux native stack
make stage             Stage the Linux runtime and patch ELF RPATHs
make wheel             Build the bundled WeasyPrint wheel
make verify-wheel      Inspect an existing wheel in dist/
make test-unit         Test build and patch logic without native compilation
make local-test        Build, install and render the test document
make local-test-wheel  Test an already built wheel
make clean             Remove build and local-test output
make distclean         Also remove environments and download caches
```

## Windows

Normal Windows builds use the committed MSYS2 package lock:

```powershell
.\scripts\build_windows.ps1 -WeasyPrintVersion 69.0 -Profile x86_64
```

Update the package closure only when intentionally changing the native stack:

```powershell
uv run python scripts/fetch_windows_packages.py --profile x86_64 --update-lock
```

## macOS

The macOS build stages and relocates the Homebrew dependency closure before
patching the upstream wheel:

```bash
WEASYPRINT_VERSION=69.0 ./scripts/build_macos.sh
```

## Local integration test

`make local-test` creates the wheel and then runs
`scripts/test_patched_wheel.py`. The script creates `.test-venv`, installs only
the generated WeasyPrint wheel plus the test dependencies, and executes
`tests/runtime/test_direct_weasyprint_wheel.py`.

The document test verifies:

- no legacy `weasyprint-libs` distribution or `weasyprint_libs` module exists;
- the embedded runtime loader activated during `import weasyprint`;
- native files are present in `weasyprint/_weasyprint_libs`;
- the bundled/local wheel metadata is consistent;
- HarfBuzz subset is included;
- PDF generation uses the normal subsetting path, not `full_fonts=True`;
- the resulting two-page PDF contains the expected text;
- on Linux, Pango, HarfBuzz, Fontconfig and FreeType are not loaded from system paths.

## Runtime configuration

Runtime entry libraries and macOS CFFI aliases are maintained in
`config/runtime-libraries.toml`. The Python configuration module is no longer
checked into the repository. It is rendered directly into the target
WeasyPrint wheel by `scripts/patch_weasyprint_wheel.py`.

Validate the configuration with:

```bash
make runtime-config-check
```
