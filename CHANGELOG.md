# Changelog

## [Unreleased]

## 26.1.2

- Removed the standalone `weasyprint-libs` wheel and `.pth` activation path.
- The build now produces only directly patched `weasyprint` wheels with bundled native libraries.
- Added local unit, wheel-verification and clean-environment document tests.
- changed platform specific script runners to `just`
- add complex html document for tests from [sphinx-simplepdf](https://github.com/useblocks/sphinx-simplepdf/tree/main/demo)

## 26.1.1

- Support for macos

## 26.1.0

- First release supporting windows and manylinux
