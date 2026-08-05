#!/usr/bin/env python3
"""Cross-platform project orchestration for bundled WeasyPrint wheels.

The specialised build and verification modules remain separate.  This module
only defines the public workflow and replaces duplicated Make, shell and
PowerShell orchestration.
"""

from __future__ import annotations

import argparse
import os
import platform
import shlex
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WEASYPRINT_VERSION = "69.0"
DEFAULT_TEST_PYTHON = "3.13"
DEFAULT_WINDOWS_PROFILE = "x86_64"


class Runner:
    """Run project commands from the repository root."""

    def __init__(self, *, dry_run: bool = False) -> None:
        self.dry_run = dry_run

    def run(
        self,
        *args: str | Path,
        env: dict[str, str] | None = None,
        capture_output: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        command = [str(value) for value in args]
        print("+", shlex.join(command), flush=True)
        if self.dry_run:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        command_env = os.environ.copy()
        if env:
            command_env.update(env)
        return subprocess.run(
            command,
            cwd=ROOT,
            env=command_env,
            check=True,
            text=True,
            capture_output=capture_output,
        )

    def python_script(
        self,
        name: str,
        *args: str | Path,
        optional: bool = False,
        capture_output: bool = False,
    ) -> subprocess.CompletedProcess[str] | None:
        path = ROOT / "scripts" / name
        if optional and not path.is_file():
            print(f"- skip missing optional script: {path.relative_to(ROOT)}", flush=True)
            return None
        if not self.dry_run and not path.is_file():
            raise FileNotFoundError(path)
        return self.run(sys.executable, path, *args, capture_output=capture_output)


def host_platform() -> str:
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform == "darwin":
        return "macos"
    if sys.platform == "win32":
        return "windows"
    raise RuntimeError(f"Unsupported host platform: {sys.platform}")


def default_platform_tag(target: str, profile: str = DEFAULT_WINDOWS_PROFILE) -> str:
    if target == "linux":
        return "manylinux_2_28_x86_64"
    if target == "windows":
        tags = {"x86_64": "win_amd64", "arm64": "win_arm64"}
        try:
            return tags[profile]
        except KeyError as error:
            raise RuntimeError(f"Unsupported Windows profile: {profile}") from error
    if target == "macos":
        machine = platform.machine().lower()
        tags = {
            "arm64": "macosx_11_0_arm64",
            "aarch64": "macosx_11_0_arm64",
            "x86_64": "macosx_11_0_x86_64",
            "amd64": "macosx_11_0_x86_64",
        }
        try:
            return tags[machine]
        except KeyError as error:
            raise RuntimeError(f"Unsupported macOS architecture: {machine}") from error
    raise RuntimeError(f"Unsupported target platform: {target}")


def resolve_platform_tag(
    runner: Runner,
    target: str,
    profile: str,
    override: str | None,
) -> str:
    if override:
        return override
    if target != "windows":
        return default_platform_tag(target, profile)

    config_script = ROOT / "scripts" / "windows_config.py"
    if runner.dry_run or not config_script.is_file():
        return default_platform_tag(target, profile)
    result = runner.python_script(
        "windows_config.py",
        "--profile",
        profile,
        "--field",
        "platform_tag",
        capture_output=True,
    )
    assert result is not None
    tag = result.stdout.strip()
    if not tag:
        raise RuntimeError("windows_config.py returned an empty platform tag")
    return tag


def remove_paths(paths: Sequence[Path]) -> None:
    for path in paths:
        absolute = path if path.is_absolute() else ROOT / path
        if absolute.is_dir() and not absolute.is_symlink():
            shutil.rmtree(absolute, ignore_errors=True)
        else:
            absolute.unlink(missing_ok=True)


def runtime_config_check(runner: Runner) -> None:
    runner.python_script("runtime_config.py", "--check")


def fetch_sources(runner: Runner, *, write_lock: bool = False) -> None:
    args = ["--write-lock"] if write_lock else []
    runner.python_script("fetch_sources.py", *args)


def build_native_linux(runner: Runner) -> None:
    fetch_sources(runner)
    runner.python_script("build.py", "--clean")


def verify_runtime(runner: Runner, target: str) -> None:
    runner.python_script(
        "verify_runtime_payload.py",
        "--root",
        "_build/runtime",
        "--platform",
        target,
        optional=True,
    )


def stage_linux(runner: Runner) -> None:
    runtime_config_check(runner)
    runner.python_script("stage_wheel.py")
    runner.python_script("patch_rpath.py", "_build/runtime/lib")
    verify_runtime(runner, "linux")


def stage_windows(runner: Runner, profile: str) -> None:
    runtime_config_check(runner)
    runner.python_script("fetch_windows_packages.py", "--profile", profile, "--locked")
    runner.python_script("extract_windows_packages.py", "--profile", profile)
    runner.python_script("stage_windows_wheel.py", "--profile", profile)
    verify_runtime(runner, "windows")


def stage_macos(runner: Runner) -> None:
    runtime_config_check(runner)
    runner.python_script("stage_macos_wheel.py")
    verify_runtime(runner, "macos")


def stage_runtime(runner: Runner, target: str, profile: str) -> None:
    if target == "linux":
        stage_linux(runner)
    elif target == "windows":
        stage_windows(runner, profile)
    elif target == "macos":
        stage_macos(runner)
    else:
        raise RuntimeError(f"Unsupported target platform: {target}")


def find_single_wheel(path: Path) -> Path:
    absolute = path if path.is_absolute() else ROOT / path
    if absolute.is_file():
        return absolute
    wheels = sorted(absolute.glob("weasyprint-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"Expected exactly one WeasyPrint wheel in {absolute}, got {wheels}")
    return wheels[0]


def verify_wheel(runner: Runner, path: Path = Path("dist")) -> None:
    runner.python_script("verify_patched_weasyprint_wheel.py", path)


def build_wheel(
    runner: Runner,
    *,
    version: str,
    profile: str,
    platform_tag: str | None,
) -> None:
    target = host_platform()
    if target == "linux":
        build_native_linux(runner)
    stage_runtime(runner, target, profile)

    tag = resolve_platform_tag(runner, target, profile, platform_tag)
    remove_paths([Path("dist")])
    runner.python_script(
        "patch_weasyprint_wheel.py",
        "--version",
        version,
        "--platform-tag",
        tag,
    )
    verify_wheel(runner)

    if target == "macos":
        wheel = (
            Path("dist/weasyprint-DRY-RUN.whl")
            if runner.dry_run
            else find_single_wheel(Path("dist"))
        )
        runner.python_script(
            "verify_macos_wheel.py",
            wheel,
            "--arch",
            platform.machine(),
            optional=True,
        )


def run_ruff(runner: Runner, *args: str) -> None:
    runner.run("uv", "tool", "run", "--from", "ruff==0.16.1", "ruff", *args)


def test_unit(runner: Runner) -> None:
    runner.run(
        "uv",
        "run",
        "--with",
        "pytest==8.4.2",
        "python",
        "-m",
        "pytest",
        "tests/unit",
        "-v",
    )


def check(runner: Runner) -> None:
    run_ruff(runner, "check", ".")
    run_ruff(runner, "format", "--check", ".")
    runtime_config_check(runner)
    test_unit(runner)


def test_wheel(runner: Runner, wheel: Path, python_version: str, keep_venv: bool) -> None:
    args: list[str | Path] = ["--wheel", wheel, "--python", python_version]
    if keep_venv:
        args.append("--keep-venv")
    runner.python_script("test_patched_wheel.py", *args)


def clean(*, all_files: bool = False) -> None:
    paths = [
        Path("_build"),
        Path("dist"),
        Path(".test-venv"),
        Path("tests/runtime/_output_direct"),
        Path("tests/sphinx-simplepdf-demo/_output_direct"),
    ]
    if all_files:
        paths.extend(
            [
                Path(".venv"),
                Path(".uv-cache"),
                Path("downloads/current"),
                Path("downloads/weasyprint"),
                Path("downloads/windows"),
                Path("downloads/windows-arm64"),
            ]
        )
    remove_paths(paths)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build, verify and test bundled WeasyPrint wheels.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing them.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_parser = subparsers.add_parser("sync", help="Synchronise the uv environment.")
    sync_parser.add_argument("--frozen", action="store_true")

    subparsers.add_parser("lock", help="Refresh uv.lock.")
    subparsers.add_parser("format", help="Format Python files with Ruff.")
    subparsers.add_parser("check", help="Run lint, format and unit checks.")

    fetch_parser = subparsers.add_parser("fetch", help="Fetch native source archives.")
    fetch_parser.add_argument("--write-lock", action="store_true")

    subparsers.add_parser("native-build", help="Build the Linux native stack.")

    stage_parser = subparsers.add_parser("stage", help="Stage the runtime for this host.")
    stage_parser.add_argument("--profile", default=DEFAULT_WINDOWS_PROFILE)

    build_parser = subparsers.add_parser("build", help="Build the bundled wheel.")
    build_parser.add_argument("--version", default=DEFAULT_WEASYPRINT_VERSION)
    build_parser.add_argument("--profile", default=DEFAULT_WINDOWS_PROFILE)
    build_parser.add_argument("--platform-tag")

    subparsers.add_parser("verify-sources", help="Verify downloaded source archives.")

    verify_runtime_parser = subparsers.add_parser(
        "verify-runtime",
        help="Verify the staged runtime.",
    )
    verify_runtime_parser.add_argument(
        "--platform",
        choices=("linux", "windows", "macos"),
        default=None,
    )

    verify_wheel_parser = subparsers.add_parser("verify-wheel", help="Verify a wheel.")
    verify_wheel_parser.add_argument("path", nargs="?", type=Path, default=Path("dist"))

    subparsers.add_parser("test-unit", help="Run fast unit tests.")

    test_wheel_parser = subparsers.add_parser(
        "test-wheel",
        help="Install a wheel in a clean venv and render the test PDF.",
    )
    test_wheel_parser.add_argument("--wheel", type=Path, default=Path("dist"))
    test_wheel_parser.add_argument("--python", default=DEFAULT_TEST_PYTHON)
    test_wheel_parser.add_argument("--keep-venv", action="store_true")

    clean_parser = subparsers.add_parser("clean", help="Remove generated files.")
    clean_parser.add_argument("--all", action="store_true", dest="all_files")

    windows_lock_parser = subparsers.add_parser(
        "windows-update-lock",
        help="Resolve and update the Windows package lock.",
    )
    windows_lock_parser.add_argument("--profile", default=DEFAULT_WINDOWS_PROFILE)

    tag_parser = subparsers.add_parser("platform-tag", help="Print the host wheel tag.")
    tag_parser.add_argument("--profile", default=DEFAULT_WINDOWS_PROFILE)
    tag_parser.add_argument("--override")

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    runner = Runner(dry_run=args.dry_run)

    if args.command == "sync":
        command = ["uv", "sync"]
        if args.frozen:
            command.append("--frozen")
        runner.run(*command)
    elif args.command == "lock":
        runner.run("uv", "lock")
    elif args.command == "format":
        run_ruff(runner, "format", ".")
    elif args.command == "check":
        check(runner)
    elif args.command == "fetch":
        fetch_sources(runner, write_lock=args.write_lock)
    elif args.command == "native-build":
        if host_platform() != "linux":
            raise RuntimeError("native-build is only available on Linux")
        build_native_linux(runner)
    elif args.command == "stage":
        stage_runtime(runner, host_platform(), args.profile)
    elif args.command == "build":
        build_wheel(
            runner,
            version=args.version,
            profile=args.profile,
            platform_tag=args.platform_tag,
        )
    elif args.command == "verify-sources":
        fetch_sources(runner)
    elif args.command == "verify-runtime":
        verify_runtime(runner, args.platform or host_platform())
    elif args.command == "verify-wheel":
        verify_wheel(runner, args.path)
    elif args.command == "test-unit":
        test_unit(runner)
    elif args.command == "test-wheel":
        test_wheel(runner, args.wheel, args.python, args.keep_venv)
    elif args.command == "clean":
        clean(all_files=args.all_files)
    elif args.command == "windows-update-lock":
        runner.python_script(
            "fetch_windows_packages.py",
            "--profile",
            args.profile,
            "--update-lock",
        )
    elif args.command == "platform-tag":
        print(resolve_platform_tag(runner, host_platform(), args.profile, args.override))
    else:  # pragma: no cover - argparse guarantees a known command.
        raise AssertionError(args.command)


if __name__ == "__main__":
    main()
