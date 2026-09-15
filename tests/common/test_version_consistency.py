from __future__ import annotations

import re
import tomllib
from pathlib import Path

from keith_ivt import version

ROOT = Path(__file__).resolve().parents[2]
FREEZE_MARKER = ROOT / "tools" / "release" / "RELEASE_FREEZE_MARKER"


def test_runtime_version_is_pep440_beta_and_matches_pyproject() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["version"] == version.VERSION

    if FREEZE_MARKER.exists():
        frozen = FREEZE_MARKER.read_text(encoding="utf-8").strip()
        assert frozen == version.VERSION
        assert re.fullmatch(r"\d+\.\d+b(?:\d+)?", version.VERSION)
    else:
        assert re.fullmatch(r"\d+\.\d+b\d+", version.VERSION)


def test_validation_script_reads_runtime_version_not_stale_literal() -> None:
    text = (ROOT / "tests" / "run_full_validation.py").read_text(encoding="utf-8")
    assert "version.VERSION" in text


def test_docs_describe_version_freeze_and_namespace_policy() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    versioning = (ROOT / "docs" / "VERSIONING.md").read_text(encoding="utf-8")
    assert "release-candidate identity" in readme
    assert "Every normal development commit increments" in versioning
    assert "release freeze" in versioning.lower()
    assert "human release owner" in versioning.lower()

    naming = (ROOT / "docs" / "NAMING.md").read_text(encoding="utf-8")
    assert "Public Python package/CLI namespace: `happymeasure`" in naming
    assert "Legacy implementation namespace: `keith_ivt`" in naming
    assert version.PACKAGE_NAME == "happymeasure"
    assert version.LEGACY_PACKAGE_NAME == "keith_ivt"
