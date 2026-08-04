# Licensing and redistribution

## Project license

The repository's own Python code, build scripts and documentation are licensed under MIT as stated in the root `LICENSE` file.

This does not relicense bundled third-party libraries. Each native component remains subject to its upstream license.

## What should be distributed

For binary wheels containing third-party libraries, include at least:

1. the project's MIT license;
2. a list of bundled components, versions and licenses;
3. required copyright and attribution notices;
4. the applicable license texts;
5. information required by copyleft licenses, including access to the corresponding source and relinking/replacement rights where applicable.

A short SPDX table is useful for orientation but is not always sufficient on its own.

## LGPL libraries

Several bundled libraries use LGPL licenses. Shipping them as separate shared libraries normally preserves the user's ability to replace or relink them, but distributors must still satisfy the exact license obligations. Keep the unmodified shared-library form and provide the applicable LGPL text and corresponding-source information.

Do not state that the complete wheel is MIT-licensed without qualification. A more accurate statement is:

> Project-specific code is MIT licensed. Bundled native libraries are redistributed under their respective licenses.

## Source availability

The repository records source URLs, versions and checksums in `config/libraries.toml`. Release artifacts should retain enough information for recipients to obtain the exact corresponding source for bundled copyleft components.

For long-term or offline compliance, consider publishing a source archive bundle alongside each wheel rather than relying only on upstream URLs.

## Windows package closure

The Windows wheel is assembled from a transitive MSYS2 package closure. Its contents may include additional libraries beyond the explicitly configured rendering stack. Therefore the third-party report must be regenerated or reviewed whenever `config/windows-packages.lock.toml` changes.

## Recommended release check

Before publishing a wheel:

```text
- inspect all packaged .so and .dll files;
- map each file to its source package and version;
- verify the upstream license from the exact source/package revision;
- include required license and notice files in the wheel;
- verify corresponding-source availability for LGPL components;
- review the Windows transitive package closure separately.
```

This document is an engineering checklist, not legal advice.
