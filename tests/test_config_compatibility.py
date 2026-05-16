from __future__ import annotations

import json
from pathlib import Path

from keith_ivt.data.presets import load_presets, save_preset
from keith_ivt.data.settings import AppSettings, load_settings, save_settings


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_load_settings_tolerates_corrupt_or_non_dict_json(tmp_path: Path) -> None:
    bad = tmp_path / "settings.json"
    bad.write_text("{not json", encoding="utf-8")
    assert load_settings(bad) == AppSettings()

    write_json(bad, ["not", "a", "dict"])
    assert load_settings(bad) == AppSettings()


def test_load_settings_sanitizes_legacy_string_values(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    write_json(path, {
        "default_debug": "False",
        "cache_enabled": "yes",
        "default_autorange": "0",
        "auto_source_range": "false",
        "auto_measure_range": "true",
        "default_step": "not-a-number",
        "default_compliance": "-1",
        "default_terminal": "FRONT",
        "ui_theme": "Nordic Dark",
        "ui_font_size": "99",
        "log_max_bytes": "bad",
        "unknown_future_key": "ignored",
    })
    settings = load_settings(path)
    assert settings.default_debug is False
    assert settings.cache_enabled is True
    assert settings.default_autorange is False
    assert settings.auto_source_range is False
    assert settings.auto_measure_range is True
    assert settings.default_step == AppSettings().default_step
    assert settings.default_compliance == 0.0
    assert settings.default_terminal == "FRON"
    assert settings.ui_theme == "Dark"
    assert settings.ui_font_size == 18
    assert settings.log_max_bytes == AppSettings().log_max_bytes


def test_save_settings_writes_sanitized_payload(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    settings = AppSettings(log_max_bytes=1, ui_font_size=99, default_terminal="FRONT")
    save_settings(settings, path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["log_max_bytes"] == 1024
    assert raw["ui_font_size"] == 18
    assert raw["default_terminal"] == "FRON"


def test_load_presets_sanitizes_partial_legacy_presets(tmp_path: Path) -> None:
    path = tmp_path / "presets.json"
    write_json(path, {
        "Legacy": {
            "default_mode": "CURR",
            "default_start": "-5",
            "default_stop": "bad",
            "default_autorange": "False",
            "default_source_range": "1e-3",
            "unknown": "ignored",
        },
        "Broken": ["not", "dict"],
        "": {"default_mode": "VOLT"},
    })
    presets = load_presets(path)
    assert "Default" in presets
    assert "Legacy" in presets
    assert "Broken" not in presets
    assert "" not in presets
    assert presets["Legacy"]["default_mode"] == "CURR"
    assert presets["Legacy"]["default_start"] == -5.0
    assert presets["Legacy"]["default_stop"] == AppSettings().default_stop
    assert presets["Legacy"]["default_autorange"] is False
    assert presets["Legacy"]["default_source_range"] == 1e-3


def test_save_preset_rejects_empty_and_default_names(tmp_path: Path) -> None:
    path = tmp_path / "presets.json"
    for name in ("", "   ", "Default"):
        try:
            save_preset(name, {}, path)
        except ValueError:
            pass
        else:
            raise AssertionError(f"preset name should be rejected: {name!r}")
