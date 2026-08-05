#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script must run on macOS." >&2
  exit 1
fi

case "$(uname -m)" in
  arm64)
    platform_tag="macosx_11_0_arm64"
    expected_arch="arm64"
    ;;
  x86_64)
    platform_tag="macosx_11_0_x86_64"
    expected_arch="x86_64"
    ;;
  *)
    echo "Unsupported macOS architecture: $(uname -m)" >&2
    exit 1
    ;;
esac

command -v brew >/dev/null || {
  echo "Homebrew is required to build the macOS runtime." >&2
  exit 1
}

brew list --versions pango >/dev/null 2>&1 || brew install pango
uv sync --frozen
uv run python scripts/stage_macos_wheel.py
rm -rf dist
WHEEL_PLATFORM_TAG="${platform_tag}" uv build --wheel
uv run python scripts/verify_pth_wheel.py
wheel="$(find dist -maxdepth 1 -name '*.whl' -print -quit)"
uv run python scripts/verify_macos_wheel.py "${wheel}" --arch "${expected_arch}"
