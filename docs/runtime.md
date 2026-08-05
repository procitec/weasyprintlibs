# Runtime activation and maintenance

## Automatic activation

The standalone runtime wheel contains a top-level `.pth` file:

```text
weasyprint_libs.pth
```

It imports `weasyprint_libs.activate()` during Python site initialization. The
direct WeasyPrint wheel instead inserts the same loader into the `weasyprint`
package and calls it before the normal WeasyPrint imports. Both variants use the
same loader implementation and generated runtime configuration.

The activation function is idempotent and keeps native library and DLL-directory
handles alive for the complete Python process.

## Central runtime configuration

Runtime entry libraries, macOS CFFI aliases and macOS staging seed patterns are
defined once in:

```text
config/runtime-libraries.toml
```

The checked-in Python module is generated from this file:

```text
src/weasyprint_libs/_weasyprint_libs_config.py
```

Regenerate and verify it with:

```bash
uv run python scripts/runtime_config.py
uv run python scripts/runtime_config.py --check
```

Build staging fails when the generated module is stale. The direct WeasyPrint
wheel receives both `_weasyprint_libs_loader.py` and
`_weasyprint_libs_config.py`, so it does not maintain a second library list.

## Why a runtime bootstrap remains necessary

WeasyPrint opens native libraries dynamically through CFFI. The library names
therefore do not appear as normal linked dependencies of a Python extension.
Wheel repair tools can copy, relocate and inspect native binaries, but they
cannot infer every CFFI entry library or the required activation time from the
upstream pure-Python wheel.

The project consequently uses a hybrid model:

1. build and staging code collects the complete native dependency closure;
2. platform tools patch native loader metadata where applicable;
3. `verify_runtime_payload.py` checks the required entry libraries and binary
   architecture;
4. a small Python bootstrap registers or preloads only the configured entry
   libraries;
5. WeasyPrint continues with its normal CFFI loading.

The bootstrap must not grow into a wheel-repair implementation. Dependency
collection, binary rewriting, architecture checking and wheel metadata changes
belong in build scripts and platform tools.

## Linux

Before loading Fontconfig, Pango or Cairo, the loader configures:

```text
FONTCONFIG_FILE
FONTCONFIG_PATH
XDG_CACHE_HOME
```

All bundled ELF libraries must use a relative runtime path such as `$ORIGIN`, so
transitive dependencies in the same package directory are resolved without
system copies. `scripts/patch_rpath.py` performs this relocation.

Avoid mixing bundled and system copies of GLib, Fontconfig, FreeType, HarfBuzz,
Cairo and Pango. ABI conflicts can otherwise appear as font lookup failures or
process crashes.

## Windows

The loader:

1. locates the packaged `bin` directory;
2. registers it with `os.add_dll_directory()`;
3. preserves the returned directory handle;
4. preloads the configured CFFI entry DLLs in a deterministic order.

The staged runtime keeps the MSYS2 prefix layout (`bin`, `etc`, `share`) so
Fontconfig can find its bundled configuration relative to that prefix.

The DLL names in `runtime-libraries.toml` are architecture-neutral. The selected
Windows build profile decides whether the files contain x86-64 or ARM64 code.
The payload verifier reads the PE machine field and rejects mismatched binaries.

## macOS

Homebrew libraries are collected from configured seed patterns and their
transitive `otool -L` dependencies. Each bundled dylib is rewritten to use
`@loader_path` references and receives an ad-hoc signature.

Some CFFI names used by WeasyPrint follow Linux or Windows naming conventions.
The configured alias map redirects only these known names to absolute paths in
the bundled `lib` directory. The required dylibs are preloaded with global
symbol visibility before WeasyPrint imports them.

## Payload validation

Staging scripts invoke the verifier automatically. It can also be run manually:

```bash
uv run python scripts/verify_runtime_payload.py \
  --platform linux \
  --architecture x86_64
```

Windows example:

```powershell
uv run python scripts/verify_runtime_payload.py `
  --platform windows `
  --architecture x86_64
```

The verifier checks the central entry-library list, the bundled Fontconfig
configuration and, where requested, native binary architecture.

## Diagnostic checks

Linux dependency metadata:

```bash
readelf -d path/to/library.so | grep -E 'NEEDED|RPATH|RUNPATH|SONAME'
```

Resolved Linux dependencies:

```bash
LD_LIBRARY_PATH=path/to/weasyprint_libs/lib \
ldd path/to/weasyprint_libs/lib/libpango-1.0.so.0
```

Wheel contents:

```bash
python -m zipfile -l dist/*.whl
```
