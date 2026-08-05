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

## Responsibility split

- `justfile` contains short, discoverable user commands.
- `scripts/project.py` defines workflow ordering and cross-platform cleanup.
- Specialised scripts continue to implement ELF, Mach-O, PE/MSYS2, wheel and
  runtime details.
- GitHub Actions should call the same `just` recipes as local development.

This avoids duplicating workflow order in a Makefile, Bash scripts, PowerShell
scripts and CI YAML while keeping platform-specific binary logic isolated.
