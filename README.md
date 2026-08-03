# WeasyPrint native libraries superbuild 2026.1

Reproducible native Linux stack for WeasyPrint 69.0, built for the
`manylinux_2_28_x86_64` ABI baseline. This baseline targets RHEL 8 and newer
Linux systems using glibc.

## Native stack

- zlib 1.3.1
- libffi 3.5.0
- PCRE2 10.47
- Expat 2.8.2
- GLib 2.84.4
- libpng 1.6.50
- FreeType 2.13.3
- Fontconfig 2.17.1
- Pixman 0.46.4
- Cairo 1.18.4
- FriBidi 1.0.16
- HarfBuzz 14.2.1
- Pango 1.58.0

The source URLs, checksums, build order and native build options are stored in
`config/libraries.toml`.

## Prerequisites

The Python environment and Python-based build tools are managed by `uv`.
Native tools must be installed by the operating system:

```text
autoconf automake libtool make gcc gcc-c++ cmake pkg-config
bison flex gperf gettext curl xz bzip2 tar patchelf
```

Meson and Ninja are installed into `.venv` from the `native-build` dependency
group in `pyproject.toml`.

## Initial setup

```bash
uv lock
uv sync
```

`uv run` automatically uses the project environment. After the first successful `uv sync`, commit the generated `uv.lock`. It then controls the Meson and Ninja versions used by the build.

## Complete local build

```bash
make wheel
```

This is equivalent to:

```bash
uv run python scripts/fetch_sources.py
uv run python scripts/build.py --clean
uv run python scripts/stage_wheel.py
uv run python scripts/patch_rpath.py
WHEEL_PLATFORM_TAG=manylinux_2_28_x86_64 uv build --wheel
```

The resulting wheel is written to `dist/`.

The native work directory is `_build/`. It is deliberately not named `build/`,
so it cannot shadow Python's former `build` package.

## Source downloads and checksums

Source archives are downloaded on demand into `downloads/current/`:

```bash
make source-lock
```

This writes the observed SHA-256 values to
`config/source-lock.generated.toml`. Replace remaining
`checksum = "unlocked"` entries in `config/libraries.toml` with these fixed
values before publishing a release.

The zlib source uses the upstream `zlib-1.3.1.tar.gz` archive. Expat is built
from the extraction root and does not use an additional `source_subdir`.

## Manylinux container

```bash
docker build \
  -f containers/Dockerfile.manylinux_2_28 \
  -t weasyprintlibs-2026.1 .

docker run --rm \
  -v "$PWD:/io" \
  -w /io \
  weasyprintlibs-2026.1 \
  make wheel
```

The container installs `uv` and the native build prerequisites, including
`gperf`. `uv sync` is performed automatically by the first `uv run` command.

## Useful targets

```bash
make lock          # update uv.lock
make sync          # create/update .venv and uv.lock
make fetch         # download and verify native source archives
make source-lock   # additionally record observed SHA-256 sums
make native-build  # build the complete native stack
make stage         # copy runtime files and patch ELF RPATH values
make wheel         # complete build and wheel creation
make clean         # remove generated native and wheel output
make distclean     # also remove .venv and downloaded source cache
```

## Windows status

This project currently contains only the Linux manylinux superbuild. A Windows
wheel must be created later from a separately version-locked MinGW/MSYS2 build
of the same native stack.

## Windows wheel from MSYS2/MinGW packages

The Windows path does not compile the native stack. It resolves and downloads
binary packages from the MSYS2 `mingw64` repository, records the complete
transitive package closure in a lock file, extracts it, and stages the runtime
DLLs into the same Python wheel package.

### Prerequisites

- Windows 10 or newer
- `uv`
- MSYS2 installed, normally at `C:\\msys64`
- An up-to-date MSYS2 package database for the explicit lock update

The normal locked build does not invoke Pacman. It only downloads the package
archives recorded in `config/windows-packages.lock.toml`.

### Create or update the Windows package lock

Run this explicitly when updating the Windows native stack:

```powershell
uv sync
uv run python scripts/fetch_windows_packages.py --update-lock
```

When Pacman is not found automatically:

