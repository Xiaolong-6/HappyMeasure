from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_status_icons_are_canvas_rendered_not_emoji_labels() -> None:
    status_bar = (ROOT / "src" / "keith_ivt" / "ui" / "status_bar.py").read_text(encoding="utf-8")
    theme = (ROOT / "src" / "keith_ivt" / "ui" / "theme.py").read_text(encoding="utf-8")
    bridge = (ROOT / "src" / "keith_ivt" / "ui" / "app_state_bridge.py").read_text(encoding="utf-8")

    assert "tk.Canvas" in status_bar
    assert "_draw_connection_status_icon" in status_bar
    assert "_draw_status_gear" in status_bar
    assert 'width=16' in status_bar
    assert 'height=16' in status_bar
    assert "Segoe UI Emoji" not in theme
    assert "🔴" not in bridge
    assert "🟢" not in bridge
    assert "😈" not in bridge


def test_canvas_status_icon_supports_connection_and_simulator_modes() -> None:
    status_bar = (ROOT / "src" / "keith_ivt" / "ui" / "status_bar.py").read_text(encoding="utf-8")
    bridge = (ROOT / "src" / "keith_ivt" / "ui" / "app_state_bridge.py").read_text(encoding="utf-8")

    for token in ('"connected"', '"disconnected"', '"connecting"', '"error"', '"simulated"'):
        assert token in status_bar or token in bridge

    assert "canvas.create_oval" in status_bar
    assert "canvas.create_polygon" in status_bar
    assert "self._set_connection_status_icon(icon_kind)" in bridge
