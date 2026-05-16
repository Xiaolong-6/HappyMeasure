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
) -> dict[str, str | None]:
    return {
        "status": status,
        "message": message,
        "latest_version": latest_version,
        "release_url": release_url,
    }


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
        newer = is_newer_version(tag_name, current_version)
    except ValueError as exc:
        return _result("error", f"Update check unavailable: {exc}")

    display_version = tag_name if tag_name.startswith("v") else f"v{tag_name}"
    if newer:
        return _result(
            "newer",
            f"New version available: {display_version}. Please upgrade manually.",
            display_version,
            str(release_url) if release_url else None,
        )

    return _result(
        "current",
        "You are using the latest version.",
        display_version,
        str(release_url) if release_url else None,
    )
