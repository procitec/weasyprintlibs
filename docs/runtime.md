# Embedded native runtime

The runtime is embedded below `weasyprint/_weasyprint_libs`. The patched
`weasyprint/__init__.py` calls `_weasyprint_libs_loader.activate()` before the
normal WeasyPrint imports continue.

## Source and generated files

The maintained loader source is:

```text
runtime/loader.py
```

The central runtime configuration is:

```text
config/runtime-libraries.toml
```

During wheel patching they become:

```text
weasyprint/_weasyprint_libs_loader.py
weasyprint/_weasyprint_libs_config.py
```

No standalone Python package or `.pth` activation file is involved.

## Staging

All platforms stage their payload in:

```text
_build/runtime/
  lib/ or bin/
  etc/
  share/
```

Linux uses `$ORIGIN` RPATHs. macOS rewrites install names to
`@loader_path/<name>`. Windows registers the embedded `bin` directory with
`os.add_dll_directory` before preloading the configured entry DLLs.

Fontconfig is pointed at the embedded configuration and an embedded cache
location through `FONTCONFIG_FILE`, `FONTCONFIG_PATH` and `XDG_CACHE_HOME`.

## Avoiding mixed runtimes

Pango, HarfBuzz, HarfBuzz subset, Fontconfig and FreeType are explicitly part of
the configured runtime entry set. The Linux integration test inspects
`/proc/<pid>/maps` and rejects system copies of these libraries after rendering
a PDF.

The CFFI alias map is used on macOS because WeasyPrint probes several Linux,
Windows and macOS library names. Known aliases are redirected to absolute paths
inside the embedded runtime.
