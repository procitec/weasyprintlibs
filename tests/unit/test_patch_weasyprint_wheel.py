from __future__ import annotations

import csv
import io
import json
import zipfile
from email.parser import Parser
from pathlib import Path

from scripts.patch_weasyprint_wheel import build_wheel, bundled_version
from scripts.verify_patched_weasyprint_wheel import verify_wheel


def _upstream_wheel(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "weasyprint/__init__.py",
            '"""test"""\nfrom __future__ import annotations\n',
        )
        archive.writestr(
            "weasyprint-69.0.dist-info/METADATA",
            "Metadata-Version: 2.4\nName: WeasyPrint\nVersion: 69.0\n",
        )
        archive.writestr(
            "weasyprint-69.0.dist-info/WHEEL",
            "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        )
        archive.writestr("weasyprint-69.0.dist-info/RECORD", "")


def test_build_wheel_embeds_runtime_and_updates_metadata(tmp_path: Path) -> None:
    source = tmp_path / "weasyprint-69.0-py3-none-any.whl"
    _upstream_wheel(source)

    runtime = tmp_path / "runtime"
    (runtime / "lib").mkdir(parents=True)
    (runtime / "lib" / "libexample.so.1").write_bytes(b"native")
    (runtime / "etc" / "fonts").mkdir(parents=True)
    (runtime / "etc" / "fonts" / "fonts.conf").write_text("<fontconfig/>")

    licenses = tmp_path / "licenses"
    (licenses / "texts" / "example").mkdir(parents=True)
    (licenses / "PROJECT_LICENSE.txt").write_text("project license\n")
    (licenses / "THIRD_PARTY_LICENSES.md").write_text("# Licenses\n")
    (licenses / "texts" / "example" / "LICENSE").write_text("example license\n")
    (licenses / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "platform": "linux",
                "platform_tag": "manylinux_2_28_x86_64",
                "project": {
                    "name": "test-builder",
                    "version": "26.1.1",
                    "license": "MIT",
                    "license_file": "PROJECT_LICENSE.txt",
                },
                "components": [
                    {
                        "name": "example",
                        "version": "1.0",
                        "type": "upstream-source",
                        "license_expression": "MIT",
                        "license_files": ["texts/example/LICENSE"],
                        "runtime_files": ["lib/libexample.so.1"],
                    }
                ],
            },
            indent=2,
        )
        + "\n"
    )

    output = build_wheel(
        source,
        runtime,
        tmp_path / "dist",
        "manylinux_2_28_x86_64",
        "69.0",
        "26.1.1",
        licenses,
    )

    verify_wheel(output)

    assert output.name == ("weasyprint-69.0+bundled.26.1.1-py3-none-manylinux_2_28_x86_64.whl")
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        metadata_name = next(name for name in names if name.endswith(".dist-info/METADATA"))
        metadata = Parser().parsestr(archive.read(metadata_name).decode())
        assert metadata["Version"] == bundled_version("69.0", "26.1.1")
        assert "weasyprint/_weasyprint_libs/lib/libexample.so.1" in names
        assert "weasyprint/_weasyprint_libs_loader.py" in names
        assert "weasyprint/_weasyprint_libs_config.py" in names
        assert any(name.endswith(".dist-info/licenses/manifest.json") for name in names)

        runtime_name = next(
            name for name in names if name.endswith(".dist-info/BUNDLED-RUNTIME.json")
        )
        runtime_metadata = json.loads(archive.read(runtime_name))
        assert runtime_metadata["upstream_version"] == "69.0"
        assert runtime_metadata["builder_version"] == "26.1.1"

        record_name = next(name for name in names if name.endswith(".dist-info/RECORD"))
        recorded = {
            row[0] for row in csv.reader(io.StringIO(archive.read(record_name).decode("utf-8")))
        }
        assert names <= recorded
