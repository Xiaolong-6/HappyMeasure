from __future__ import annotations

import re
import tomllib
from pathlib import Path

from keith_ivt import version

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_version_is_pep440_alpha_and_matches_pyproject() -> None:
    assert version.VERSION == "0.7a1"
    assert re.fullmatch(r"\d+\.\d+a\d+", version.VERSION)
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["version"] == version.VERSION


def test_validation_script_reads_runtime_version_not_stale_literal() -> None:
    text = (ROOT / "tests" / "run_full_validation.py").read_text(encoding="utf-8")
    assert "version.VERSION" in text
    assert "0.6.0-alpha.5" not in text


def test_agent_docs_reference_current_version_and_package_cleanup_deferral() -> None:
    for rel in ["README.md", "docs/AGENT_START_HERE.md", "docs/AGENT_HANDOFF.md", "docs/CHANGELOG.md"]:
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert version.VERSION in text, rel
    notes = (ROOT / "docs" / "TECH_DEBT_AGENT_NOTES.md").read_text(encoding="utf-8")
    assert 'PACKAGE_NAME = "keith_ivt"' in notes
    assert "next packaging/namespace cleanup" in notes
