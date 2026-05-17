from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def source_text(relative: str) -> str:
    return (SRC / "keith_ivt" / relative).read_text(encoding="utf-8")


def test_export_selected_uses_all_selected_traces() -> None:
    text = source_text("ui/trace_panel.py")
    assert "def _selected_traces" in text
    assert "for trace_id in self._selected_trace_ids()" in text
    assert "save_combined_csv(results, path)" in text
    assert "Saved {len(traces)} selected traces" in text


def test_default_settings_dialog_has_factory_restore_button() -> None:
    text = source_text("ui/settings_preset_actions.py")
    assert "Restore factory settings" in text
    assert "def restore_factory_fields" in text
    assert "AppSettings()" in text
    assert "Nothing is saved until you click Save Selected" in text
