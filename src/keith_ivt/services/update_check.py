from __future__ import annotations

import json
import re
import socket
from dataclasses import dataclass
from urllib import error, request

GITHUB_RELEASES_API = "https://api.github.com/repos/{owner}/{repo}/releases"


@dataclass(frozen=True, order=True)
class ParsedVersion:
    major: int
    minor: int
    patch: int
    stage_rank: int
    prerelease_number: int


_STAGE_RANK = {
    "alpha": 0,
    "a": 0,
    "beta": 1,
    "b": 1,
    "rc": 2,
    "stable": 3,
}

_VERSION_RE = re.compile(
    r"^v?(?P<major>\d+)\.(?P<minor>\d+)(?:\.(?P<patch>\d+))?"
    r"(?:(?:-|\.?)(?P<stage>alpha|a|beta|b|rc)\.?(?P<num>\d+)?)?$",
    re.IGNORECASE,
)


def parse_version(value: str) -> ParsedVersion:
    """Parse HappyMeasure release tags into comparable version parts."""
    text = (value or "").strip()
    match = _VERSION_RE.match(text)
    if not match:
        raise ValueError(f"Unsupported version format: {value!r}")

    stage = (match.group("stage") or "stable").lower()
    return ParsedVersion(
        major=int(match.group("major")),
        minor=int(match.group("minor")),
        patch=int(match.group("patch") or 0),
        stage_rank=_STAGE_RANK[stage],
        prerelease_number=int(match.group("num") or 0),
    )


def is_newer_version(remote_version: str, current_version: str) -> bool:
    return parse_version(remote_version) > parse_version(current_version)


def _result(
    status: str,
    message: str,
    latest_version: str | None = None,
    release_url: str | None = None,
    asset_name: str | None = None,
    asset_download_url: str | None = None,
    asset_sha256: str | None = None,
) -> dict[str, str | None]:
    return {
        "status": status,
        "message": message,
        "latest_version": latest_version,
        "release_url": release_url,
        "asset_name": asset_name,
        "asset_download_url": asset_download_url,
        "asset_sha256": asset_sha256,
    }


def select_portable_zip_asset_details(
    release: dict,
) -> tuple[str | None, str | None, str | None]:
    """Return the preferred Windows portable zip asset from a GitHub release.

    GitHub automatically exposes source-code archives for every tag; those are
    not runnable PyInstaller builds.  The updater therefore only accepts an
    explicit release asset whose name looks like the HappyMeasure Windows
    portable package.
    """
    assets = release.get("assets") if isinstance(release, dict) else None
    if not isinstance(assets, list):
        return None, None, None

    candidates: list[tuple[int, str, str, str | None]] = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "").strip()
        url = str(asset.get("browser_download_url") or "").strip()
        digest = str(asset.get("digest") or "").strip().lower()
        digest_value = digest.removeprefix("sha256:")
        sha256: str | None = digest_value if re.fullmatch(r"[0-9a-f]{64}", digest_value) else None
        lowered = name.lower()
        if not name or not url or not lowered.endswith(".zip"):
            continue
        if "source" in lowered:
            continue
        score = 0
        if "happymeasure" in lowered:
            score += 3
        if "windows" in lowered or "win" in lowered:
            score += 2
        if "portable" in lowered:
            score += 2
        if score >= 5:
            candidates.append((-score, name, url, sha256))

    if not candidates:
        return None, None, None
    candidates.sort(key=lambda item: item[:3])
    _score, name, url, selected_sha256 = candidates[0]
    return name, url, selected_sha256


def select_portable_zip_asset(release: dict) -> tuple[str | None, str | None]:
    """Compatibility wrapper returning only the selected asset name and URL."""
    name, url, _sha256 = select_portable_zip_asset_details(release)
    return name, url


def check_github_release(
    owner: str,
    repo: str,
    current_version: str,
    include_prerelease: bool = True,
    timeout_s: float = 3.0,
) -> dict[str, str | None]:
    """Check GitHub Releases metadata without downloading or installing anything."""
    url = GITHUB_RELEASES_API.format(owner=owner, repo=repo)
    req = request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "HappyMeasure update metadata check",
        },
    )

    try:
        with request.urlopen(req, timeout=timeout_s) as response:
            payload = response.read().decode("utf-8")
        releases = json.loads(payload)
    except error.HTTPError as exc:
        return _result("error", f"Update check unavailable: {exc}")
    except (TimeoutError, socket.timeout, error.URLError):
        return _result("offline", "Update check unavailable: offline.")
    except Exception as exc:
        return _result("error", f"Update check unavailable: {exc}")

    if not isinstance(releases, list):
        return _result("error", "Update check unavailable.")

    latest_release = None
    for release in releases:
        if not isinstance(release, dict) or release.get("draft"):
            continue
        if not include_prerelease and release.get("prerelease"):
            continue
        latest_release = release
        break

    if latest_release is None:
        return _result("current", "No published releases found.")

    tag_name = str(latest_release.get("tag_name") or "").strip()
    release_url = latest_release.get("html_url")
    if not tag_name:
        return _result("error", "Update check unavailable.")

    try:
        remote = parse_version(tag_name)
        current = parse_version(current_version)
    except ValueError as exc:
        return _result("error", f"Update check unavailable: {exc}")

    display_version = tag_name if tag_name.startswith("v") else f"v{tag_name}"
    asset_name, asset_download_url, asset_sha256 = select_portable_zip_asset_details(latest_release)
    if remote > current:
        installer_note = (
            " Ready to download and install."
            if asset_download_url and asset_sha256
            else " Open the release page to download manually."
        )
        return _result(
            "newer",
            f"New version available: {display_version}.{installer_note}",
            display_version,
            str(release_url) if release_url else None,
            asset_name,
            asset_download_url,
            asset_sha256,
        )
    if remote < current:
        return _result(
            "ahead",
            f"Local version is newer than the latest published release ({display_version}).",
            display_version,
            str(release_url) if release_url else None,
            asset_name,
            asset_download_url,
            asset_sha256,
        )

    return _result(
        "current",
        "You are using the latest published version.",
        display_version,
        str(release_url) if release_url else None,
        asset_name,
        asset_download_url,
        asset_sha256,
    )
