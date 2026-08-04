from __future__ import annotations

import shutil
import tarfile
import tomllib
from pathlib import Path
from typing import Any

import zstandard

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "windows-packages.toml"


def load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        return tomllib.load(stream)


def extract_archive(archive_path: Path, destination: Path) -> None:
    print(f"Extracting {archive_path.name}")
    with archive_path.open("rb") as compressed:
        with zstandard.ZstdDecompressor().stream_reader(compressed) as reader:
            with tarfile.open(fileobj=reader, mode="r|") as archive:
                archive.extractall(destination, filter="data")


def main() -> None:
    config = load_toml(CONFIG_PATH)["windows"]
    lock_path = ROOT / config["lock_file"]
    lock = load_toml(lock_path)
    download_dir = ROOT / config["download_dir"]
    destination = ROOT / config["extract_dir"]

    shutil.rmtree(destination, ignore_errors=True)
    destination.mkdir(parents=True, exist_ok=True)

    for package in lock.get("package", []):
        archive = download_dir / package["filename"]
        if not archive.is_file():
            raise RuntimeError(f"Missing {archive}. Run fetch_windows_packages.py --locked first.")
        extract_archive(archive, destination)


if __name__ == "__main__":
    main()
