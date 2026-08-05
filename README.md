# Bundled WeasyPrint wheels

This repository builds platform-specific `weasyprint` wheels that contain the
native Pango, HarfBuzz, Fontconfig, FreeType and Cairo runtime required by
WeasyPrint.
Importing `weasyprint` activates the runtime embedded below
`weasyprint/_weasyprint_libs` before WeasyPrint loads its native dependencies.

## Supported wheels

| Platform | Wheel tag | Native source |
|---|---|---|
| Linux x86-64 | `manylinux_2_28_x86_64` | Libraries built from pinned source archives |
| Windows x86-64 | `win_amd64` | Locked MSYS2/MinGW runtime packages |
| macOS Apple Silicon | `macosx_11_0_arm64` | Relocated Homebrew runtime |
| macOS Intel | `macosx_11_0_x86_64` | Relocated Homebrew runtime |

The generated version uses a PEP 440 local version identifier, for example:

```text
weasyprint-69.0+bundled.26.1.1-py3-none-manylinux_2_28_x86_64.whl
```

## Build

```bash
just build "69.0" x86_64
```

Generated wheels are written to `dist/`.

## Local tests

Fast source and build-logic tests:

```bash
just check
```

Build the complete Linux wheel, install it into a clean virtual environment and
render the test document without `full_fonts=True`:

```bash
make test-unit
```

Test an already built wheel without rebuilding the native stack:

```bash
make test-wheel
```

## Documentation

- [Build and test workflow](docs/build.md)
- [Wheel layout and patching](docs/weasyprint-wheel.md)
- [Runtime activation](docs/runtime.md)
- [macOS wheels](docs/macos.md)
- [Licensing and redistribution](docs/licensing.md)
- [Bundled third-party libraries](THIRD_PARTY_LICENSES.md)

## License

The project-specific Python and build code is licensed under the [MIT License](LICENSE).
Bundled third-party libraries retain their respective licenses; see
[THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).
