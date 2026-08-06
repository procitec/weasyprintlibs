#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

try:
    from license_bundle import verify_bundle
except ModuleNotFoundError:
    from scripts.license_bundle import verify_bundle

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify a generated third-party license bundle.")
    parser.add_argument("path", type=Path, nargs="?", default=Path("_build/licenses"))
    parser.add_argument("--runtime", type=Path)
    args = parser.parse_args()

    bundle = args.path if args.path.is_absolute() else ROOT / args.path
    runtime = None
    if args.runtime is not None:
        runtime = args.runtime if args.runtime.is_absolute() else ROOT / args.runtime
    manifest = verify_bundle(bundle, runtime)
    print(
        f"Verified {len(manifest['components'])} license records for "
        f"{manifest['platform_tag']} in {bundle}"
    )


if __name__ == "__main__":
    main()
