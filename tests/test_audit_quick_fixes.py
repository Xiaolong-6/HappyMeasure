from __future__ import annotations

import tomllib
from pathlib import Path

from keith_ivt.ui.app_state import RunState

ROOT = Path(__file__).resolve().parents[1]


def test_runstate_running_remains_documented_alias_for_sweeping() -> None:
    assert "RUNNING" in RunState.__members__
    assert RunState.RUNNING is RunState.SWEEPING
    assert RunState.from_legacy_text("running") is RunState.SWEEPING


def test_pyproject_coverage_omit_has_no_redundant_happymeasure_diagnostics_entry() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    omit = data["tool"]["coverage"]["run"]["omit"]
    assert "src/happymeasure/*" in omit
    assert "src/happymeasure/diagnostics/*" not in omit


def test_coverage_and_mypy_policy_remain_explicit() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["tool"]["coverage"]["report"]["fail_under"] == 95
    assert data["tool"]["mypy"]["disallow_untyped_defs"] is False

    docs_audit = (ROOT / "docs" / "DOCS_AUDIT.md").read_text(encoding="utf-8")
    assert "documentation ownership" in docs_audit.lower() or "owners" in docs_audit.lower()
