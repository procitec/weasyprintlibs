param(
    [string]$WeasyPrintVersion = "69.0",
    [ValidateSet("x86_64", "arm64")]
    [string]$Profile = "x86_64"
)

$ErrorActionPreference = "Stop"

uv sync --frozen
uv run python scripts/runtime_config.py --check
uv run python scripts/fetch_windows_packages.py --profile $Profile --locked
uv run python scripts/extract_windows_packages.py --profile $Profile
uv run python scripts/stage_windows_wheel.py --profile $Profile

$platformTag = uv run python scripts/windows_config.py `
    --profile $Profile `
    --field platform_tag

Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
uv run python scripts/patch_weasyprint_wheel.py `
    --version $WeasyPrintVersion `
    --platform-tag $platformTag.Trim()
