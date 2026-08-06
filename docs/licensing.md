# Licensing and redistribution

## Project and bundled code

The repository's own Python code, build scripts and documentation are licensed
under MIT as stated in the root `LICENSE` file. Native libraries bundled into a
patched WeasyPrint wheel are not relicensed and remain subject to their
upstream terms.

The build therefore creates a platform-specific license bundle and embeds it
into the wheel. A successful build contains:

```text
weasyprint-<bundled-version>.dist-info/licenses/
  PROJECT_LICENSE.txt
  THIRD_PARTY_LICENSES.md
  manifest.json
  texts/<component>/...
```

A matching `dist/third-party-licenses-<platform-tag>.zip` is produced for CI
artifacts and GitHub releases.

## Source of truth

The generated Markdown summary is not maintained manually. `manifest.json` and
the copied texts are derived from the exact build inputs:

### Linux source archives

Each `[[library]]` entry in `config/libraries.toml` declares:

- `license_expression`;
- `license_files`, relative to the archive root;
- `runtime_patterns`, relative to `_build/runtime`;
- an optional `redistribution_license`;
- whether corresponding source is required.

The collector verifies every downloaded archive against
`config/source-lock.generated.toml`, copies the configured texts directly from
that archive and maps every staged ELF shared library to one component.

Changing a library version must include reviewing these fields. A missing text,
source-lock mismatch or unowned `.so` stops the build.

### Windows MSYS2 packages

Windows staging does not copy every DLL from the resolved MSYS2 package set.
It starts with the entry DLLs in `config/runtime-libraries.toml`, reads their PE
import tables and recursively stages only MSYS2 DLL dependencies. Windows
system DLLs are left to the operating system. Tools and unrelated libraries,
such as Tcl/Tk pulled into the package cache by another tool, do not become
part of the wheel merely because their package was downloaded.

The license collector reads each locked `.pkg.tar.zst` archive. It uses the
archive's `.PKGINFO` license declarations, copies files installed below
`share/licenses` or matching license/notice names below `share/doc`, and maps
each staged DLL back to the package archive that contained it. Only packages
that contributed a staged DLL are included.

Some MSYS2 binary packages declare a license but do not install its text. For
these cases, `config/windows-packages.toml` can contain a version-bound
`[[windows.license_fallback]]`. The collector downloads the declared upstream
source, verifies its SHA-256 checksum and copies only the configured license
files. A package update invalidates the fallback until its version, checksum
and license paths are reviewed. Without an installed text or a matching
fallback, the build still fails.

A general MSYS2 or MinGW-w64 license is not used as an umbrella license for
independent projects. Each staged DLL remains associated with its own upstream
package and license.

The MSYS2 binary-package URL is not automatically a complete corresponding
source offer. Releases containing copyleft packages must still ensure that the
exact source is available for the required period and under the required
terms.

### macOS Homebrew kegs

The macOS staging script records the original Homebrew Cellar path for every
copied dylib in `_build/runtime-provenance.json`. The collector groups these
files by formula and keg version, reads `brew info --json=v2`, and copies
installed license or notice files from the keg. If a bottle did not install a
license text, the collector downloads the stable upstream source recorded by
the formula, verifies its SHA-256 checksum and extracts license-like files from
that exact archive.

A dylib outside the recorded Homebrew Cellar, missing formula metadata, a
version mismatch, an invalid source checksum or a source without a discoverable
license text stops the build.

## Build and verification

A complete build runs the following sequence:

```text
stage native runtime
→ map native files to their source/package/formula
→ collect and verify license texts
→ create the release license ZIP
→ embed the bundle into the wheel
→ verify wheel runtime and license mappings
```

The standalone commands are:

```bash
just licenses
just verify-licenses
just verify-wheel dist
```

`just verify-licenses` compares the generated manifest with the staged runtime.
`just verify-wheel` checks that the same runtime mapping and all copied texts
are present in the final wheel and listed in `RECORD`.

## Corresponding source

Several components use LGPL or other copyleft licenses. Keeping them as
separate shared libraries helps preserve replacement and relinking ability, but
does not by itself satisfy every redistribution obligation.

The generated manifest records exact source or package references and marks
components whose declared license may require corresponding source. For robust
long-term compliance, publish exact source archives for these components next
to the release rather than relying only on upstream URLs.

This document is an engineering checklist, not legal advice.
