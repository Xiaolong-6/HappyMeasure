"""Audit freshly built Windows portable artifacts before release publication."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tomllib
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

MIB = 1024 * 1024
MAP_ZIP_LIMIT = 80 * MIB
MAP_EXTRACTED_LIMIT = 180 * MIB

_TEXT_SUFFIXES = {
    ".cfg",
    ".csv",
    ".ini",
    ".json",
    ".log",
    ".md",
    ".py",
    ".txt",
    ".yaml",
    ".yml",
}
_FORBIDDEN_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".venv-build",
    ".venv-build-map",
    "__pycache__",
    "build",
    "hardware_smoke_results",
    "tests",
}
_FORBIDDEN_TOKENS = (
    "liux" + "16",
    "461" + "2952",
)
_HOME_PATH_PATTERNS = (
    re.compile(r"(?i)C:\\Users\\(?!%|<|\{)[A-Za-z0-9._-]+\\"),
    re.compile(r"(?i)C:/Users/(?!%|<|\{)[A-Za-z0-9._-]+/"),
    re.compile(r"(?i)/home/(?!<|\{)[A-Za-z0-9._-]+/"),
    re.compile(r"(?i)/Users/(?!<|\{)[A-Za-z0-9._-]+/"),
)
_MAP_FORBIDDEN_SUBSTRINGS = (
    "qt6webengine",
    "qtwebengine",
    "qt6quick",
    "/qml/",
    "qtpdf",
    "qt6multimedia",
)
_MAP_FORBIDDEN_COMPONENTS = {
    "cv2",
    "matplotlib",
    "numba",
    "pandas",
    "pil",
    "scipy",
    "sklearn",
}


def project_version(root: Path) -> str:
    with (root / "pyproject.toml").open("rb") as handle:
        return str(tomllib.load(handle)["project"]["version"])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def directory_stats(path: Path) -> tuple[int, int]:
    files = [item for item in path.rglob("*") if item.is_file()]
    return sum(item.stat().st_size for item in files), len(files)


def _name_failures(name: str, label: str) -> list[str]:
    normalized = name.replace("\\", "/")
    parts = [part.lower() for part in PurePosixPath(normalized).parts]
    failures = [
        f"{label}: forbidden path component {part!r} in {name!r}"
        for part in parts
        if part in _FORBIDDEN_PARTS
    ]
    if "/logs/" in f"/{normalized.lower().strip('/')}/" and not normalized.endswith("/"):
        failures.append(f"{label}: packaged runtime log file {name!r}")
    return failures


def _text_failures(text: str, label: str) -> list[str]:
    failures: list[str] = []
    lowered = text.lower()
    for token in _FORBIDDEN_TOKENS:
        if token.lower() in lowered:
            failures.append(f"{label}: contains forbidden private identifier")
    for pattern in _HOME_PATH_PATTERNS:
        match = pattern.search(text)
        if match:
            failures.append(f"{label}: contains private home path {match.group(0)!r}")
    return failures


def _map_runtime_failures(names: list[str], label: str) -> list[str]:
    failures: list[str] = []
    for name in names:
        normalized = name.replace("\\", "/").lower()
        padded = f"/{normalized.strip('/')}"
        for forbidden in _MAP_FORBIDDEN_SUBSTRINGS:
            if forbidden in padded:
                failures.append(
                    f"{label}: unexpected Map runtime dependency matching {forbidden!r}"
                )
        for part in PurePosixPath(normalized).parts:
            component = part.lower()
            for package in _MAP_FORBIDDEN_COMPONENTS:
                if component == package or component.startswith(f"{package}-"):
                    failures.append(
                        f"{label}: unexpected Map runtime package component {component!r}"
                    )
    return failures


def audit_zip(path: Path, app_name: str) -> list[str]:
    failures: list[str] = []
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        for name in names:
            failures.extend(_name_failures(name, path.name))
            suffix = Path(name).suffix.lower()
            if suffix in _TEXT_SUFFIXES:
                info = archive.getinfo(name)
                if info.file_size <= 2 * MIB:
                    text = archive.read(name).decode("utf-8", errors="replace")
                    failures.extend(_text_failures(text, f"{path.name}:{name}"))

        exe_suffix = f"{app_name}/{app_name}.exe".lower()
        if not any(name.replace("\\", "/").lower().endswith(exe_suffix) for name in names):
            failures.append(f"{path.name}: missing {app_name}.exe")
        if not any(
            "/_internal/" in f"/{name.replace(chr(92), '/').lower()}" for name in names
        ):
            failures.append(f"{path.name}: missing _internal runtime directory")
        if not any(name.lower().endswith("/readme_first.txt") for name in names):
            failures.append(f"{path.name}: missing README_FIRST.txt")

        if app_name == "MapReconstruction":
            failures.extend(_map_runtime_failures(names, path.name))
    return failures


def audit_folder(path: Path, app_name: str) -> list[str]:
    failures: list[str] = []
    if not (path / f"{app_name}.exe").is_file():
        failures.append(f"{path}: missing {app_name}.exe")
    if not (path / "_internal").is_dir():
        failures.append(f"{path}: missing _internal directory")
    if not (path / "README_FIRST.txt").is_file():
        failures.append(f"{path}: missing README_FIRST.txt")

    for item in path.rglob("*"):
        rel = item.relative_to(path).as_posix()
        failures.extend(_name_failures(rel, str(path)))
        if (
            item.is_file()
            and item.suffix.lower() in _TEXT_SUFFIXES
            and item.stat().st_size <= 2 * MIB
        ):
            text = item.read_text(encoding="utf-8", errors="replace")
            failures.extend(_text_failures(text, f"{path}:{rel}"))
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--manifest", type=Path, default=Path("dist/release-artifacts.json"))
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[2]
    dist = (root / args.dist).resolve() if not args.dist.is_absolute() else args.dist
    manifest_path = (
        (root / args.manifest).resolve() if not args.manifest.is_absolute() else args.manifest
    )
    version = project_version(root)
    failures: list[str] = []
    artifacts: list[dict[str, object]] = []

    for app_name in ("HappyMeasure", "MapReconstruction"):
        folder = dist / app_name
        archive = dist / f"{app_name}-{version}-windows-portable.zip"
        if not folder.is_dir():
            failures.append(f"missing portable folder: {folder}")
            continue
        if not archive.is_file():
            failures.append(f"missing portable ZIP: {archive}")
            continue

        failures.extend(audit_folder(folder, app_name))
        failures.extend(audit_zip(archive, app_name))
        extracted_size, file_count = directory_stats(folder)
        zip_size = archive.stat().st_size
        if app_name == "MapReconstruction":
            if extracted_size > MAP_EXTRACTED_LIMIT:
                failures.append(
                    "MapReconstruction extracted size exceeded release ceiling: "
                    f"{extracted_size / MIB:.2f} MiB > {MAP_EXTRACTED_LIMIT / MIB:.0f} MiB"
                )
            if zip_size > MAP_ZIP_LIMIT:
                failures.append(
                    "MapReconstruction ZIP size exceeded release ceiling: "
                    f"{zip_size / MIB:.2f} MiB > {MAP_ZIP_LIMIT / MIB:.0f} MiB"
                )

        artifacts.append(
            {
                "name": archive.name,
                "sha256": sha256_file(archive),
                "zip_bytes": zip_size,
                "zip_mib": round(zip_size / MIB, 2),
                "extracted_bytes": extracted_size,
                "extracted_mib": round(extracted_size / MIB, 2),
                "file_count": file_count,
            }
        )

    manifest = {
        "version": version,
        "commit": os.environ.get("GITHUB_SHA", ""),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "artifacts": artifacts,
        "map_size_limits_mib": {
            "zip": MAP_ZIP_LIMIT // MIB,
            "extracted": MAP_EXTRACTED_LIMIT // MIB,
        },
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(manifest, indent=2))
    if failures:
        print("PORTABLE ARTIFACT AUDIT FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PORTABLE ARTIFACT AUDIT PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
