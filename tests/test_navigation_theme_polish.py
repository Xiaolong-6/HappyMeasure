from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")

def test_push_nav_uses_single_commit_not_multiframe_animation():
    nav = read("src/keith_ivt/ui/navigation.py")
    assert "def _commit_drawer_width" in nav
    assert "self.root.after(12" not in nav
    assert "forced a full workspace reflow" in nav

def test_light_theme_removes_label_background_islands():
    theme = read("src/keith_ivt/ui/theme.py")
    assert '"panel": "#FFFFFF"' in theme
    assert "label_bg = card if not debug else panel" in theme
    helpers = read("src/keith_ivt/ui/widget_helpers.py")
    assert 'style="Card.TLabel"' in helpers
    assert 'kwargs.setdefault("style", "Muted.TLabel")' in helpers
