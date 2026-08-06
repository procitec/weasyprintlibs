# Third-party licenses

The generated WeasyPrint wheels redistribute native libraries. Their license
inventory is generated separately for every platform build from the exact
sources that contributed files to the wheel.

## Generated artifacts

Every successful build creates:

```text
_build/licenses/
  PROJECT_LICENSE.txt
  THIRD_PARTY_LICENSES.md
  manifest.json
  texts/<component>/...

dist/third-party-licenses-<platform-tag>.zip
```

The same directory is embedded into the wheel below
`weasyprint-<version>.dist-info/licenses/`. The ZIP file is uploaded next to the
wheel in CI and attached to GitHub releases.

`manifest.json` maps each packaged `.so`, `.dll`, `.dylib` or diagnostic
executable to the source archive, MSYS2 package or Homebrew formula that
provided it. The build fails if a native runtime file has no owner or a
contributing component has no copied license text.

## Platform sources

- **Linux:** license expressions, exact license paths and runtime patterns are
  declared beside each component in `config/libraries.toml`. Texts are copied
  from the downloaded source archives after their SHA-256 values are checked
  against `config/source-lock.generated.toml`.
- **Windows:** only the recursive PE dependency closure of the configured entry
  DLLs is staged. Ownership, package versions, declared licenses and installed
  license texts are read from the locked MSYS2 package archives. A package that
  installs no text may use a version- and checksum-bound upstream source
  fallback declared in `config/windows-packages.toml`.
- **macOS:** Dylib ownership is recorded while staging the Homebrew runtime.
  Formula metadata and installed license files are then collected from the
  exact Homebrew kegs that supplied the libraries. If a keg contains no license
  text, the checksummed upstream source recorded by the formula is used as a
  fallback.

## Commands

After staging a runtime, regenerate and verify its license bundle with:

```bash
just licenses
just verify-licenses
```

A normal `just build` performs these steps automatically.

## Scope

The repository's own code and documentation are licensed under MIT. Bundled
native libraries retain their respective upstream licenses. The generated
inventory and copied texts support redistribution review but do not replace a
legal assessment or any required corresponding-source publication.
