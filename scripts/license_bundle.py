from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tarfile
import tomllib
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA_VERSION = 1
PROJECT_LICENSE_NAME = "PROJECT_LICENSE.txt"
MANIFEST_NAME = "manifest.json"
SUMMARY_NAME = "THIRD_PARTY_LICENSES.md"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        return tomllib.load(stream)


def safe_name(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")
    if not result:
        raise RuntimeError(f"Cannot derive a safe path name from {value!r}")
    return result


def reset_directory(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)


def is_copyleft(expression: str) -> bool:
    upper = expression.upper()
    return "GPL" in upper or "LGPL" in upper or "AGPL" in upper


def _normalised_tar_members(archive: tarfile.TarFile) -> dict[str, tarfile.TarInfo]:
    members = [member for member in archive.getmembers() if member.isfile()]
    paths = [PurePosixPath(member.name) for member in members]
    first_parts = {path.parts[0] for path in paths if path.parts}
    strip_root = len(first_parts) == 1 and all(len(path.parts) > 1 for path in paths)

    result: dict[str, tarfile.TarInfo] = {}
    for member, path in zip(members, paths, strict=True):
        relative = PurePosixPath(*path.parts[1:]) if strip_root else path
        name = relative.as_posix()
        if name in result:
            raise RuntimeError(f"Duplicate archive member after root stripping: {name}")
        result[name] = member
    return result


def _copy_tar_license_files(
    archive_path: Path,
    configured_paths: list[str],
    destination: Path,
) -> list[str]:
    copied: list[str] = []
    with tarfile.open(archive_path, "r:*") as archive:
        members = _normalised_tar_members(archive)
        for configured in configured_paths:
            member = members.get(configured)
            if member is None:
                available = sorted(
                    name
                    for name in members
                    if Path(name).name.upper().startswith(("COPYING", "LICENSE", "LICENCE"))
                )
                raise RuntimeError(
                    f"License file {configured!r} is missing from {archive_path.name}; "
                    f"license-like files: {available[:20]}"
                )
            extracted = archive.extractfile(member)
            if extracted is None:
                raise RuntimeError(f"Cannot read {member.name} from {archive_path}")
            target = destination / configured
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(extracted.read())
            copied.append(target.as_posix())
    return copied


def _runtime_matches(runtime_root: Path, patterns: list[str]) -> list[str]:
    matches: set[str] = set()
    for pattern in patterns:
        for path in runtime_root.glob(pattern):
            if path.is_file() or path.is_symlink():
                matches.add(path.relative_to(runtime_root).as_posix())
    return sorted(matches)


def native_runtime_files(runtime_root: Path, platform_name: str) -> set[str]:
    if platform_name == "linux":
        paths = [path for path in (runtime_root / "lib").rglob("*") if ".so" in path.name]
    elif platform_name == "windows":
        paths = list((runtime_root / "bin").glob("*.dll"))
        paths.extend((runtime_root / "bin").glob("*.exe"))
    elif platform_name == "macos":
        paths = list((runtime_root / "lib").glob("*.dylib"))
    else:
        raise RuntimeError(f"Unsupported platform for license collection: {platform_name}")
    return {
        path.relative_to(runtime_root).as_posix()
        for path in paths
        if path.is_file() or path.is_symlink()
    }


def _source_lock_map(path: Path) -> dict[str, dict[str, Any]]:
    data = load_toml(path)
    result: dict[str, dict[str, Any]] = {}
    for item in data.get("source", []):
        name = item["name"]
        if name in result:
            raise RuntimeError(f"Duplicate source lock entry: {name}")
        result[name] = item
    return result


def collect_linux(
    *,
    root: Path,
    runtime_root: Path,
    output: Path,
    platform_tag: str,
) -> dict[str, Any]:
    config_path = root / "config" / "libraries.toml"
    lock_path = root / "config" / "source-lock.generated.toml"
    config = load_toml(config_path)
    source_lock = _source_lock_map(lock_path)
    download_dir = root / config["build"]["download_dir"]

    components: list[dict[str, Any]] = []
    owners: dict[str, str] = {}
    texts_root = output / "texts"

    for item in config.get("library", []):
        name = item["name"]
        required_fields = ("license_expression", "license_files", "runtime_patterns")
        missing = [field for field in required_fields if not item.get(field)]
        if missing:
            raise RuntimeError(f"Library {name!r} is missing license fields: {missing}")

        locked = source_lock.get(name)
        if locked is None:
            raise RuntimeError(f"Library {name!r} is missing from {lock_path}")
        for field in ("version", "url", "archive"):
            if locked.get(field) != item.get(field):
                raise RuntimeError(
                    f"Source lock mismatch for {name}.{field}: "
                    f"{locked.get(field)!r} != {item.get(field)!r}"
                )

        archive_path = download_dir / item["archive"]
        if not archive_path.is_file():
            raise RuntimeError(f"Missing source archive: {archive_path}")
        actual_sha256 = sha256(archive_path)
        if actual_sha256 != locked["sha256"]:
            raise RuntimeError(
                f"SHA-256 mismatch for {archive_path.name}: "
                f"{actual_sha256} != {locked['sha256']}"
            )

        component_dir = texts_root / safe_name(name)
        copied_absolute = _copy_tar_license_files(
            archive_path,
            list(item["license_files"]),
            component_dir,
        )
        license_files = [
            Path(path).relative_to(output).as_posix() for path in copied_absolute
        ]
        runtime_files = _runtime_matches(runtime_root, list(item["runtime_patterns"]))
        if not runtime_files:
            raise RuntimeError(
                f"Library {name!r} contributed no staged runtime files; "
                f"patterns={item['runtime_patterns']}"
            )
        for runtime_file in runtime_files:
            previous = owners.setdefault(runtime_file, name)
            if previous != name:
                raise RuntimeError(
                    f"Runtime file {runtime_file} is assigned to both {previous} and {name}"
                )

        expression = item["license_expression"]
        components.append(
            {
                "name": name,
                "version": item["version"],
                "type": "upstream-source",
                "license_expression": expression,
                "redistribution_license": item.get("redistribution_license"),
                "corresponding_source_required": item.get(
                    "corresponding_source_required", is_copyleft(expression)
                ),
                "source": {
                    "url": item["url"],
                    "archive": item["archive"],
                    "sha256": actual_sha256,
                },
                "license_files": license_files,
                "runtime_files": runtime_files,
            }
        )

    expected = native_runtime_files(runtime_root, "linux")
    missing_owners = sorted(expected - set(owners))
    if missing_owners:
        raise RuntimeError(f"Unmapped Linux runtime libraries: {missing_owners}")

    return _manifest(root, "linux", platform_tag, components)


def _parse_pkginfo(content: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition(" = ")
        if separator:
            result[key].append(value)
    return dict(result)


def _windows_license_relative(name: str, prefix: str) -> str | None:
    path = PurePosixPath(name)
    parts = path.parts
    prefixes = (
        (prefix, "share", "licenses"),
        (prefix, "share", "doc"),
        ("usr", "share", "licenses"),
        ("usr", "share", "doc"),
    )
    for marker in prefixes:
        marker_length = len(marker)
        for index in range(0, len(parts) - marker_length + 1):
            if parts[index : index + marker_length] != marker:
                continue
            tail = parts[index + marker_length :]
            if not tail:
                return None
            basename = tail[-1].upper()
            if marker[-1] == "licenses" or basename.startswith(
                ("COPYING", "LICENSE", "LICENCE", "NOTICE", "COPYRIGHT")
            ):
                return PurePosixPath(*tail).as_posix()
    return None


def _read_windows_package(
    archive_path: Path,
    *,
    prefix: str,
    runtime_names: set[str],
) -> tuple[dict[str, list[str]], dict[str, bytes], set[str]]:
    try:
        import zstandard
    except ModuleNotFoundError as error:  # pragma: no cover - dependency is in pyproject.
        raise RuntimeError("zstandard is required to inspect MSYS2 package archives") from error

    pkginfo: dict[str, list[str]] = {}
    licenses: dict[str, bytes] = {}
    runtime_files: set[str] = set()

    with archive_path.open("rb") as compressed:
        with zstandard.ZstdDecompressor().stream_reader(compressed) as reader:
            with tarfile.open(fileobj=reader, mode="r|") as archive:
                for member in archive:
                    if not member.isfile():
                        continue
                    path = PurePosixPath(member.name)
                    extracted = None
                    if path.name == ".PKGINFO":
                        extracted = archive.extractfile(member)
                        if extracted is None:
                            raise RuntimeError(f"Cannot read .PKGINFO from {archive_path}")
                        pkginfo = _parse_pkginfo(extracted.read().decode("utf-8"))
                        continue

                    if (
                        len(path.parts) >= 3
                        and path.parts[-3] == prefix
                        and path.parts[-2] == "bin"
                        and path.name in runtime_names
                    ):
                        runtime_files.add(f"bin/{path.name}")

                    relative = _windows_license_relative(member.name, prefix)
                    if relative is not None:
                        extracted = archive.extractfile(member)
                        if extracted is None:
                            raise RuntimeError(f"Cannot read {member.name} from {archive_path}")
                        if relative in licenses:
                            relative = f"{safe_name(path.parent.name)}-{relative}"
                        licenses[relative] = extracted.read()

    if not pkginfo:
        raise RuntimeError(f"Package archive has no readable .PKGINFO: {archive_path}")
    return pkginfo, licenses, runtime_files


def collect_windows(
    *,
    root: Path,
    runtime_root: Path,
    output: Path,
    platform_tag: str,
    profile: str,
) -> dict[str, Any]:
    try:
        from .windows_config import load_windows_profile
    except ImportError:
        from windows_config import load_windows_profile

    selected = load_windows_profile(profile)
    lock_path = root / selected["lock_file"]
    lock = load_toml(lock_path)
    metadata = lock.get("metadata")
    if not isinstance(metadata, dict):
        raise RuntimeError(f"Missing [metadata] in {lock_path}")
    expected_metadata = {
        "repository": selected["repository"],
        "architecture": selected["architecture"],
        "prefix": selected["prefix"],
        "mirror_base_url": selected["mirror_base_url"].rstrip("/"),
    }
    mismatches = [
        f"{key}: {metadata.get(key)!r} != {value!r}"
        for key, value in expected_metadata.items()
        if metadata.get(key) != value
    ]
    if mismatches:
        raise RuntimeError(
            f"Windows package lock does not match profile {profile}: "
            + "; ".join(mismatches)
        )
    packages = lock.get("package", [])
    download_dir = root / selected["download_dir"]
    runtime_names = {Path(path).name for path in native_runtime_files(runtime_root, "windows")}

    package_data: list[tuple[dict[str, Any], dict[str, list[str]], dict[str, bytes], set[str]]] = []
    owners: dict[str, str] = {}
    for item in packages:
        archive_path = download_dir / item["filename"]
        if not archive_path.is_file():
            raise RuntimeError(f"Missing locked MSYS2 package archive: {archive_path}")
        actual = sha256(archive_path)
        if actual != item["sha256"].lower():
            raise RuntimeError(
                f"SHA-256 mismatch for {archive_path.name}: {actual} != {item['sha256']}"
            )
        pkginfo, licenses, runtime_files = _read_windows_package(
            archive_path,
            prefix=selected["prefix"],
            runtime_names=runtime_names,
        )
        package_data.append((item, pkginfo, licenses, runtime_files))
        for runtime_file in runtime_files:
            previous = owners.setdefault(runtime_file, item["name"])
            if previous != item["name"]:
                raise RuntimeError(
                    f"Runtime file {runtime_file} occurs in both {previous} and {item['name']}"
                )

    expected = native_runtime_files(runtime_root, "windows")
    missing_owners = sorted(expected - set(owners))
    if missing_owners:
        raise RuntimeError(f"Unmapped Windows runtime files: {missing_owners}")

    components: list[dict[str, Any]] = []
    for item, pkginfo, licenses, runtime_files in package_data:
        if not runtime_files:
            continue
        if not licenses:
            raise RuntimeError(
                f"MSYS2 package {item['name']} contributes runtime files but no license texts"
            )
        component_dir = output / "texts" / safe_name(item["name"])
        copied: list[str] = []
        for relative, content in sorted(licenses.items()):
            target = component_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            copied.append(target.relative_to(output).as_posix())

        identifiers = pkginfo.get("license", [])
        if not identifiers:
            raise RuntimeError(f"MSYS2 package {item['name']} has no declared license metadata")
        expression = " AND ".join(identifiers)
        components.append(
            {
                "name": item["name"],
                "version": item["version"],
                "type": "msys2-package",
                "license_expression": expression,
                "license_identifiers": identifiers,
                "corresponding_source_required": is_copyleft(expression),
                "source": {
                    "url": item["url"],
                    "archive": item["filename"],
                    "sha256": item["sha256"].lower(),
                    "note": "Locked MSYS2 binary package; see package metadata for source package.",
                },
                "license_files": copied,
                "runtime_files": sorted(runtime_files),
            }
        )

    return _manifest(root, "windows", platform_tag, components)


def _brew_info(formula: str) -> dict[str, Any]:
    result = subprocess.run(
        ("brew", "info", "--json=v2", formula),
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    formulae = data.get("formulae", [])
    if len(formulae) != 1:
        raise RuntimeError(f"Expected one Homebrew formula record for {formula}: {formulae}")
    return formulae[0]


def _macos_license_files(keg: Path, formula: str) -> list[Path]:
    candidates: set[Path] = set()
    licenses_root = keg / "share" / "licenses"
    if licenses_root.is_dir():
        candidates.update(path for path in licenses_root.rglob("*") if path.is_file())

    doc_roots = [keg / "share" / "doc" / formula, keg / "share" / "doc"]
    for doc_root in doc_roots:
        if not doc_root.is_dir():
            continue
        for path in doc_root.rglob("*"):
            if path.is_file() and path.name.upper().startswith(
                ("COPYING", "LICENSE", "LICENCE", "NOTICE", "COPYRIGHT")
            ):
                candidates.add(path)

    for pattern in ("COPYING*", "LICENSE*", "LICENCE*", "NOTICE*"):
        candidates.update(path for path in keg.glob(pattern) if path.is_file())
    return sorted(candidates)


def _is_source_license_path(relative: PurePosixPath) -> bool:
    if not relative.parts or len(relative.parts) > 4:
        return False
    basename = relative.name.upper()
    if basename.startswith(("COPYING", "LICENSE", "LICENCE", "NOTICE", "COPYRIGHT")):
        return True
    if basename in {"FTL.TXT", "GPLV2.TXT", "GPLV3.TXT", "LGPLV2.1.TXT"}:
        return True
    return relative.parts[0].lower() in {"license", "licenses"}


def _source_archive_license_blobs(archive_path: Path) -> dict[str, bytes]:
    blobs: dict[str, bytes] = {}
    if zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path) as archive:
            paths = [PurePosixPath(name) for name in archive.namelist() if not name.endswith("/")]
            first_parts = {path.parts[0] for path in paths if path.parts}
            strip_root = len(first_parts) == 1 and all(len(path.parts) > 1 for path in paths)
            for path in paths:
                relative = PurePosixPath(*path.parts[1:]) if strip_root else path
                if _is_source_license_path(relative):
                    blobs[relative.as_posix()] = archive.read(path.as_posix())
        return blobs

    with tarfile.open(archive_path, "r:*") as archive:
        members = _normalised_tar_members(archive)
        for relative_name, member in members.items():
            relative = PurePosixPath(relative_name)
            if not _is_source_license_path(relative):
                continue
            extracted = archive.extractfile(member)
            if extracted is None:
                raise RuntimeError(f"Cannot read {member.name} from {archive_path}")
            blobs[relative_name] = extracted.read()
    return blobs


def _download_homebrew_source(
    *,
    root: Path,
    formula: str,
    version: str,
    url: str,
    expected_sha256: str,
) -> Path:
    parsed = urllib.parse.urlparse(url)
    url_name = Path(parsed.path).name or "source-archive"
    destination = (
        root
        / "downloads"
        / "homebrew-license-sources"
        / f"{safe_name(formula)}-{safe_name(version)}-{safe_name(url_name)}"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and sha256(destination) == expected_sha256:
        return destination

    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.unlink(missing_ok=True)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "weasyprint-bundled-builder-license-collector"},
    )
    print(f"Downloading Homebrew source for {formula} {version}: {url}")
    with urllib.request.urlopen(request) as response, temporary.open("wb") as output:
        shutil.copyfileobj(response, output)
    actual = sha256(temporary)
    if actual != expected_sha256:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(
            f"SHA-256 mismatch for Homebrew source {formula}: "
            f"{actual} != {expected_sha256}"
        )
    temporary.replace(destination)
    return destination


def collect_macos(
    *,
    root: Path,
    runtime_root: Path,
    output: Path,
    platform_tag: str,
    provenance_path: Path,
) -> dict[str, Any]:
    if not provenance_path.is_file():
        raise RuntimeError(f"Missing macOS runtime provenance: {provenance_path}")
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    files = provenance.get("files", {})
    if not isinstance(files, dict) or not files:
        raise RuntimeError(f"Invalid macOS runtime provenance: {provenance_path}")

    brew_prefix = Path(provenance["homebrew_prefix"]).resolve()
    cellar = brew_prefix / "Cellar"
    grouped: dict[tuple[str, str, Path], list[str]] = defaultdict(list)
    for runtime_file, details in files.items():
        source = Path(details["source"]).resolve()
        try:
            relative = source.relative_to(cellar)
        except ValueError as error:
            raise RuntimeError(f"Homebrew library is outside the Cellar: {source}") from error
        if len(relative.parts) < 3:
            raise RuntimeError(f"Cannot identify Homebrew keg from {source}")
        formula, version = relative.parts[:2]
        keg = cellar / formula / version
        grouped[(formula, version, keg)].append(runtime_file)

    expected = native_runtime_files(runtime_root, "macos")
    recorded = {path for runtime_files in grouped.values() for path in runtime_files}
    missing = sorted(expected - recorded)
    if missing:
        raise RuntimeError(f"Unmapped macOS runtime libraries: {missing}")

    components: list[dict[str, Any]] = []
    for (formula, version, keg), runtime_files in sorted(grouped.items()):
        info = _brew_info(formula)
        component_dir = output / "texts" / safe_name(formula)
        copied: list[str] = []
        stable = info.get("urls", {}).get("stable", {})
        checksum = stable.get("checksum")
        if isinstance(checksum, dict):
            checksum = checksum.get("sha256")
        stable_url = stable.get("url")
        stable_version = info.get("versions", {}).get("stable")
        if stable_version and not (
            version == stable_version or version.startswith(f"{stable_version}_")
        ):
            raise RuntimeError(
                f"Installed Homebrew keg {formula} {version} does not match stable formula "
                f"version {stable_version}"
            )

        license_paths = _macos_license_files(keg, formula)
        for source_path in license_paths:
            relative = source_path.relative_to(keg)
            target = component_dir / "installed" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target)
            copied.append(target.relative_to(output).as_posix())

        if not copied:
            if not isinstance(stable_url, str) or not stable_url:
                raise RuntimeError(f"Homebrew formula {formula} has no stable source URL")
            if not isinstance(checksum, str) or not checksum:
                raise RuntimeError(f"Homebrew formula {formula} has no stable source checksum")
            source_archive = _download_homebrew_source(
                root=root,
                formula=formula,
                version=version,
                url=stable_url,
                expected_sha256=checksum,
            )
            blobs = _source_archive_license_blobs(source_archive)
            if not blobs:
                raise RuntimeError(
                    f"No license texts found in Homebrew source archive for {formula} {version}"
                )
            for relative, content in sorted(blobs.items()):
                target = component_dir / "source" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                copied.append(target.relative_to(output).as_posix())

        raw_license = info.get("license")
        if not raw_license:
            raise RuntimeError(f"Homebrew formula {formula} has no declared license metadata")
        expression = (
            raw_license
            if isinstance(raw_license, str)
            else json.dumps(raw_license, sort_keys=True)
        )
        components.append(
            {
                "name": formula,
                "version": version,
                "type": "homebrew-formula",
                "license_expression": expression,
                "corresponding_source_required": is_copyleft(expression),
                "source": {
                    "url": stable_url,
                    "sha256": checksum,
                    "homepage": info.get("homepage"),
                    "note": (
                        "Version and license metadata reported by the installed Homebrew formula."
                    ),
                },
                "license_files": copied,
                "runtime_files": sorted(runtime_files),
            }
        )

    return _manifest(root, "macos", platform_tag, components)


