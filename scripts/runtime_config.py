#!/usr/bin/env python3
from __future__ import annotations

import argparse
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "runtime-libraries.toml"
PLATFORMS = ("windows", "linux", "macos")


def load_runtime_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    with path.open("rb") as stream:
        config = tomllib.load(stream)

    for platform in PLATFORMS:
        section = config.get(platform)
        if not isinstance(section, dict):
            raise RuntimeError(f"Missing [{platform}] section in {path}")

        directory = section.get("directory")
        preload = section.get("preload")
        if not isinstance(directory, str) or not directory:
            raise RuntimeError(f"Invalid {platform}.directory in {path}")
        if not isinstance(preload, list) or not preload:
            raise RuntimeError(f"Invalid {platform}.preload in {path}")
        if not all(isinstance(name, str) and name for name in preload):
            raise RuntimeError(f"Invalid library name in {platform}.preload")
        if len(preload) != len(set(preload)):
            raise RuntimeError(f"Duplicate library in {platform}.preload")

    macos = config["macos"]
    aliases = macos.get("aliases")
    seed_patterns = macos.get("seed_patterns")
    if not isinstance(aliases, dict) or not aliases:
        raise RuntimeError(f"Invalid macos.aliases in {path}")
    if not all(isinstance(key, str) and isinstance(value, str) for key, value in aliases.items()):
        raise RuntimeError(f"Invalid entry in macos.aliases in {path}")
    if not isinstance(seed_patterns, list) or not seed_patterns:
        raise RuntimeError(f"Invalid macos.seed_patterns in {path}")

    preload_names = set(macos["preload"])
    missing_targets = sorted(set(aliases.values()) - preload_names)
    if missing_targets:
        formatted = ", ".join(missing_targets)
        raise RuntimeError(
            "Every macOS alias target must be explicitly preloaded; "
            f"missing from macos.preload: {formatted}"
        )

    return config


def render_generated_module(config: dict[str, Any]) -> str:
    scalar_values = {
        "WINDOWS_LIBRARY_DIRECTORY": config["windows"]["directory"],
        "LINUX_LIBRARY_DIRECTORY": config["linux"]["directory"],
        "MACOS_LIBRARY_DIRECTORY": config["macos"]["directory"],
    }
    sequence_values = {
        "WINDOWS_LIBRARIES": config["windows"]["preload"],
        "LINUX_LIBRARIES": config["linux"]["preload"],
        "MACOS_LIBRARIES": config["macos"]["preload"],
        "MACOS_SEED_LIBRARY_PATTERNS": config["macos"]["seed_patterns"],
    }

    lines = [
        "# Generated while patching the WeasyPrint wheel.",
        "# Source: config/runtime-libraries.toml",
        "from __future__ import annotations",
        "",
    ]

    for name, value in scalar_values.items():
        lines.extend((f"{name} = {value!r}", ""))

    for name, values in sequence_values.items():
        lines.append(f"{name} = (")
        lines.extend(f"    {value!r}," for value in values)
        lines.extend((")", ""))

    lines.append("MACOS_LIBRARY_ALIASES = {")
    for alias, target in sorted(config["macos"]["aliases"].items()):
        lines.append(f"    {alias!r}: {target!r},")
    lines.extend(("}", ""))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate or render the native runtime bootstrap configuration."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate the TOML configuration without writing generated files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for the generated Python bootstrap module",
    )
    args = parser.parse_args()

    config = load_runtime_config()
    if args.output:
        output = args.output if args.output.is_absolute() else ROOT / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_generated_module(config), encoding="utf-8")
        print(f"Generated {output.relative_to(ROOT)}")
    else:
        print(f"Verified {CONFIG_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
