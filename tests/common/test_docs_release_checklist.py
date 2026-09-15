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
        "## 2. Automated core validation",
        "## 3. Map Reconstruction release gate",
        "## 4. Desktop simulator/UX and screenshots",
        "## 5. Hardware evidence",
        "## 6. Windows portable package CI",
        "## 7. Release publication",
        "## 8. Post-release",
    ):
        assert heading in text
    assert "check_version_sequence.py" in text
    assert ".[dev,map]" in text
    assert "QT_QPA_PLATFORM" in text
    assert "audit_portable_artifacts.py" in text
    assert "release-artifacts.json" in text


def test_docs_index_lists_current_owner_documents() -> None:
    text = _read(DOCS / "README.md")
    required_docs = [
        "ARCHITECTURE_CURRENT.md",
        "STATE_MACHINE.md",
        "ERROR_RECOVERY.md",
        "TROUBLESHOOTING.md",
        "TRACE_SCHEMA.md",
        "SETTINGS_COMPATIBILITY.md",
        "HARDWARE_VALIDATION_PROTOCOL.md",
        "MAP_PROJECT_FORMAT.md",
        "RELEASE_CHECKLIST.md",
        "VALIDATION_STATUS.md",
        "VERSIONING.md",
        "RELEASE_NOTES_NEXT.md",
    ]
    for doc_name in required_docs:
        assert doc_name in text
        assert (DOCS / doc_name).exists(), f"docs index references missing file: {doc_name}"


def test_obsolete_diaries_migrations_and_versioned_release_notes_are_removed() -> None:
    for doc_name in (
        "AGENT_HANDOFF.md",
        "TESTED_CURRENT.md",
        "MIGRATION_PLAN.md",
        "HARDWARE_DRIVER_MIGRATION.md",
        "SETTINGS_MIGRATION.md",
        "RESTART_MECHANISM.md",
        "DOCS_AUDIT.md",
        "RELEASE_NOTES_v0.7a1.md",
        "RELEASE_NOTES_v1.0b1.md",
        "RELEASE_NOTES_v1.1b1.md",
        "RELEASE_NOTES_v1.1b3.md",
        "RELEASE_NOTES_v1.1b4.md",
        "RELEASE_NOTES_v1.1b5.md",
        "RELEASE_NOTES_v1.1b6.md",
    ):
        assert not (DOCS / doc_name).exists(), doc_name


def test_current_docs_avoid_hardcoded_internal_build_identity() -> None:
    for doc_name in (
        "README.md",
        "ARCHITECTURE_CURRENT.md",
        "SETTINGS_COMPATIBILITY.md",
        "HARDWARE_VALIDATION_PROTOCOL.md",
        "RELEASE_CHECKLIST.md",
        "VALIDATION_STATUS.md",
    ):
        text = _read(DOCS / doc_name) if doc_name != "README.md" else _read(ROOT / "README.md")
        assert "current source candidate: **`1.1b" not in text.lower()


def test_hardware_preflight_docs_match_com_only_gui_detection() -> None:
    text = _read(DOCS / "HARDWARE_PREFLIGHT.md")
    assert "Detect COM" in text
    assert "send **no SCPI command**" in text
    assert "never scans alternate baud rates" in text
    assert ":OUTP?" in text
    assert "does not source voltage/current" in text


def test_versioning_policy_covers_development_increments_and_release_freeze() -> None:
    text = _read(DOCS / "VERSIONING.md")
    assert "Every normal development commit increments" in text
    assert "beta serial by exactly one" in text
    assert "release freeze" in text.lower()
    assert "1.2b" in text


def test_stop_safety_copy_is_cooperative_not_emergency() -> None:
    paths = (
        DOCS / "HARDWARE_DRY_RUN_GUIDE.md",
        ROOT / "src" / "keith_ivt" / "ui" / "operator_bar.py",
        ROOT / "src" / "keith_ivt" / "ui" / "panels.py",
        ROOT / "src" / "keith_ivt" / "ui" / "sweep_controller.py",
    )
    for path in paths:
        text = _read(path)
        assert "Emergency Stop" not in text
        assert "Emergency stop requested" not in text
    assert "cooperative" in _read(DOCS / "HARDWARE_DRY_RUN_GUIDE.md").lower()


def test_settings_doc_covers_new_persistent_preferences() -> None:
    text = _read(DOCS / "SETTINGS_COMPATIBILITY.md")
    assert "auto_save_backup" in text
    assert "record_log" in text
    assert "Last N points" in text
    assert "while a measurement is running" in text


def test_readme_references_all_release_screenshots() -> None:
    readme = _read(ROOT / "README.md")
    screenshot_dir = DOCS / "screenshots"
    names = (
        "happymeasure-hardware.png",
        "happymeasure-sweep-result.png",
        "happymeasure-front-panel-popup.png",
        "map-reconstruction-preparation.png",
        "map-reconstruction-reconstruction.png",
        "map-reconstruction-analysis.png",
    )
    assert "## Screenshots" in readme
    for name in names:
        assert f"docs/screenshots/{name}" in readme
        assert (screenshot_dir / name).is_file(), name
