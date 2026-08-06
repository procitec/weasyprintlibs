from __future__ import annotations

import hashlib
import io
import json
import tarfile
import zipfile
from pathlib import Path

from scripts.license_bundle import (
    _source_archive_license_blobs,
    collect_linux,
    reset_directory,
    verify_bundle,
    write_bundle,
)


def _source_archive(path: Path, license_text: bytes) -> str:
    path.parent.mkdir(parents=True)
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo("example-1.0/LICENSE")
        info.size = len(license_text)
        archive.addfile(info, io.BytesIO(license_text))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_collect_linux_builds_verified_bundle_and_archive(tmp_path: Path) -> None:
    root = tmp_path
    (root / "config").mkdir()
    (root / "LICENSE").write_text("project license\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        """
[project]
name = "test-builder"
version = "1.2.3"
license = "MIT"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    archive = root / "downloads" / "example-1.0.tar.gz"
    digest = _source_archive(archive, b"example license\n")
    (root / "config" / "libraries.toml").write_text(
        """
[build]
download_dir = "downloads"

[[library]]
name = "example"
version = "1.0"
url = "https://example.invalid/example-1.0.tar.gz"
archive = "example-1.0.tar.gz"
license_expression = "MIT"
license_files = ["LICENSE"]
runtime_patterns = ["lib/libexample.so*"]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (root / "config" / "source-lock.generated.toml").write_text(
        f"""
[[source]]
name = "example"
version = "1.0"
url = "https://example.invalid/example-1.0.tar.gz"
archive = "example-1.0.tar.gz"
sha256 = "{digest}"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    runtime = root / "_build" / "runtime"
    (runtime / "lib").mkdir(parents=True)
    (runtime / "lib" / "libexample.so.1").write_bytes(b"native")
    output = root / "_build" / "licenses"
    release_archive = root / "dist" / "third-party-licenses-test.zip"
    reset_directory(output)

    manifest = collect_linux(
        root=root,
        runtime_root=runtime,
        output=output,
        platform_tag="manylinux_2_28_x86_64",
    )
    write_bundle(
        root=root,
        output=output,
        manifest=manifest,
        archive_path=release_archive,
    )

    verified = verify_bundle(output, runtime)
    assert verified["components"][0]["name"] == "example"
    assert (output / "texts" / "example" / "LICENSE").read_text() == "example license\n"
    with zipfile.ZipFile(release_archive) as bundle:
        names = set(bundle.namelist())
    assert any(name.endswith("/manifest.json") for name in names)
    assert any(name.endswith("/texts/example/LICENSE") for name in names)


def test_source_archive_license_discovery_ignores_regular_source_files(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "source.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("project-1.0/LICENSE", "license\n")
        archive.writestr("project-1.0/docs/FTL.TXT", "freetype license\n")
        archive.writestr("project-1.0/src/example.c", "int main(void) { return 0; }\n")

    blobs = _source_archive_license_blobs(archive_path)

    assert blobs == {
        "LICENSE": b"license\n",
        "docs/FTL.TXT": b"freetype license\n",
    }
