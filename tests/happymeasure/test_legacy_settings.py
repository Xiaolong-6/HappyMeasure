from __future__ import annotations

from keith_ivt.data.settings import AppSettings, load_settings, sanitize_settings_dict, save_settings


def test_legacy_high_contrast_theme_migrates_to_debug(tmp_path) -> None:
    path = tmp_path / "settings.json"
    save_settings(AppSettings(ui_theme="High contrast"), path)

    migrated = load_settings(path)

    assert migrated.ui_theme == "Debug"


def test_front_panel_auto_popup_defaults_enabled_and_sanitizes_boolean_text() -> None:
    assert AppSettings().show_front_panel_on_start is True
    assert sanitize_settings_dict({})["show_front_panel_on_start"] is True
    assert sanitize_settings_dict({"show_front_panel_on_start": "no"})[
        "show_front_panel_on_start"
    ] is False


def test_debug_simulator_defaults_disabled_and_sanitizes_boolean_text() -> None:
    assert AppSettings().default_debug is False
    assert sanitize_settings_dict({})["default_debug"] is False
    assert sanitize_settings_dict({"default_debug": "yes"})["default_debug"] is True
