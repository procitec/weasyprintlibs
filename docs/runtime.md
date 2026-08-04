# Runtime activation

## Automatic activation

The wheel contains a top-level `.pth` file:

```text
weasyprint_libs.pth
```

Its purpose is to initialize the packaged native runtime during Python site initialization. The activation function is idempotent and keeps native library handles alive.

## Linux

Before loading Fontconfig, Pango or Cairo, the loader configures:

```text
FONTCONFIG_FILE
FONTCONFIG_PATH
XDG_CACHE_HOME
```

The bundled `fonts.conf` and its relative `conf.d` includes must be resolved from the installed package directory.

All bundled ELF libraries should use a relative runtime path such as `$ORIGIN`, so dependencies located in the same package directory are resolved without relying on system copies.

Avoid mixing bundled and system copies of GLib, Fontconfig, FreeType, HarfBuzz, Cairo and Pango. This can cause ABI conflicts that appear as font lookup failures or segmentation faults.

## Windows

The loader:

1. adds the packaged `bin` directory with `os.add_dll_directory()`;
2. preserves the directory handle;
3. configures Fontconfig;
4. loads the required runtime DLLs.

## Diagnostic checks

Linux dependency metadata:

```bash
readelf -d path/to/library.so | grep -E 'NEEDED|RPATH|RUNPATH|SONAME'
```

Resolved dependencies:

```bash
LD_LIBRARY_PATH=path/to/weasyprintlibs_native/lib \
ldd path/to/weasyprintlibs_native/lib/libpango-1.0.so.0
```

Wheel contents:

```bash
python -m zipfile -l dist/*.whl
```