```powershell
uv run python scripts/fetch_windows_packages.py `
  --update-lock `
  --pacman C:\msys64\usr\bin\pacman.exe
```

This command:

1. clears `downloads/windows/`,
2. lets Pacman resolve the complete dependency closure,
3. downloads all `*.pkg.tar.zst` files,
4. reads package names and versions from `.PKGINFO`,
5. writes URLs and SHA-256 values to
   `config/windows-packages.lock.toml`.

Commit the resulting lock file.

### Reproducible Windows build

```powershell
.\scripts\build_windows.ps1
```

Equivalent individual commands:

```powershell
uv sync --frozen
uv run python scripts/fetch_windows_packages.py --locked
uv run python scripts/extract_windows_packages.py
uv run python scripts/stage_windows_wheel.py
$env:WHEEL_PLATFORM_TAG = "win_amd64"
uv build --wheel
```

The result is written to `dist/` with the platform tag `win_amd64`.

### Windows package configuration

`config/windows-packages.toml` contains the Pacman entry packages and paths.
Pacman resolves all transitive dependencies. The explicit packages document the
important rendering components: Pango, Cairo, Fontconfig, FreeType, FriBidi,
GLib and HarfBuzz.

The staging script copies:

- all DLLs from the extracted `mingw64/bin`,
- `pango-view.exe` when present,
- Fontconfig configuration,
- Fontconfig and GLib runtime data.

Headers, import libraries, static libraries, pkg-config files and documentation
are not included in the wheel.

### Loader behavior

On Windows `weasyprintlibs_native.activate()`:

- adds the wheel's `bin` directory via `os.add_dll_directory()`,
- sets `WEASYPRINT_DLL_DIRECTORIES`,
- keeps the DLL-directory handle alive,
- preloads the core GLib, Fontconfig, Cairo, HarfBuzz and Pango DLLs,
- sets the bundled `FONTCONFIG_FILE` when available.

## GitHub Actions

Two workflows are included under `.github/workflows/`.

### Build wheels

`.github/workflows/build-wheels.yml` runs on pushes to `main`, pull requests,
version tags and manual dispatches.

- Linux is built inside `containers/Dockerfile.manylinux_2_28` on an Ubuntu
  GitHub runner. This keeps the glibc 2.28 ABI baseline independent of the
  host runner image.
- Windows is built natively on `windows-2025`. The locked MSYS2 archives are
  downloaded and extracted; MSYS2 itself is not required for the normal build.
- Both wheels are uploaded as GitHub Actions artifacts for 14 days.

The build workflow expects these files to be committed:

```text
uv.lock
config/windows-packages.lock.toml
```

For Linux source traceability, also commit:

```text
config/source-lock.generated.toml
```

### Update lockfiles

Run `.github/workflows/update-lockfiles.yml` manually from the Actions page.
It updates in parallel:

- `uv.lock`,
- `config/source-lock.generated.toml`,
- `config/windows-packages.lock.toml`.

The combined files are always uploaded as the `updated-lockfiles` artifact.
The workflow input `commit_changes` optionally commits and pushes the changes
to the selected branch. Direct pushing requires the workflow to have write
permission and the branch rules to permit GitHub Actions pushes.

The Windows update job installs an isolated MSYS2 environment through
`msys2/setup-msys2` and uses Pacman only to resolve and download the complete
MinGW package closure. Normal Windows wheel builds use only the committed lock.

### Native runner versus Docker

Use Docker for the Linux wheel. A native `ubuntu-*` build would inherit the
runner's newer glibc and could no longer be safely tagged
`manylinux_2_28_x86_64`. The existing Manylinux Dockerfile is the reproducible
ABI boundary.

Use the native Windows runner for the Windows wheel. Windows wheels do not use
a Manylinux-style baseline, and the package contents are already prebuilt
MinGW DLLs. Adding a Windows container would increase complexity without
improving compatibility with Windows 10.

## Setuptools work directory

`setup.cfg` redirects Setuptools' temporary `build/` directory to:

```text
_build/setuptools/
```

This keeps all generated native and Python build output under `_build/`.
