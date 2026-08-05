from pathlib import Path
from zipfile import ZipFile

PTH_NAME = "weasyprint_libs.pth"
CONFIG_MODULE = "weasyprint_libs/_weasyprint_libs_config.py"
LOADER_MODULE = "weasyprint_libs/loader.py"


def _installation_candidates(names: list[str], relative_path: str) -> list[str]:
    return [
        name
        for name in names
        if name == relative_path or name.endswith(f".data/purelib/{relative_path}")
    ]


def main() -> None:
    wheels = list(Path("dist").glob("*.whl"))

    if len(wheels) != 1:
        raise SystemExit(f"Expected exactly one wheel in dist/, found {len(wheels)}")

    wheel = wheels[0]

    with ZipFile(wheel) as archive:
        names = archive.namelist()
        pth_candidates = _installation_candidates(names, PTH_NAME)

        if not pth_candidates:
            raise SystemExit(f"{PTH_NAME} is missing from wheel installation paths: {wheel}")

        for required in (CONFIG_MODULE, LOADER_MODULE):
            if not _installation_candidates(names, required):
                raise SystemExit(f"{required} is missing from wheel installation paths: {wheel}")

        pth_path = pth_candidates[0]
        content = archive.read(pth_path).decode("utf-8").strip()

    expected = "import weasyprint_libs; weasyprint_libs.activate()"

    if content != expected:
        raise SystemExit(f"Unexpected content in {pth_path}: {content!r}")

    print(f"Verified {pth_path}, {LOADER_MODULE} and {CONFIG_MODULE} in {wheel}")


if __name__ == "__main__":
    main()
