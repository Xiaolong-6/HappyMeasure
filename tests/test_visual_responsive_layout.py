from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "keith_ivt"


def text(rel: str) -> str:
    return (SRC / rel).read_text(encoding="utf-8")


def test_navigation_push_rail_not_overlay_or_auto_hide():
    simple = text("ui/simple_app.py")
    nav = text("ui/navigation.py")
    assert "self._workspace_column = 1" in simple
    assert "self.main_pane.grid(row=0, column=self._workspace_column" in simple
    assert "place(" not in nav and "place_forget" not in nav
    assert "grid(row=0, column=0, rowspan=3" in nav
    assert "no longer auto-hides" in nav
    assert "builders[name](self.current_content)" in nav
    assert "self._bind_content_mousewheel_recursive(self.current_content)" in nav


def test_sweep_large_font_content_scrolls_from_child_widgets():
    scaffold = text("ui/ui_scaffold.py")
    nav = text("ui/navigation.py")
    assert "def _bind_content_mousewheel_recursive" in scaffold
    assert "for child in widget.winfo_children()" in scaffold
    assert "self._bind_content_mousewheel_recursive(self.current_content)" in nav
    assert "plot-wheel" in scaffold or "plot" in scaffold


def test_light_theme_is_modern_card_theme_and_debug_keeps_borders():
    theme = text("ui/theme.py")
    assert '"bg": "#F7F9FB"' in theme
    assert '"accent": "#3498DB"' in theme
    assert '"forest": "#1ABC9C"' in theme
    assert 'frame_border = 0' in theme
    assert 'debug = theme == "Debug"' in theme
    assert 'frame_border = 2' in theme


def test_operator_and_status_follow_workspace_column():
    assert 'column=getattr(self, "_workspace_column", 0)' in text("ui/operator_bar.py")
    assert 'column=getattr(self, "_workspace_column", 0)' in text("ui/status_bar.py")
