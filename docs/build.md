# Project commands with `just`

The repository uses `just` as the public command interface. Build logic remains
in Python and can also be called directly with `uv run python -m scripts`.

List available recipes:

```bash
just
```

Common commands:

```bash
just check
just build
just build 69.0
just local-test
just verify-wheel dist
just clean
```

Windows profiles are regular recipe parameters:

```powershell
just build 69.0 x86_64
just windows-update-lock x86_64
```

On macOS, install the Homebrew runtime build dependencies before running the
build:

```bash
brew install pango
just build 69.0
```

## Build outputs

A successful build writes both artifacts to `dist/`:

```text
weasyprint-<version>-py3-none-<platform-tag>.whl
third-party-licenses-<platform-tag>.zip
```

The wheel contains the same license bundle below its `.dist-info/licenses/`
directory.

## License-only commands

After `_build/runtime` has been staged, the license inventory can be rebuilt
without rebuilding the wheel:

```bash
just licenses
just verify-licenses
```

The collector validates source/package checksums, copies exact license texts,
maps every native runtime file to its owner and creates the release ZIP. A
normal `just build` performs this automatically before patching the WeasyPrint
wheel.

## Responsibility split

- `justfile` contains short, discoverable user commands.
- `scripts/project.py` defines workflow ordering and cross-platform cleanup.
- `scripts/collect_licenses.py` selects the platform collector.
- `scripts/license_bundle.py` implements collection, manifest generation,
  archive creation and validation.
- Specialized scripts continue to implement ELF, Mach-O, PE/MSYS2, wheel and
  runtime details.
- GitHub Actions calls the same `just` recipes as local development and uploads
  the wheel together with its matching license archive.

This avoids duplicating workflow order in a Makefile, Bash scripts, PowerShell
scripts and CI YAML while keeping platform-specific binary logic isolated.
