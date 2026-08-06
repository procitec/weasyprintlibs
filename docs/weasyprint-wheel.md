# Bundled WeasyPrint wheel

The repository produces one artifact type: a platform-specific `weasyprint`
wheel with its native runtime embedded directly in the package.

## Wheel identity

The distribution remains `WeasyPrint`. A downstream local version identifies
the bundled runtime revision:

```text
weasyprint-69.0+bundled.26.1.1-py3-none-manylinux_2_28_x86_64.whl
```

The same version is written to `METADATA`, the `.dist-info` directory and
`BUNDLED-RUNTIME.json`.

## Layout

```text
weasyprint/
  __init__.py
  _weasyprint_libs_loader.py
  _weasyprint_libs_config.py
  _weasyprint_libs/
    lib/ or bin/
    etc/fonts/
    share/
weasyprint-<bundled-version>.dist-info/
  BUNDLED-RUNTIME.json
  licenses/
    PROJECT_LICENSE.txt
    THIRD_PARTY_LICENSES.md
    manifest.json
    texts/<component>/...
  METADATA
  WHEEL
  RECORD
```

## Processing steps

1. build or extract the native runtime into `_build/runtime`;
2. collect and validate license texts for every staged native file;
3. create the matching release license ZIP;
4. download the exact upstream `py3-none-any` WeasyPrint wheel;
5. copy the staged runtime into `weasyprint/_weasyprint_libs`;
6. copy the generated license bundle into `.dist-info/licenses`;
7. inject an early loader call into `weasyprint/__init__.py`;
8. render the runtime configuration from `config/runtime-libraries.toml`;
9. set the bundled local version and platform wheel tag;
10. regenerate `RECORD` and repack the wheel;
11. verify metadata, runtime payload, license texts and runtime ownership.

An existing upstream wheel can be patched directly:

```bash
uv run python scripts/patch_weasyprint_wheel.py \
  --wheel downloads/weasyprint/weasyprint-69.0-py3-none-any.whl \
  --licenses _build/licenses \
  --platform-tag manylinux_2_28_x86_64
```

The default runtime source is `_build/runtime` and the default output directory
is `dist`.
