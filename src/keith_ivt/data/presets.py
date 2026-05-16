from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from keith_ivt.data.settings import AppSettings, sanitize_settings_dict

PRESETS_PATH = Path("config") / "presets.json"
SWEEP_PRESET_KEYS = {
    "default_mode", "default_sweep_kind", "default_start", "default_stop", "default_step",
    "default_constant_value", "default_duration_s", "default_interval_s",
    "default_compliance", "default_nplc", "default_autorange",
    "default_source_range", "default_measure_range", "default_adaptive_logic",
}


def default_sweep_preset() -> dict[str, Any]:
    settings = AppSettings()
    data = asdict(settings)
    return {k: data[k] for k in SWEEP_PRESET_KEYS}


def _clean(data: dict[str, Any]) -> dict[str, Any]:
    defaults = default_sweep_preset()
    sanitized = sanitize_settings_dict(data)
    cleaned = defaults.copy()
    for key in SWEEP_PRESET_KEYS:
        if key in data:
            cleaned[key] = sanitized[key]
    return cleaned


def load_presets(path: str | Path = PRESETS_PATH) -> dict[str, dict[str, Any]]:
    path = Path(path)
    out: dict[str, dict[str, Any]] = {"Default": default_sweep_preset()}
    if not path.exists():
        return out
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return out
    if not isinstance(raw, dict):
        return out
    for name, data in raw.items():
        if isinstance(name, str) and isinstance(data, dict) and name.strip():
            out[name] = _clean(data)
    out["Default"] = default_sweep_preset()
    return out


def save_preset(name: str, settings: dict[str, Any] | AppSettings, path: str | Path = PRESETS_PATH) -> Path:
    name = name.strip()
    if not name:
        raise ValueError("Preset name cannot be empty.")
    if name == "Default":
        raise ValueError("Default preset is built in and cannot be overwritten.")
    if isinstance(settings, AppSettings):
        data = asdict(settings)
    else:
        data = dict(settings)
    path = Path(path)
    presets = load_presets(path)
    presets[name] = _clean(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {k: v for k, v in presets.items() if k != "Default"}
    path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
    return path


def delete_preset(name: str, path: str | Path = PRESETS_PATH) -> Path:
    if name == "Default":
        return Path(path)
    path = Path(path)
    presets = load_presets(path)
    presets.pop(name, None)
    path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {k: v for k, v in presets.items() if k != "Default"}
    path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
    return path
