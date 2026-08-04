param(
    [string]$WeasyPrintVersion = "69.0"
)

$ErrorActionPreference = "Stop"

uv sync --frozen
uv run python scripts/fetch_windows_packages.py --locked
uv run python scripts/extract_windows_packages.py
uv run python scripts/stage_windows_wheel.py

Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
uv run python scripts/patch_weasyprint_wheel.py `
    --version $WeasyPrintVersion `
    --platform-tag win_amd64
