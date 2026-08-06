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
weasyprint-69.0+bundled.<release>-py3-none-manylinux_2_28_x86_64.whl
```

## Build

```bash
just build "69.0" x86_64
```

Generated wheels and matching `third-party-licenses-<platform-tag>.zip` archives are
written to `dist/`. The same license bundle is embedded in the wheel under
`.dist-info/licenses/`.

## Local tests

Fast source and build-logic tests:

```bash
just check
```

Build the complete Linux wheel, install it into a clean virtual environment and
render the test document without `full_fonts=True`:

```bash
just local-test
```

Test an already built wheel without rebuilding the native stack:

```bash
just test-wheel
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
Bundled third-party libraries retain their respective licenses. Their exact
platform-specific texts and runtime mappings are generated during every build;
see [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).
