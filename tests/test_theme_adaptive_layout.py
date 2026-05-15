from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_theme_names_and_defaults_contract():
    settings = read("src/keith_ivt/data/settings.py")
    theme = read("src/keith_ivt/ui/theme.py")
    panels = read("src/keith_ivt/ui/panels.py")
    assert 'ui_theme: str = "Light"' in settings
    assert 'theme not in {"Light", "Dark", "Debug"}' in settings
    assert 'theme = "Debug"' in settings
    assert 'debug = theme == "Debug"' in theme
    assert '["Light", "Dark", "Debug"]' in panels
    assert '["High contrast", "Dark"]' not in panels


def test_adaptive_common_range_controls_stay_above_dynamic_editor():
    panels = read("src/keith_ivt/ui/panels.py")
    common_idx = panels.index("self.common_box = ttk.Frame")
    dynamic_idx = panels.index("self.dynamic_box = ttk.Frame")
    assert common_idx < dynamic_idx
    assert "Adaptive mode cannot push range/compliance fields out of view" in panels
    assert "self.source_range_row = self._range_control_row" in panels
    assert "self.measure_range_row = self._range_control_row" in panels


def test_light_debug_theme_border_intent():
    theme = read("src/keith_ivt/ui/theme.py")
    assert "frame_border = 2" in theme
    assert "frame_border = 0" in theme
    assert "splitter" in theme and "Nordic.TPanedwindow" in theme
