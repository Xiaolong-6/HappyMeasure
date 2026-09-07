from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def source(name: str) -> str:
    return (SRC / "keith_ivt" / name).read_text(encoding="utf-8")


def test_adaptive_editor_uses_multiline_segment_text_contract():
    text = source("ui/sweep_config.py")
    block = text[
        text.index("def _build_adaptive_segment_table") : text.index("def _adaptive_segment_text")
    ]
    assert "tk.Text(" in block
    assert "Remove duplicate scan values" in block
    assert "Ascending: 1, 20, 1" in block
    assert "Descending: 20, 1, 1" in block
    assert "either step sign is accepted" in block
    assert "＋ Row" not in block and "－ Row" not in block


def test_log_max_bytes_rotates_before_crossing_limit(tmp_path: Path):
    from keith_ivt.data.logging_utils import AppLog

    log_path = tmp_path / "logs" / "log.txt"
    app_log = AppLog(path=log_path, max_bytes=10_000)
    app_log.write("first" * 900)
    assert log_path.exists()
    assert log_path.stat().st_size <= 10_000
    app_log.write("second" * 1200)
    rotated = sorted(log_path.parent.glob("log_*.txt"))
    assert rotated, "existing log should rotate before a write that crosses max_bytes"
    assert "second" in log_path.read_text(encoding="utf-8")


def test_saved_settings_use_app_log_setter():
    text = source("ui/settings_preset_actions.py")
    assert "self.app_log.set_max_bytes" in text
    assert "self.app_log.max_bytes = int" not in text
