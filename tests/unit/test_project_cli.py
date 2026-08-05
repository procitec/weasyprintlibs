from __future__ import annotations

import importlib

import pytest

project = importlib.import_module("scripts.project")


@pytest.mark.parametrize(
    ("target", "profile", "expected"),
    [
        ("linux", "x86_64", "manylinux_2_28_x86_64"),
        ("windows", "x86_64", "win_amd64"),
        ("windows", "arm64", "win_arm64"),
    ],
)
def test_default_platform_tag(target: str, profile: str, expected: str) -> None:
    assert project.default_platform_tag(target, profile) == expected


def test_build_command_defaults() -> None:
    args = project.build_parser().parse_args(["build"])

    assert args.version == "69.0"
    assert args.profile == "x86_64"
    assert args.platform_tag is None


def test_dry_run_does_not_execute_process(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("subprocess.run must not be called")

    monkeypatch.setattr(project.subprocess, "run", fail)
    result = project.Runner(dry_run=True).run("example", "argument with spaces")

    assert result.returncode == 0


def test_remove_paths_removes_files_and_directories(
    tmp_path: project.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project, "ROOT", tmp_path)
    file_path = tmp_path / "file.txt"
    directory = tmp_path / "directory"
    file_path.write_text("content", encoding="utf-8")
    directory.mkdir()
    (directory / "nested.txt").write_text("content", encoding="utf-8")

    project.remove_paths([project.Path("file.txt"), project.Path("directory")])

    assert not file_path.exists()
    assert not directory.exists()
