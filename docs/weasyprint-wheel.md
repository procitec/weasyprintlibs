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
  METADATA
  WHEEL
  RECORD
```

## Processing steps

1. build or extract the native runtime into `_build/runtime`;
2. download the exact upstream `py3-none-any` WeasyPrint wheel;
3. copy the staged runtime into `weasyprint/_weasyprint_libs`;
4. inject an early loader call into `weasyprint/__init__.py`;
5. render the runtime configuration from `config/runtime-libraries.toml`;
6. set the bundled local version and platform wheel tag;
7. regenerate `RECORD` and repack the wheel;
8. verify layout, metadata and runtime payload.

An existing upstream wheel can be patched directly:

```bash
uv run python scripts/patch_weasyprint_wheel.py \
  --wheel downloads/weasyprint/weasyprint-69.0-py3-none-any.whl \
  --platform-tag manylinux_2_28_x86_64
```

The default runtime source is `_build/runtime` and the default output directory
is `dist`.
