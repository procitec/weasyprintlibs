# macOS wheels

The macOS build uses Homebrew only as the source of the native runtime. Users of the generated wheel do not need Homebrew or a separately installed Pango stack.

Two architecture-specific wheels are produced:

| Architecture | Wheel tag | GitHub runner |
|---|---|---|
| Apple Silicon | `macosx_11_0_arm64` | `macos-15` |
| Intel | `macosx_11_0_x86_64` | `macos-15-intel` |

## Staging process

`scripts/stage_macos_wheel.py` performs these steps:

1. locate the Pango, Cairo, Fontconfig, FreeType and HarfBuzz seed libraries;
2. read their Mach-O dependencies recursively with `otool -L`;
3. copy every Homebrew dependency into `_build/runtime/lib`;
4. record each copied dylib's original Cellar path in
   `_build/runtime-provenance.json` for license collection;
5. replace Homebrew install names with `@loader_path/<name>`;
6. set each bundled dylib ID to `@loader_path/<name>`;
7. ad-hoc sign the modified dylibs;
8. copy Fontconfig configuration and install a relocatable `fonts.conf`.

Dependencies from `/usr/lib` and `/System/Library` remain system dependencies. Any other dependency outside the Homebrew prefix causes the build to fail.

## Verification

`scripts/verify_macos_wheel.py` checks every bundled dylib for:

- the expected CPU architecture;
- absence of `/opt/homebrew`, `/usr/local/Cellar`, and `/usr/local/opt` references;
- only `@loader_path`, `/usr/lib`, or `/System/Library` dependencies.

The GitHub runtime tests unlink the Homebrew libraries before rendering a PDF. This prevents an incomplete wheel from silently using the build host's Pango installation.

The license collector groups the provenance records by Homebrew keg, copies
installed license files where available, and otherwise downloads the exact
checksummed upstream source declared by the formula to extract the license
texts.
