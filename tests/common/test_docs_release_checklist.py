from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_release_checklist_has_current_release_gates() -> None:
    text = _read(DOCS / "RELEASE_CHECKLIST.md")
    for heading in (
        "## 1. Identity and tree hygiene",
        "## 2. Automated source validation",
        "## 3. Map Reconstruction release gate",
        "## 4. Desktop simulator/UX smoke",
        "## 5. Hardware safety gate",
        "## 6. Windows portable package",
        "## 7. Tag and GitHub Release",
        "## 8. Post-release",
    ):
        assert heading in text
    assert "1.1b6" in text
    assert "v1.1b6" in text
    assert ".[dev,map]" in text
    assert "QT_QPA_PLATFORM" in text


def test_docs_index_lists_current_owner_documents() -> None:
    text = _read(DOCS / "README.md")
    required_docs = [
        "ARCHITECTURE_CURRENT.md",
        "STATE_MACHINE.md",
        "ERROR_RECOVERY.md",
        "TRACE_SCHEMA.md",
        "HARDWARE_VALIDATION_PROTOCOL.md",
        "MAP_PROJECT_FORMAT.md",
        "RELEASE_CHECKLIST.md",
        "VALIDATION_STATUS.md",
        "DOCS_AUDIT.md",
        "RELEASE_NOTES_v1.1b6.md",
    ]
    for doc_name in required_docs:
        assert doc_name in text
        assert (DOCS / doc_name).exists(), f"docs index references missing file: {doc_name}"


def test_removed_diaries_and_completed_migration_plans_stay_removed() -> None:
    for doc_name in (
        "AGENT_HANDOFF.md",
        "TESTED_CURRENT.md",
        "MIGRATION_PLAN.md",
        "HARDWARE_DRIVER_MIGRATION.md",
    ):
        assert not (DOCS / doc_name).exists(), doc_name


def test_docs_audit_records_ownership_and_cleanup_rationale() -> None:
    text = _read(DOCS / "DOCS_AUDIT.md")
    assert "## Owners" in text
    assert "## 2026-09-11 cleanup decisions" in text
    assert "VALIDATION_STATUS.md" in text
    assert "AGENT_HANDOFF.md" in text


def test_versioning_policy_does_not_reuse_published_beta() -> None:
    text = _read(DOCS / "VERSIONING.md")
    assert "1.1b6" in text
    assert "Do not reuse a published version/tag" in text
