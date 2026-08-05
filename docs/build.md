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
  make wheel
```

`make wheel` performs the following steps:

1. download and verify source archives;
2. build the pinned native stack;
3. stage runtime libraries and data;
4. patch Linux runtime paths;
5. build the platform wheel;
6. verify the activation `.pth` file.

Useful targets:

```text
make sync          Create or update the uv environment
make fetch         Download and verify native sources
make source-lock   Record observed source checksums
make native-build  Build the Linux native stack
make stage         Stage package data and patch ELF paths
make wheel         Build the complete wheel
make local-test    Install and test the generated wheel locally
make clean         Remove generated build output
make distclean     Also remove environments and download caches
```

The pinned native source configuration is stored in `config/libraries.toml`.

## Windows wheel

Normal Windows builds use the committed MSYS2 package lock and do not resolve packages again:

```powershell
.\scripts\build_windows.ps1
```

Update the package closure only when intentionally changing the Windows native stack:

```powershell
uv sync
uv run python scripts/fetch_windows_packages.py --update-lock
```

Commit the resulting `config/windows-packages.lock.toml`.

## Runtime tests

The runtime tests install the generated wheel into a clean environment, install WeasyPrint and render a PDF without manually calling `activate()`.

GitHub Actions test:

- Ubuntu 24.04;
- Rocky Linux 8;
- Rocky Linux 9;
- Windows x86-64.
- MacOS x86-64.
- MacOS arm64.

A successful build on the build image alone is insufficient. The Rocky tests are important because they reveal accidental dependencies on newer system libraries.

## Runtime library configuration

The source build versions remain in `config/libraries.toml`. Runtime entry
libraries and loader aliases are maintained separately in
`config/runtime-libraries.toml` because source-project names and installed
binary names are not the same concept.

After changing runtime names or macOS aliases, regenerate the checked-in module:

```bash
make runtime-config
make runtime-config-check
```

`make check` includes the non-modifying generated-file check.

## Windows build profiles

Windows package sources are grouped into profiles in
`config/windows-packages.toml`. The current default and release profile is
`x86_64`:

```powershell
.\scripts\build_windows.ps1 -Profile x86_64
```

The scripts accept a profile consistently during lock generation, download,
extraction, staging and wheel tagging:

```powershell
uv run python scripts/fetch_windows_packages.py `
  --profile x86_64 `
  --update-lock
```

An `arm64` profile is prepared with the MSYS2 `clangarm64` package names and the
`win_arm64` wheel tag. It is not part of the release matrix yet. Before enabling
it, generate and commit `config/windows-packages-arm64.lock.toml`, build the
runtime, and execute the complete PDF smoke test on native Windows ARM64.
