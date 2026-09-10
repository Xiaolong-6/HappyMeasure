from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from keith_ivt.data.presets import (
    PRESET_SCHEMA_VERSION,
    _clean,
    default_sweep_preset,
    delete_preset,
    load_presets,
    normalize_preset,
    save_preset,
)
from keith_ivt.data.settings import AppSettings


def test_default_preset_contains_only_hardware_and_visible_step_state() -> None:
    preset = default_sweep_preset()
    assert set(preset) == {"schema_version", "hardware", "sweep"}
    assert preset["schema_version"] == PRESET_SCHEMA_VERSION
    assert set(preset["hardware"]) == {"port", "baud_rate", "terminal", "sense_mode"}
    assert set(preset["sweep"]) == {
        "mode",
        "kind",
        "hysteresis",
        "compliance",
        "nplc",
        "delay_s",
        "auto_source_range",
        "source_range",
        "auto_measure_range",
        "measure_range",
        "parameters",
        "acquisition",
    }
    assert preset["sweep"]["acquisition"]["profile"] == "Standard"
    assert set(preset["sweep"]["parameters"]) == {"start", "stop", "step"}


def test_load_presets_returns_default_when_file_missing(tmp_path: Path) -> None:
    path = tmp_path / "nonexistent" / "presets.json"
    presets = load_presets(path)
    assert "Default" in presets
    assert presets["Default"] == default_sweep_preset()


def test_load_presets_returns_default_on_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("not valid json {{{", encoding="utf-8")
    presets = load_presets(path)
    assert "Default" in presets


def test_load_presets_returns_default_when_not_dict(tmp_path: Path) -> None:
    path = tmp_path / "list.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    presets = load_presets(path)
    assert "Default" in presets


def test_load_presets_valid_file(tmp_path: Path) -> None:
    path = tmp_path / "presets.json"
    data = {"MyPreset": {"default_mode": "CURR"}}
    path.write_text(json.dumps(data), encoding="utf-8")
    presets = load_presets(path)
    assert "Default" in presets
    assert "MyPreset" in presets
    assert presets["MyPreset"]["sweep"]["mode"] == "CURR"


def test_load_presets_skips_non_string_names(tmp_path: Path) -> None:
    path = tmp_path / "presets.json"
    data = {123: {"default_mode": "CURR"}, "Valid": {"default_mode": "VOLT"}}
    path.write_text(json.dumps(data), encoding="utf-8")
    presets = load_presets(path)
    assert "Valid" in presets
    assert 123 not in presets


def test_load_presets_skips_non_dict_values(tmp_path: Path) -> None:
    path = tmp_path / "presets.json"
    data = {"Bad": "not a dict", "Good": {"default_mode": "VOLT"}}
    path.write_text(json.dumps(data), encoding="utf-8")
    presets = load_presets(path)
    assert "Good" in presets
    assert "Bad" not in presets


def test_load_presets_skips_empty_name(tmp_path: Path) -> None:
    path = tmp_path / "presets.json"
    data = {"": {"default_mode": "VOLT"}, "  ": {"default_mode": "CURR"}}
    path.write_text(json.dumps(data), encoding="utf-8")
    presets = load_presets(path)
    assert "" not in presets
    assert "  " not in presets


