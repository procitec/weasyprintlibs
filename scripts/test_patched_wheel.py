#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, check=True)


def venv_python(venv: Path) -> Path:
    if sys.platform == "win32":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def find_wheel(value: Path) -> Path:
    path = value if value.is_absolute() else ROOT / value
    if path.is_file():
        return path.resolve()
    wheels = sorted(path.glob("weasyprint-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"Expected exactly one wheel in {path}, got {wheels}")
    return wheels[0].resolve()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Install a patched WeasyPrint wheel into a clean venv and run its document test."
        )
    )
    parser.add_argument("--wheel", type=Path, default=Path("dist"))
    parser.add_argument("--venv", type=Path, default=Path(".test-venv"))
    parser.add_argument("--python", default="3.13")
    parser.add_argument(
        "--keep-venv",
        action="store_true",
        help="Reuse an existing test environment instead of recreating it",
    )
    args = parser.parse_args()

    wheel = find_wheel(args.wheel)
    venv = args.venv if args.venv.is_absolute() else ROOT / args.venv
    if not args.keep_venv:
        shutil.rmtree(venv, ignore_errors=True)

    if not venv_python(venv).is_file():
        run("uv", "venv", str(venv), "--python", args.python)

    python = venv_python(venv)
    run(
        "uv",
        "pip",
        "install",
        "--python",
        str(python),
        "--force-reinstall",
        str(wheel),
        "pytest>=8,<9",
        "pypdf>=6,<7",
    )
    run(
        str(python),
        "-m",
        "pytest",
        "tests/runtime/test_direct_weasyprint_wheel.py",
        "-v",
        "-s",
    )


if __name__ == "__main__":
    main()
