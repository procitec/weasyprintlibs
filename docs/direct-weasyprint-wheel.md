# Directly patched WeasyPrint wheel

The local build can create a platform-specific `weasyprint` wheel that already contains the native runtime. This is an alternative to installing `procitec-weasyprint-libs` beside the upstream wheel.

## Linux

Build the native stack and patch WeasyPrint 69.0:

```bash
make patched-wheel WEASYPRINT_VERSION=69.0
```

For the reproducible manylinux build, run the same target in the existing container:

```bash
docker build \
  -f containers/Dockerfile.manylinux_2_28 \
  -t weasyprintlibs-manylinux .

docker run --rm \
  -v "$PWD:/io" \
  -w /io \
  weasyprintlibs-manylinux \
  make patched-wheel WEASYPRINT_VERSION=69.0
```

## Windows

```powershell
.\scripts\build_patched_weasyprint_windows.ps1 -WeasyPrintVersion 69.0
```

The generated file is written to `dist/` and keeps the upstream package name and version, but changes the wheel to the selected platform tag.

## Processing steps

1. build or extract the native runtime;
2. download the exact upstream `py3-none-any` WeasyPrint wheel;
3. copy the runtime into `weasyprint/_weasyprint_libs`;
4. add an early loader call to `weasyprint/__init__.py`;
5. change `Root-Is-Purelib` and the wheel platform tag;
6. regenerate `RECORD` and repack the wheel.

An already downloaded wheel can also be patched directly:

```bash
uv run python scripts/patch_weasyprint_wheel.py \
  --wheel downloads/weasyprint/weasyprint-69.0-py3-none-any.whl \
  --platform-tag manylinux_2_28_x86_64
```

## GitHub Actions

The build and release workflows create two independent artifacts per platform:

- `wheel-*`: the existing `procitec-weasyprint-libs` runtime wheel.
- `direct-weasyprint-*`: the patched upstream WeasyPrint wheel containing the runtime.

The `test-direct-*` jobs install only the `direct-weasyprint-*` artifact. Their
runtime test renders `tests/runtime/document.html` and verifies that the legacy
`procitec-weasyprint-libs` distribution and `weasyprint_libs` package are
not present. The release workflow publishes both wheel variants after all tests
have passed.
