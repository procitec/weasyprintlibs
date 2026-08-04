# Third-party libraries

The generated wheels redistribute native libraries. The table below documents the explicitly configured rendering stack. Versions must remain synchronized with `config/libraries.toml` and the Windows package lock.

| Component | Version in current Linux configuration | License identifier / family | Notes |
|---|---:|---|---|
| zlib | 1.3.1 | Zlib | Preserve the upstream notice. |
| libffi | 3.5.0 | MIT | Preserve copyright and permission notice. |
| PCRE2 | 10.47 | BSD-3-Clause | Verify the exact upstream COPYING text. |
| Expat | 2.8.2 | MIT | Preserve copyright and permission notice. |
| GLib | 2.84.4 | LGPL-2.1-or-later | Shared-library redistribution and corresponding-source obligations apply. |
| libpng | 1.6.50 | libpng-2.0 | Preserve the upstream license and notices. |
| FreeType | 2.13.3 | FTL OR GPL-2.0-only | The build should document which licensing option is relied upon; FTL is commonly selected for binary redistribution. |
| Fontconfig | 2.17.1 | MIT | Preserve copyright and permission notice. |
| Pixman | 0.46.4 | MIT | Preserve copyright and permission notice. |
| Cairo | 1.18.4 | LGPL-2.1-or-later OR MPL-1.1 | Document the chosen redistribution basis. |
| FriBidi | 1.0.16 | LGPL-2.1-or-later | Corresponding-source obligations apply. |
| HarfBuzz | 14.2.1 | MIT | The exact COPYING file contains multiple copyright notices. |
| Pango | 1.58.0 | LGPL-2.1-or-later | Corresponding-source obligations apply. |

## Important limitations

This table is not a substitute for the complete license texts and notices from the exact source releases.

The Windows wheel is assembled from a transitive MSYS2 dependency closure and may contain additional runtime DLLs. Review every package in `config/windows-packages.lock.toml` and every DLL staged into the wheel. Add all additional components and their notices before release.

## Packaging recommendation

Store exact upstream license files under a structure such as:

```text
licenses/
  zlib/LICENSE
  libffi/LICENSE
  pcre2/COPYING
  expat/COPYING
  glib/COPYING
  libpng/LICENSE
  freetype/FTL.TXT
  fontconfig/COPYING
  pixman/COPYING
  cairo/COPYING-LGPL-2.1
  cairo/COPYING-MPL-1.1
  fribidi/COPYING
  harfbuzz/COPYING
  pango/COPYING
```

Include this directory in both the source distribution and built wheels. Prefer copying these files from the exact downloaded source archives during staging, so the notices cannot drift from the bundled versions.