def _manifest(
    root: Path,
    platform_name: str,
    platform_tag: str,
    components: list[dict[str, Any]],
) -> dict[str, Any]:
    project = load_toml(root / "pyproject.toml")["project"]
    return {
        "schema_version": SCHEMA_VERSION,
        "platform": platform_name,
        "platform_tag": platform_tag,
        "generator": "scripts/collect_licenses.py",
        "project": {
            "name": project["name"],
            "version": project["version"],
            "license": project.get("license"),
            "license_file": PROJECT_LICENSE_NAME,
        },
        "components": sorted(components, key=lambda item: item["name"].lower()),
    }


def render_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# Third-party licenses",
        "",
        "This file is generated from the exact source, MSYS2 package, or Homebrew ",
        "installation used for this platform build. The complete copied texts are under `texts/`.",
        "",
        f"Platform: `{manifest['platform_tag']}`",
        "",
        "| Component | Version | License | Runtime files |",
        "|---|---:|---|---:|",
    ]
    for component in manifest["components"]:
        lines.append(
            f"| {component['name']} | {component['version']} | "
            f"{component['license_expression']} | {len(component['runtime_files'])} |"
        )

    lines.extend(
        [
            "",
            "## Component details",
            "",
        ]
    )
    for component in manifest["components"]:
        lines.extend(
            [
                f"### {component['name']} {component['version']}",
                "",
                f"- License: `{component['license_expression']}`",
                f"- Package type: `{component['type']}`",
                "- License texts:",
            ]
        )
        lines.extend(f"  - `{path}`" for path in component["license_files"])
        source = component.get("source", {})
        if source.get("url"):
            lines.append(f"- Source/package URL: {source['url']}")
        if source.get("sha256"):
            lines.append(f"- SHA-256: `{source['sha256']}`")
        if component.get("corresponding_source_required"):
            lines.append(
                "- Corresponding source: required or potentially required by the selected license; "
                "retain the exact source/package reference from the manifest."
            )
        lines.append("")

    lines.extend(
        [
            "## Scope",
            "",
            "The project-specific build code is covered by `PROJECT_LICENSE.txt`. Bundled native ",
            "libraries remain under their respective upstream licenses. This generated inventory ",
            "is ",
            "an engineering aid and not legal advice.",
            "",
        ]
    )
    return "\n".join(lines)


