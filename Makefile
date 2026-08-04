UV ?= uv
PLATFORM_TAG ?= manylinux_2_28_x86_64

UV_RUN := $(UV) run
.PHONY: sync lock fetch source-lock native-build stage wheel verify verify-pth clean distclean

sync:
	$(UV) sync

lock:
	$(UV) lock

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

verify:
	$(UV_RUN) python scripts/fetch_sources.py

verify-pth:
	$(UV_RUN) python scripts/verify_pth_wheel.py

clean:
	rm -rf _build dist src/weasyprintlibs_native/lib src/weasyprintlibs_native/bin src/weasyprintlibs_native/etc src/weasyprintlibs_native/share

distclean: clean
	rm -rf .venv .uv-cache downloads/current

.PHONY: windows-update-lock windows-fetch windows-extract windows-stage windows-wheel

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
