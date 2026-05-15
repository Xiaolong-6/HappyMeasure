from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from keith_ivt.data.settings import AppSettings, load_settings, save_settings


def test_trace_panel_imports_touch_menu_helpers():
    text = (ROOT / "src/keith_ivt/ui/trace_panel.py").read_text(encoding="utf-8")
    assert "from keith_ivt.ui.menu_utils import make_touch_menu, popup_menu" in text
    assert "make_touch_menu(" in text
    assert "popup_menu(" in text


def test_light_is_default_and_debug_replaces_high_contrast(tmp_path):
    default_settings = load_settings(tmp_path / "missing.json")
    assert default_settings.ui_theme == "Light"

    p = tmp_path / "settings.json"
    save_settings(AppSettings(ui_theme="High contrast"), p)
    migrated = load_settings(p)
    assert migrated.ui_theme == "Debug"

    panels = (ROOT / "src/keith_ivt/ui/panels.py").read_text(encoding="utf-8")
    assert '["Light", "Dark", "Debug"]' in panels
    assert '["High contrast", "Dark"]' not in panels


def test_button_and_dark_theme_styles_keep_visible_borders():
    theme = (ROOT / "src/keith_ivt/ui/theme.py").read_text(encoding="utf-8")
    assert 'ui_theme", "Light"' in theme
    assert 'relief="solid", borderwidth=1' in theme
    for style_name in [
        '"TButton"',
        '"Soft.TButton"',
        '"Drawer.TButton"',
        '"Start.TButton"',
        '"Stop.TButton"',
        '"TinyIcon.TButton"',
    ]:
        assert style_name in theme
    assert '"card": "#FFFFFF"' in theme and '"card": "#20262B"' in theme
    assert '"input": "#FFFFFF"' in theme and '"input": "#20262B"' in theme
