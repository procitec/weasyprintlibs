$ErrorActionPreference = "Stop"

uv sync --frozen
uv run python scripts/fetch_windows_packages.py --locked
uv run python scripts/extract_windows_packages.py
uv run python scripts/stage_windows_wheel.py

$env:WHEEL_PLATFORM_TAG = "win_amd64"
uv build --wheel
