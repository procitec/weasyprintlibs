# Public project commands. The actual orchestration lives in scripts/project.py.
set dotenv-load := true
set shell := ["sh", "-uc"]
set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

uv := env_var_or_default("UV", "uv")

# List available commands.
default:
    @just --list

# Synchronise the development environment.
sync:
    {{uv}} sync

# Reproduce the committed environment without changing uv.lock.
sync-frozen:
    {{uv}} sync --frozen

# Refresh uv.lock.
lock:
    {{uv}} lock

# Format Python files.
format:
    {{uv}} run python -m scripts format

# Run lint, format, configuration and unit checks.
check:
    {{uv}} run python -m scripts check

# Download and verify native source archives.
fetch:
    {{uv}} run python -m scripts fetch

# Record observed source archive checksums.
source-lock:
    {{uv}} run python -m scripts fetch --write-lock

# Build the native Linux stack.
native-build:
    {{uv}} run python -m scripts native-build

# Stage the native runtime for the current platform.
stage profile="x86_64":
    {{uv}} run python -m scripts stage --profile "{{profile}}"

# Collect exact third-party license texts for the staged runtime.
licenses profile="x86_64":
    {{uv}} run python -m scripts licenses --profile "{{profile}}"

# Verify a generated third-party license bundle.
verify-licenses path="_build/licenses":
    {{uv}} run python -m scripts verify-licenses "{{path}}" --runtime _build/runtime

# Build and verify a bundled WeasyPrint wheel for the current platform.
build version="69.0" profile="x86_64":
    {{uv}} sync --frozen
    {{uv}} run python -m scripts build --version "{{version}}" --profile "{{profile}}"

# Build with an explicit wheel platform tag.
build-tag version tag profile="x86_64":
    {{uv}} sync --frozen
    {{uv}} run python -m scripts build --version "{{version}}" --profile "{{profile}}" --platform-tag "{{tag}}"

# Compatibility alias for the former Make target.
wheel version="69.0" profile="x86_64":
    just build "{{version}}" "{{profile}}"

# Verify downloaded native source archives.
verify-sources:
    {{uv}} run python -m scripts verify-sources

# Verify the staged runtime for the current platform.
verify-runtime:
    {{uv}} run python -m scripts verify-runtime

# Verify a generated wheel or a directory containing one wheel.
verify-wheel path="dist":
    {{uv}} run python -m scripts verify-wheel "{{path}}"

# Run fast tests without compiling the native stack.
test-unit:
    {{uv}} run python -m scripts test-unit

# Install an existing wheel into a clean venv and render the test document.
test-wheel wheel="dist" python="3.13":
    {{uv}} run python -m scripts test-wheel --wheel "{{wheel}}" --python "{{python}}"

# Build a wheel and run the clean-environment document test.
local-test version="69.0" profile="x86_64" python="3.13":
    just build "{{version}}" "{{profile}}"
    just test-wheel dist "{{python}}"

# Update the selected Windows package lock intentionally.
windows-update-lock profile="x86_64":
    {{uv}} run python -m scripts windows-update-lock --profile "{{profile}}"

# Print the automatically selected wheel platform tag.
platform-tag profile="x86_64":
    {{uv}} run python -m scripts platform-tag --profile "{{profile}}"

# Remove build and local test outputs.
clean:
    {{uv}} run python -m scripts clean

# Also remove environments and download caches.
distclean:
    {{uv}} run python -m scripts clean --all
