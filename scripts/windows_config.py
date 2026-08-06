#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "windows-packages.toml"
REQUIRED_FIELDS = (
    "repository",
    "architecture",
    "prefix",
    "mirror_base_url",
    "lock_file",
    "download_dir",
    "extract_dir",
    "platform_tag",
    "packages",
)


def load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        return tomllib.load(stream)


def _license_fallbacks(windows: dict[str, Any], path: Path) -> list[dict[str, Any]]:
    fallbacks = windows.get("license_fallback", [])
    if not isinstance(fallbacks, list) or not all(
        isinstance(item, dict) for item in fallbacks
    ):
        raise RuntimeError(f"Invalid [[windows.license_fallback]] entries in {path}")
    return [dict(item) for item in fallbacks]


def load_windows_profile(
    profile_name: str | None = None,
    *,
    path: Path = CONFIG_PATH,
) -> dict[str, Any]:
    config = load_toml(path)
    windows = config.get("windows")
    if not isinstance(windows, dict):
        raise RuntimeError(f"Missing [windows] section in {path}")

    # Backward compatibility for older single-profile configurations.
    profiles = windows.get("profiles")
    if not isinstance(profiles, dict):
        profile = dict(windows)
        profile["profile"] = profile_name or "default"
        profile["license_fallbacks"] = _license_fallbacks(windows, path)
        return profile

    selected = profile_name or os.environ.get("WINDOWS_PROFILE") or windows.get("default_profile")
    if not isinstance(selected, str) or not selected:
        raise RuntimeError(f"No Windows profile selected in {path}")

    raw_profile = profiles.get(selected)
    if not isinstance(raw_profile, dict):
        available = ", ".join(sorted(profiles))
        raise RuntimeError(f"Unknown Windows profile {selected!r}; available: {available}")

    profile = dict(raw_profile)
    profile["profile"] = selected
    profile["license_fallbacks"] = _license_fallbacks(windows, path)
    missing = [field for field in REQUIRED_FIELDS if field not in profile]
    if missing:
        raise RuntimeError(f"Windows profile {selected!r} is missing fields: {missing}")
    if not isinstance(profile["packages"], list) or not profile["packages"]:
        raise RuntimeError(f"Windows profile {selected!r} has no packages")
    return profile


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a Windows native-runtime profile.")
    parser.add_argument("--profile")
    parser.add_argument("--field", choices=REQUIRED_FIELDS + ("profile",))
    args = parser.parse_args()

    profile = load_windows_profile(args.profile)
    if args.field:
        value = profile[args.field]
        if isinstance(value, list):
            print("\n".join(value))
        else:
            print(value)
        return

    for field in ("profile", *REQUIRED_FIELDS):
        value = profile[field]
        print(f"{field}={value}")


if __name__ == "__main__":
    main()
