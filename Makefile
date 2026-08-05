UV ?= uv
PLATFORM_TAG ?= manylinux_2_28_x86_64
WEASYPRINT_VERSION ?= 69.0
WINDOWS_PROFILE ?= x86_64
TEST_PYTHON_VERSION ?= 3.13

UV_RUN := $(UV) run
RUFF ?= $(UV) tool run --from ruff==0.16.1 ruff
WINDOWS_PLATFORM_TAG = $(shell $(UV_RUN) python scripts/windows_config.py --profile $(WINDOWS_PROFILE) --field platform_tag)

.PHONY: sync lock format check ruff-format ruff-check ruff-fix \
	runtime-config-check fetch source-lock native-build stage wheel \
	verify-sources verify-runtime verify-wheel test test-unit local-test \
	local-test-wheel local-test-clean clean distclean

sync:
	$(UV) sync

lock:
	$(UV) lock

format: ruff-format

check: ruff-check runtime-config-check test-unit

ruff-format:
	$(RUFF) format .

ruff-check:
	$(RUFF) format --check .
	$(RUFF) check .

ruff-fix:
	$(RUFF) check --fix .
	$(RUFF) format .

runtime-config-check:
	$(UV_RUN) python scripts/runtime_config.py --check

fetch:
	$(UV_RUN) python scripts/fetch_sources.py

source-lock:
	$(UV_RUN) python scripts/fetch_sources.py --write-lock

native-build: fetch
	$(UV_RUN) python scripts/build.py --clean

stage: runtime-config-check
	$(UV_RUN) python scripts/stage_wheel.py
	$(UV_RUN) python scripts/patch_rpath.py _build/runtime/lib

wheel: native-build stage
	rm -rf dist
	$(UV_RUN) python scripts/patch_weasyprint_wheel.py \
		--version $(WEASYPRINT_VERSION) \
		--platform-tag $(PLATFORM_TAG)
	$(MAKE) verify-wheel

verify-sources:
	$(UV_RUN) python scripts/fetch_sources.py

verify-runtime:
	$(UV_RUN) python scripts/verify_runtime_payload.py \
		--root _build/runtime \
		--platform linux

verify-wheel:
	$(UV_RUN) python scripts/verify_patched_weasyprint_wheel.py dist

# Fast tests that do not build the native stack.
test-unit:
	$(UV) run --with pytest==8.4.2 python -m pytest tests/unit -v

test: check

# Full local integration test: build the patched wheel, install it into a new
# virtual environment and render the real two-page test document.
local-test:
	$(MAKE) wheel
	$(MAKE) local-test-wheel

# Test an already built wheel without rebuilding the native stack.
local-test-wheel: verify-wheel
	$(UV_RUN) python scripts/test_patched_wheel.py \
		--wheel dist \
		--python $(TEST_PYTHON_VERSION)

local-test-clean:
	rm -rf .test-venv tests/runtime/_output_direct tests/sphinx-simplepdf-demo/_output_direct

clean: local-test-clean
	rm -rf _build dist

distclean: clean
	rm -rf .venv .uv-cache downloads/current downloads/weasyprint

.PHONY: windows-update-lock windows-fetch windows-extract windows-stage \
	windows-wheel

windows-update-lock:
	$(UV_RUN) python scripts/fetch_windows_packages.py --profile $(WINDOWS_PROFILE) --update-lock

windows-fetch:
	$(UV_RUN) python scripts/fetch_windows_packages.py --profile $(WINDOWS_PROFILE) --locked

windows-extract: windows-fetch
	$(UV_RUN) python scripts/extract_windows_packages.py --profile $(WINDOWS_PROFILE)

windows-stage: runtime-config-check windows-extract
	$(UV_RUN) python scripts/stage_windows_wheel.py --profile $(WINDOWS_PROFILE)

windows-wheel: windows-stage
	rm -rf dist
	$(UV_RUN) python scripts/patch_weasyprint_wheel.py \
		--version $(WEASYPRINT_VERSION) \
		--platform-tag $(WINDOWS_PLATFORM_TAG)
	$(MAKE) verify-wheel

MACOS_ARCH := $(shell uname -m)
ifeq ($(MACOS_ARCH),arm64)
MACOS_PLATFORM_TAG := macosx_11_0_arm64
else ifeq ($(MACOS_ARCH),x86_64)
MACOS_PLATFORM_TAG := macosx_11_0_x86_64
else
MACOS_PLATFORM_TAG := unsupported
endif

.PHONY: macos-stage macos-wheel macos-verify

macos-stage: runtime-config-check
	$(UV_RUN) python scripts/stage_macos_wheel.py

macos-wheel: macos-stage
	rm -rf dist
	$(UV_RUN) python scripts/patch_weasyprint_wheel.py \
		--version $(WEASYPRINT_VERSION) \
		--platform-tag $(MACOS_PLATFORM_TAG)
	$(MAKE) verify-wheel
	$(MAKE) macos-verify

macos-verify:
	$(UV_RUN) python scripts/verify_macos_wheel.py \
		$$(find dist -maxdepth 1 -name 'weasyprint-*.whl' -print -quit) \
		--arch $(MACOS_ARCH)