def test_save_preset_empty_name_raises(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(ValueError, match="empty"):
        save_preset("", {}, path=tmp_path / "presets.json")


def test_save_preset_default_name_raises(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(ValueError, match="Default"):
        save_preset("Default", {}, path=tmp_path / "presets.json")


def test_save_preset_creates_file(tmp_path: Path) -> None:
    path = tmp_path / "presets.json"
    result = save_preset("TestPreset", {"default_mode": "CURR"}, path=path)
    assert result == path
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "TestPreset" in data
    assert data["TestPreset"]["schema_version"] == PRESET_SCHEMA_VERSION
    assert data["TestPreset"]["sweep"]["mode"] == "CURR"
    assert "Default" not in data


def test_save_preset_with_app_settings(tmp_path: Path) -> None:
    path = tmp_path / "presets.json"
    settings = AppSettings()
    save_preset("FromSettings", settings, path=path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "FromSettings" in data


def test_save_preset_overwrites_existing(tmp_path: Path) -> None:
    path = tmp_path / "presets.json"
    save_preset("Test", {"default_mode": "CURR"}, path=path)
    save_preset("Test", {"default_mode": "VOLT"}, path=path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["Test"]["sweep"]["mode"] == "VOLT"


def test_delete_preset_removes_from_file(tmp_path: Path) -> None:
    path = tmp_path / "presets.json"
    save_preset("ToDelete", {"default_mode": "CURR"}, path=path)
    delete_preset("ToDelete", path=path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "ToDelete" not in data
    assert "Default" not in data


def test_delete_preset_default_returns_path(tmp_path: Path) -> None:
    path = tmp_path / "presets.json"
    result = delete_preset("Default", path=path)
    assert result == path


def test_delete_preset_nonexistent_returns_path(tmp_path: Path) -> None:
    path = tmp_path / "presets.json"
    result = delete_preset("Nonexistent", path=path)
    assert result == path


def test_clean_applies_defaults_for_missing_keys() -> None:
    data = {"default_mode": "CURR"}
    cleaned = _clean(data)
    assert cleaned["sweep"]["mode"] == "CURR"
    assert cleaned["sweep"]["kind"] == "STEP"
    assert cleaned["hardware"] == default_sweep_preset()["hardware"]


def test_v2_time_snapshot_round_trips_and_discards_unrelated_content(tmp_path: Path) -> None:
    path = tmp_path / "presets.json"
    snapshot = {
        "schema_version": PRESET_SCHEMA_VERSION,
        "hardware": {
            "port": "COM8",
            "baud_rate": 19200,
            "terminal": "FRON",
            "sense_mode": "4W",
            "theme": "must be discarded",
        },
        "sweep": {
            "mode": "CURR",
            "kind": "TIME",
            "hysteresis": True,
            "compliance": 5.0,
            "nplc": 0.5,
            "delay_s": 0.1,
            "auto_source_range": False,
            "source_range": 0.001,
            "auto_measure_range": True,
            "measure_range": 10.0,
            "parameters": {
                "constant_value": 0.0001,
                "until_stop": True,
                "duration_s": 60.0,
                "interval_s": 0.5,
                "hidden_step": 99,
            },
        },
        "plot_layout": "must be discarded",
    }

    save_preset("Time", snapshot, path)
    loaded = load_presets(path)["Time"]

    assert loaded["hardware"] == {
        "port": "COM8",
        "baud_rate": 19200,
        "terminal": "FRON",
        "sense_mode": "4W",
    }
    assert loaded["sweep"]["hysteresis"] is False
    assert loaded["sweep"]["auto_source_range"] is False
    assert loaded["sweep"]["auto_measure_range"] is True
    assert loaded["sweep"]["parameters"] == {
        "constant_value": 0.0001,
        "until_stop": True,
        "duration_s": 60.0,
        "interval_s": 0.5,
    }
    assert "plot_layout" not in loaded


def test_v2_adaptive_snapshot_preserves_raw_text_and_debug_model() -> None:
    raw_segments = "# coarse\n0.1, 1, 0.1\n\n1, 20, 1"
    normalized = normalize_preset(
        {
            "schema_version": PRESET_SCHEMA_VERSION,
            "hardware": {},
            "sweep": {
                "kind": "ADAPTIVE",
                "hysteresis": "yes",
                "debug_model": "Custom debug load",
                "parameters": {
                    "segments": raw_segments,
                    "remove_duplicates": False,
                },
            },
        }
    )

    assert normalized["sweep"]["hysteresis"] is True
    assert normalized["sweep"]["debug_model"] == "Custom debug load"
    assert normalized["sweep"]["parameters"] == {
        "segments": raw_segments,
        "remove_duplicates": False,
    }


def test_legacy_manual_output_and_numeric_boole_migrate() -> None:
    normalized = normalize_preset(
        {
            "default_sweep_kind": "MANUAL_OUTPUT",
            "default_autorange": 0,
            "default_debug": True,
            "default_debug_model": "Linear resistor 1 kOhm",
        }
    )

    assert normalized["sweep"]["kind"] == "MANUAL_OUTPUT"
    assert normalized["sweep"]["parameters"] == {}
    assert normalized["sweep"]["auto_source_range"] is False
    assert normalized["sweep"]["auto_measure_range"] is False
    assert normalized["sweep"]["debug_model"] == "Linear resistor 1 kOhm"


def test_v2_snapshot_without_acquisition_normalizes_to_standard() -> None:
    normalized = normalize_preset(
        {
            "schema_version": 2,
            "hardware": {},
            "sweep": {"kind": "TIME"},
        }
    )

    assert normalized["schema_version"] == PRESET_SCHEMA_VERSION
    assert normalized["sweep"]["acquisition"]["profile"] == "Standard"
    assert normalized["sweep"]["acquisition"]["range_telemetry"] is True
    assert normalized["sweep"]["acquisition"]["measurement_only_read"] is False


def test_v3_fast_acquisition_round_trip() -> None:
    acquisition = {
        "profile": "Fast",
        "zero_refresh_before_run": True,
        "autozero_during_run": False,
        "digital_filter": False,
        "digital_filter_count": 2,
        "concurrent_measurement": False,
        "display_during_run": True,
        "measurement_only_read": True,
        "range_telemetry": False,
        "source_write_each_sample": False,
        "trigger_delay_s": 0.0,
    }
    normalized = normalize_preset(
        {
            "schema_version": PRESET_SCHEMA_VERSION,
            "hardware": {},
            "sweep": {"kind": "TIME", "acquisition": dict(acquisition)},
        }
    )

    assert normalized["sweep"]["acquisition"] == acquisition


def test_v3_custom_acquisition_preserves_all_advanced_fields() -> None:
    acquisition = {
        "profile": "Custom",
        "zero_refresh_before_run": False,
        "autozero_during_run": True,
        "digital_filter": True,
        "digital_filter_count": 5,
        "concurrent_measurement": True,
        "display_during_run": False,
        "measurement_only_read": False,
        "range_telemetry": True,
        "source_write_each_sample": True,
        "trigger_delay_s": 0.004,
    }
    normalized = normalize_preset(
        {
            "schema_version": PRESET_SCHEMA_VERSION,
            "hardware": {},
            "sweep": {"kind": "TIME", "acquisition": dict(acquisition)},
        }
    )

    assert normalized["sweep"]["acquisition"] == acquisition


def test_v3_acquisition_sanitizes_invalid_values() -> None:
    normalized = normalize_preset(
        {
            "schema_version": PRESET_SCHEMA_VERSION,
            "hardware": {},
            "sweep": {
                "kind": "TIME",
                "acquisition": {
                    "profile": "UltraFast",
                    "digital_filter_count": 0,
                    "trigger_delay_s": -1.0,
                    "range_telemetry": "yes",
                },
            },
        }
    )

    acquisition = normalized["sweep"]["acquisition"]
    assert acquisition["profile"] == "Standard"
    assert acquisition["digital_filter_count"] == 2
    assert acquisition["trigger_delay_s"] == 0.0
    assert acquisition["range_telemetry"] is True


def test_legacy_flat_preset_normalizes_to_standard_acquisition() -> None:
    normalized = normalize_preset({"default_mode": "VOLT"})

    assert normalized["schema_version"] == PRESET_SCHEMA_VERSION
    assert normalized["sweep"]["acquisition"]["profile"] == "Standard"


def test_descending_step_preset_preserves_negative_step() -> None:
    normalized = normalize_preset(
        {
            "schema_version": PRESET_SCHEMA_VERSION,
            "hardware": {},
            "sweep": {
                "kind": "STEP",
                "parameters": {"start": 20, "stop": 1, "step": -1},
            },
        }
    )

    assert normalized["sweep"]["parameters"] == {
        "start": 20.0,
        "stop": 1.0,
        "step": -1.0,
    }
