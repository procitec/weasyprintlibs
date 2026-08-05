param(
    [string]$WeasyPrintVersion = "69.0",
    [ValidateSet("x86_64", "arm64")]
    [string]$Profile = "x86_64",
    [string]$PythonVersion = "3.13"
)

$ErrorActionPreference = "Stop"

./scripts/build_windows.ps1 `
    -WeasyPrintVersion $WeasyPrintVersion `
    -Profile $Profile

uv run python scripts/test_patched_wheel.py `
    --wheel dist `
    --python $PythonVersion
