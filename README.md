# WeasyPrint native libraries

Platform wheels containing the native libraries required by WeasyPrint.

The package installs a `.pth` file that activates the bundled runtime automatically when Python starts. Applications can therefore use WeasyPrint normally without calling a separate loader function.

## Supported wheels

| Platform | Wheel tag | Native source |
|---|---|---|
| Linux x86-64 | `manylinux_2_28_x86_64` | Libraries built from pinned source archives |
| Windows x86-64 | `win_amd64` | Locked MSYS2/MinGW runtime packages |

The Linux baseline targets glibc 2.28 and newer systems, including RHEL/Rocky Linux 8 and later.

## Build

Linux:

```bash
make wheel
```

Windows:

```powershell
.\scripts\build_windows.ps1
```

Generated wheels are written to `dist/`.

## Test locally

```bash
make local-test
```

On Windows:

```powershell
.\scripts\test_local.ps1
```

The complete platform matrix is tested by GitHub Actions on Ubuntu, Rocky Linux 8/9 and Windows.

## Documentation

- [Installation and use](docs/usage.md)
- [Build and test workflow](docs/build.md)
- [Runtime activation](docs/runtime.md)
- [Licensing and redistribution](docs/licensing.md)
- [Bundled third-party libraries](THIRD_PARTY_LICENSES.md)

## License

The project-specific Python and build code is licensed under the [MIT License](LICENSE).

The wheel also redistributes third-party native libraries under their respective licenses. See [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md). The MIT license of this repository does not replace those licenses.
