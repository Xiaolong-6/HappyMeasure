from __future__ import annotations

import argparse
import re
import subprocess
import sys

_VERSION_RE = re.compile(r'^VERSION\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)
_PYPROJECT_RE = re.compile(r'^version\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)
_BETA_RE = re.compile(r"^(\d+)\.(\d+)b(\d+)$")
_RELEASE_OVERRIDE_MARKER = "[release-version]"


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def _file_at(ref: str, path: str) -> str:
    return _git("show", f"{ref}:{path}")


def _version_at(ref: str) -> str:
    text = _file_at(ref, "src/keith_ivt/version.py")
    match = _VERSION_RE.search(text)
    if not match:
        raise RuntimeError(f"{ref}: VERSION not found in src/keith_ivt/version.py")
    return match.group(1)


def _package_version_at(ref: str) -> str:
    text = _file_at(ref, "pyproject.toml")
    match = _PYPROJECT_RE.search(text)
    if not match:
        raise RuntimeError(f"{ref}: project version not found in pyproject.toml")
    return match.group(1)


def _beta_tuple(version: str) -> tuple[int, int, int] | None:
    match = _BETA_RE.fullmatch(version)
    if not match:
        return None
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def _assert_identity_consistent(ref: str) -> str:
    runtime = _version_at(ref)
    package = _package_version_at(ref)
    if runtime != package:
        raise RuntimeError(
            f"{ref}: runtime VERSION {runtime!r} != pyproject version {package!r}"
        )
    return runtime


def _first_parent(commit: str) -> str:
    line = _git("rev-list", "--parents", "-n", "1", commit)
    parts = line.split()
    if len(parts) < 2:
        raise RuntimeError(f"{commit}: commit has no parent; version sequence cannot be checked")
    return parts[1]


def _commit_message(commit: str) -> str:
    return _git("show", "-s", "--format=%B", commit)


def check_range(base: str, head: str) -> None:
    commits = [line for line in _git("rev-list", "--reverse", f"{base}..{head}").splitlines() if line]
    if not commits:
        _assert_identity_consistent(head)
        print(f"Version policy: no new commits in {base}..{head}; HEAD identity is consistent.")
        return

    for commit in commits:
        current = _assert_identity_consistent(commit)
        parent = _first_parent(commit)
        previous = _assert_identity_consistent(parent)
        message = _commit_message(commit)

        if _RELEASE_OVERRIDE_MARKER in message:
            print(f"Version policy: {commit[:8]} explicit human release-version override -> {current}")
            continue

        prev_beta = _beta_tuple(previous)
        cur_beta = _beta_tuple(current)
        if prev_beta is None or cur_beta is None:
            raise RuntimeError(
                f"{commit[:8]}: normal commits require beta identities; "
                f"parent={previous!r}, current={current!r}. "
                f"Use {_RELEASE_OVERRIDE_MARKER} only for deliberate human release finalization."
            )

        prev_major, prev_minor, prev_serial = prev_beta
        cur_major, cur_minor, cur_serial = cur_beta
        if (cur_major, cur_minor) != (prev_major, prev_minor) or cur_serial != prev_serial + 1:
            raise RuntimeError(
                f"{commit[:8]}: internal build must increment exactly once: "
                f"expected {prev_major}.{prev_minor}b{prev_serial + 1}, got {current}."
            )
        print(f"Version policy: {commit[:8]} {previous} -> {current} OK")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify HappyMeasure commit-by-commit internal beta version increments."
    )
    parser.add_argument("--base", required=True, help="Git base/ref before the commits to check")
    parser.add_argument("--head", required=True, help="Git head/ref to check")
    args = parser.parse_args(argv)
    try:
        check_range(args.base, args.head)
    except Exception as exc:
        print(f"VERSION POLICY FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
