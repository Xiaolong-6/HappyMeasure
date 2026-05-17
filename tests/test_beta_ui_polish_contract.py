from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_navigation_subtitle_and_tab_tooltips_are_user_facing() -> None:
    nav = read("src/keith_ivt/ui/navigation.py")
    assert 'text="Your lab buddy"' in nav
    assert "measurement workspace" not in nav.lower()
    assert "NAV_TIPS" in nav
    for name, summary in {
        "Hardware": "Connect to a real Keithley instrument",
        "Sweep": "Configure source mode",
        "Preset": "Save and restore common measurement setups",
        "Restore": "Recover automatically backed-up sweep data",
        "Settings": "Adjust simulator mode",
        "Log": "Review recent application events",
        "About": "View version",
    }.items():
        assert f'"{name}":' in nav
        assert summary in nav
    assert 'self.NAV_TIPS.get(name' in nav


def test_about_update_notice_is_never_blank_and_dark_theme_uses_card_styles() -> None:
    simple = read("src/keith_ivt/ui/simple_app.py")
    panels = read("src/keith_ivt/ui/panels.py")
    theme = read("src/keith_ivt/ui/theme.py")
    updates = read("src/keith_ivt/ui/update_controller.py")
    assert "default_update_text" in simple
    assert "Manual upgrade remains available" in simple
    assert "No network. Update status unknown" in updates
    assert "You are up to date" in updates
    assert 'style="AboutTitle.TLabel"' in panels
    assert 'style="AboutBody.TLabel"' in panels
    assert 'self.style.configure("AboutTitle.TLabel", background=card' in theme
    assert 'self.style.configure("AboutBody.TLabel", background=card' in theme


def test_disabled_sweep_controls_use_theme_disabled_palette() -> None:
    theme = read("src/keith_ivt/ui/theme.py")
    assert 'disabled_bg = self._palette["disabled"]' in theme
    assert 'foreground=[("disabled", disabled_fg)]' in theme
    assert 'background=[("disabled", disabled_bg)' in theme
    assert 'fieldbackground=[("disabled", disabled_bg)]' in theme
    assert '"#B8C3CA" if dark' in theme


def test_status_icons_follow_ui_scale_not_fixed_emoji_size() -> None:
    status = read("src/keith_ivt/ui/status_bar.py")
    assert "def _status_icon_size" in status
    assert "size_pt * 1.45" in status
    assert "canvas.configure(width=icon_size, height=icon_size" in status
    assert "Tk/Windows may render emoji circles" in status
    assert "_draw_status_gear(canvas, colors, icon_size)" in status
    assert "width=16" not in status
    assert "height=16" not in status
