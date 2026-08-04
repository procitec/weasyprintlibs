UV ?= uv
PLATFORM_TAG ?= manylinux_2_28_x86_64
WEASYPRINT_VERSION ?= 69.0

UV_RUN := $(UV) run
RUFF ?= $(UV) tool run --from ruff==0.16.1 ruff
.PHONY: sync lock format check ruff-format ruff-check ruff-fix fetch source-lock native-build stage wheel patched-wheel verify verify-pth clean distclean

sync:
	$(UV) sync

lock:
	$(UV) lock

format: ruff-format

check: ruff-check

ruff-format:
	$(RUFF) format .

ruff-check:
	$(RUFF) format --check .
	$(RUFF) check .

ruff-fix:
	$(RUFF) check --fix .
	$(RUFF) format .

fetch:
	$(UV_RUN) python scripts/fetch_sources.py

source-lock:
	$(UV_RUN) python scripts/fetch_sources.py --write-lock

native-build: fetch
	$(UV_RUN) python scripts/build.py --clean

stage:
	$(UV_RUN) python scripts/stage_wheel.py
	$(UV_RUN) python scripts/patch_rpath.py

wheel: native-build stage
	WHEEL_PLATFORM_TAG=$(PLATFORM_TAG) $(UV) build --wheel
	$(UV_RUN) python scripts/verify_pth_wheel.py

patched-wheel: native-build stage
	rm -rf dist
	$(UV_RUN) python scripts/patch_weasyprint_wheel.py --version $(WEASYPRINT_VERSION) --platform-tag $(PLATFORM_TAG)

verify:
	$(UV_RUN) python scripts/fetch_sources.py

verify-pth:
	$(UV_RUN) python scripts/verify_pth_wheel.py

clean:
	rm -rf _build dist src/weasyprint_libs/lib src/weasyprint_libs/bin src/weasyprint_libs/etc src/weasyprint_libs/share

distclean: clean
	rm -rf .venv .uv-cache downloads/current

.PHONY: windows-update-lock windows-fetch windows-extract windows-stage windows-wheel windows-patched-wheel

windows-update-lock:
	$(UV_RUN) python scripts/fetch_windows_packages.py --update-lock

windows-fetch:
	$(UV_RUN) python scripts/fetch_windows_packages.py --locked

windows-extract: windows-fetch
	$(UV_RUN) python scripts/extract_windows_packages.py

windows-stage: windows-extract
	$(UV_RUN) python scripts/stage_windows_wheel.py

windows-wheel: windows-stage
	WHEEL_PLATFORM_TAG=win_amd64 $(UV) build --wheel
	$(UV_RUN) python scripts/verify_pth_wheel.py

windows-patched-wheel: windows-stage
	rm -rf dist
	$(UV_RUN) python scripts/patch_weasyprint_wheel.py --version $(WEASYPRINT_VERSION) --platform-tag win_amd64
