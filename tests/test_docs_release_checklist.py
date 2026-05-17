from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_release_checklist_has_required_sections() -> None:
    text = _read(DOCS / "RELEASE_CHECKLIST.md")

    required_headings = [
        "## 0. Release identity",
        "## 1. Source tree hygiene",
        "## 2. Version and naming consistency",
        "## 3. Documentation audit",
        "## 4. Source validation",
        "## 5. Manual simulator smoke checks",
        "## 6. Hardware validation gate",
        "## 7. Version bump and release notes",
        "## 8. Windows portable packaging",
        "## 9. Git and GitHub release",
        "## 10. Post-release verification",
    ]

    for heading in required_headings:
        assert heading in text


def test_release_checklist_links_to_existing_owner_docs() -> None:
    text = _read(DOCS / "RELEASE_CHECKLIST.md")
    doc_refs = sorted(set(re.findall(r"docs[\\/][A-Za-z0-9_./-]+\.md", text)))
    assert doc_refs, "release checklist should reference owner docs"

    for ref in doc_refs:
        relative = ref.replace("\\", "/")
        assert (ROOT / relative).exists(), f"missing referenced doc: {ref}"


def test_docs_index_lists_release_owner_documents() -> None:
    text = _read(DOCS / "README.md")

    required_docs = [
        "RELEASE_CHECKLIST.md",
        "MANUAL_SMOKE_TESTS.md",
        "TRACE_SCHEMA.md",
        "HARDWARE_PREFLIGHT.md",
        "HARDWARE_VALIDATION_PROTOCOL.md",
        "WINDOWS_PORTABLE_BUILD.md",
        "WINDOWS_PYTHON314_BUILD.md",
        "AGENT_HANDOFF.md",
        "NEW_THREAD_CONTEXT.md",
        "DOCS_AUDIT.md",
    ]

    for doc_name in required_docs:
        assert doc_name in text
        assert (DOCS / doc_name).exists(), f"docs index references missing file: {doc_name}"


def test_docs_audit_records_owner_map_and_future_cleanup() -> None:
    text = _read(DOCS / "DOCS_AUDIT.md")
    assert "## Ownership map" in text
    assert "## Future cleanup candidates" in text
    assert "RELEASE_CHECKLIST.md" in text
    assert "CODEX_DIARY_TEMP.md" in text
