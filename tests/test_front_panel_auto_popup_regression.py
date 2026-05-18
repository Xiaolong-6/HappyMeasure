from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from keith_ivt.data.settings import AppSettings, sanitize_settings_dict


def source_text(relative: str) -> str:
    return (SRC / "keith_ivt" / relative).read_text(encoding="utf-8")


def test_front_panel_auto_popup_setting_defaults_enabled_and_sanitized() -> None:
    assert AppSettings().show_front_panel_on_start is True
    assert sanitize_settings_dict({})["show_front_panel_on_start"] is True
    assert sanitize_settings_dict({"show_front_panel_on_start": "no"})["show_front_panel_on_start"] is False


def test_start_stop_complete_error_paths_manage_auto_front_panel_popup() -> None:
    simple = source_text("ui/simple_app.py")
    sweep = source_text("ui/sweep_controller.py")
    status = source_text("ui/status_bar.py")
    settings = source_text("ui/settings_preset_actions.py")

    assert "self.show_front_panel_on_start = BooleanVar" in simple
    assert "self._front_panel_auto_opened = False" in simple
    assert "self._open_front_panel_for_sweep_start()" in sweep
    assert "def _open_front_panel_for_sweep_start" in sweep
    assert "self._open_front_panel_popup(auto_open=True)" in sweep
    assert sweep.count("self._close_auto_front_panel_popup()") >= 3
    assert "def _close_auto_front_panel_popup" in status
    assert "def _open_front_panel_popup(self, *, auto_open: bool = False)" in status
    assert "show_front_panel_on_start" in settings


def test_saved_auto_popup_setting_is_applied_to_live_tk_variable() -> None:
    settings_actions = source_text("ui/settings_preset_actions.py")

    assert "sanitize_settings_dict(data)" in settings_actions
    assert "self._apply_settings_dict(sanitized)" in settings_actions
    assert "self.settings = AppSettings(**sanitized)" in settings_actions


def test_debug_mode_factory_default_is_disabled() -> None:
    assert AppSettings().default_debug is False
    assert sanitize_settings_dict({})["default_debug"] is False
    assert sanitize_settings_dict({"default_debug": "yes"})["default_debug"] is True


def test_stop_paths_zero_live_status_before_closing_panel() -> None:
    sweep = Path("src/keith_ivt/ui/sweep_controller.py").read_text(encoding="utf-8")
    status = Path("src/keith_ivt/ui/status_bar.py").read_text(encoding="utf-8")
    assert "self._last_source_value = 0.0" in status
    assert "self._last_measured_value = 0.0" in status
    assert "self._reset_live_measurement_status()\n        self._close_auto_front_panel_popup()" in sweep
