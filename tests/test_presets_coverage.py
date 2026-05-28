from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from keith_ivt.data.presets import (
    SWEEP_PRESET_KEYS,
    _clean,
    default_sweep_preset,
    delete_preset,
    load_presets,
    save_preset,
)
from keith_ivt.data.settings import AppSettings


def test_default_sweep_preset_keys_match_settings() -> None:
    preset = default_sweep_preset()
    assert isinstance(preset, dict)
    for key in SWEEP_PRESET_KEYS:
        assert key in preset


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
    assert presets["MyPreset"]["default_mode"] == "CURR"


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
    assert data["TestPreset"]["default_mode"] == "CURR"
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
    assert data["Test"]["default_mode"] == "VOLT"


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
    assert cleaned["default_mode"] == "CURR"
    for key in SWEEP_PRESET_KEYS:
        assert key in cleaned
