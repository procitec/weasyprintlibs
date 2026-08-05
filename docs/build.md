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
