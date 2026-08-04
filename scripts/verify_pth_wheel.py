from pathlib import Path
from zipfile import ZipFile


PTH_NAME = "procitec_weasyprint_libs.pth"


def main() -> None:
    wheels = list(Path("dist").glob("*.whl"))

    if len(wheels) != 1:
        raise SystemExit(
            f"Expected exactly one wheel in dist/, found {len(wheels)}"
        )

    wheel = wheels[0]

    with ZipFile(wheel) as archive:
        names = archive.namelist()

        candidates = [
            name
            for name in names
            if name == PTH_NAME
            or name.endswith(f".data/purelib/{PTH_NAME}")
        ]

        if not candidates:
            raise SystemExit(
                f"{PTH_NAME} is missing from wheel installation paths: {wheel}"
            )

        pth_path = candidates[0]
        content = archive.read(pth_path).decode("utf-8").strip()

    expected = (
        "import weasyprintlibs_native; "
        "weasyprintlibs_native.activate()"
    )

    if content != expected:
        raise SystemExit(
            f"Unexpected content in {pth_path}: {content!r}"
        )

    print(f"Verified {pth_path} in {wheel}")


if __name__ == "__main__":
    main()
