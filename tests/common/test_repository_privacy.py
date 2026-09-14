from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_TEXT_SUFFIXES = {
    ".bat",
    ".cfg",
    ".ini",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".spec",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

# Construct previously leaked identifiers without storing the literal values in
# tracked text; the scanner still catches those literals anywhere else.
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


def _tracked_text_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    paths: list[Path] = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        rel = raw.decode("utf-8")
        path = ROOT / rel
        if path.suffix.lower() in _TEXT_SUFFIXES or path.name in {"AGENTS.md", "LICENSE"}:
            paths.append(path)
    return paths


def test_tracked_text_has_no_private_workstation_or_instrument_identifiers() -> None:
    failures: list[str] = []
    for path in _tracked_text_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(ROOT)
        lowered = text.lower()
        for token in _FORBIDDEN_TOKENS:
            if token.lower() in lowered:
                failures.append(f"{rel}: contains forbidden identifier {token!r}")
        for pattern in _HOME_PATH_PATTERNS:
            match = pattern.search(text)
            if match:
                failures.append(f"{rel}: contains workstation-specific home path {match.group(0)!r}")
    assert not failures, "\n".join(failures)
