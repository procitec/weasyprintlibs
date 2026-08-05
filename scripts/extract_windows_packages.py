from __future__ import annotations

import argparse
import shutil
import tarfile
from pathlib import Path

import zstandard
from windows_config import load_toml, load_windows_profile

ROOT = Path(__file__).resolve().parents[1]


def extract_archive(archive_path: Path, destination: Path) -> None:
    print(f"Extracting {archive_path.name}")
    with archive_path.open("rb") as compressed:
        with zstandard.ZstdDecompressor().stream_reader(compressed) as reader:
            with tarfile.open(fileobj=reader, mode="r|") as archive:
                archive.extractall(destination, filter="data")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile")
    args = parser.parse_args()

    profile = load_windows_profile(args.profile)
    lock_path = ROOT / profile["lock_file"]
    lock = load_toml(lock_path)
    download_dir = ROOT / profile["download_dir"]
    destination = ROOT / profile["extract_dir"]

    shutil.rmtree(destination, ignore_errors=True)
    destination.mkdir(parents=True, exist_ok=True)

    for package in lock.get("package", []):
        archive = download_dir / package["filename"]
        if not archive.is_file():
            raise RuntimeError(f"Missing {archive}. Run fetch_windows_packages.py --locked first.")
        extract_archive(archive, destination)


if __name__ == "__main__":
    main()