def write_bundle(
    *,
    root: Path,
    output: Path,
    manifest: dict[str, Any],
    archive_path: Path | None,
) -> None:
    shutil.copy2(root / "LICENSE", output / PROJECT_LICENSE_NAME)
    (output / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / SUMMARY_NAME).write_text(render_summary(manifest), encoding="utf-8")
    verify_bundle(output)
    if archive_path is not None:
        create_archive(output, archive_path, manifest["platform_tag"])


def create_archive(bundle: Path, archive_path: Path, platform_tag: str) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.unlink(missing_ok=True)
    prefix = f"third-party-licenses-{platform_tag}"
    with zipfile.ZipFile(
        archive_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in sorted(item for item in bundle.rglob("*") if item.is_file()):
            relative = path.relative_to(bundle).as_posix()
            info = zipfile.ZipInfo(f"{prefix}/{relative}", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())


def verify_bundle(bundle: Path, runtime_root: Path | None = None) -> dict[str, Any]:
    required = (PROJECT_LICENSE_NAME, MANIFEST_NAME, SUMMARY_NAME)
    missing = [name for name in required if not (bundle / name).is_file()]
    if missing:
        raise RuntimeError(f"License bundle is incomplete: {missing}")

    manifest = json.loads((bundle / MANIFEST_NAME).read_text(encoding="utf-8"))
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError(f"Unsupported license manifest schema: {manifest.get('schema_version')}")
    components = manifest.get("components")
    if not isinstance(components, list) or not components:
        raise RuntimeError("License manifest has no components")

    owners: dict[str, str] = {}
    for component in components:
        if not component.get("license_expression"):
            raise RuntimeError(f"Component has no license expression: {component}")
        license_files = component.get("license_files", [])
        runtime_files = component.get("runtime_files", [])
        if not license_files:
            raise RuntimeError(f"Component has no copied license texts: {component['name']}")
        if not runtime_files:
            raise RuntimeError(f"Component has no runtime files: {component['name']}")
        for relative in license_files:
            if not (bundle / relative).is_file():
                raise RuntimeError(f"Missing copied license file: {relative}")
        for relative in runtime_files:
            previous = owners.setdefault(relative, component["name"])
            if previous != component["name"]:
                raise RuntimeError(
                    f"Runtime file {relative} is assigned to both {previous} and "
                    f"{component['name']}"
                )

    if runtime_root is not None:
        expected = native_runtime_files(runtime_root, manifest["platform"])
        missing_runtime = sorted(expected - set(owners))
        extra_runtime = sorted(set(owners) - expected)
        if missing_runtime or extra_runtime:
            raise RuntimeError(
                "License/runtime mapping mismatch: "
                f"missing={missing_runtime}, extra={extra_runtime}"
            )
    return manifest
