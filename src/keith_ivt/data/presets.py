from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from keith_ivt.data.settings import AppSettings, sanitize_settings_dict

PRESETS_PATH = Path("config") / "presets.json"
PRESET_SCHEMA_VERSION = 3

ACQUISITION_PROFILES = ("Standard", "Fast", "Custom")


def default_acquisition_state() -> dict[str, Any]:
    """Return a fresh conservative Standard acquisition block.

    Old presets without acquisition data normalize to this; Fast is never
    inferred from NPLC or range settings.
    """

    return {
        "profile": "Standard",
        "zero_refresh_before_run": False,
        "autozero_during_run": True,
        "digital_filter": False,
        "digital_filter_count": 2,
        "concurrent_measurement": True,
        "display_during_run": True,
        "measurement_only_read": False,
        "range_telemetry": True,
        "source_write_each_sample": False,
        "trigger_delay_s": 0.0,
    }


def clean_acquisition_state(raw: Any) -> dict[str, Any]:
    """Validate a stored acquisition block, falling back to Standard."""

    state = default_acquisition_state()
    if not isinstance(raw, dict):
        return state
    profile = str(raw.get("profile", "Standard")).strip()
    state["profile"] = profile if profile in ACQUISITION_PROFILES else "Standard"
    for key in (
        "zero_refresh_before_run",
        "autozero_during_run",
        "digital_filter",
        "concurrent_measurement",
        "display_during_run",
        "measurement_only_read",
        "range_telemetry",
        "source_write_each_sample",
    ):
        state[key] = _bool_value(raw.get(key), state[key])
    try:
        count = int(raw.get("digital_filter_count", 2))
    except (TypeError, ValueError):
        count = 2
    state["digital_filter_count"] = count if count >= 1 else 2
    try:
        trigger = float(raw.get("trigger_delay_s", 0.0))
    except (TypeError, ValueError):
        trigger = 0.0
    state["trigger_delay_s"] = trigger if trigger >= 0 else 0.0
    return state

# Retained as a compatibility name for callers that still import it. New
# presets use the nested v2 snapshot below, not these legacy flat keys.
SWEEP_PRESET_KEYS = {
    "default_mode",
    "default_sweep_kind",
    "default_start",
    "default_stop",
    "default_step",
    "default_constant_value",
    "default_duration_s",
    "default_constant_until_stop",
    "default_interval_s",
    "default_compliance",
    "default_nplc",
    "default_delay_s",
    "default_autorange",
    "auto_source_range",
    "auto_measure_range",
    "default_source_range",
    "default_measure_range",
    "default_adaptive_logic",
    "default_adaptive_segments",
    "default_adaptive_remove_duplicates",
    "default_debug_model",
}

_VALID_SWEEP_KINDS = {"STEP", "TIME", "ADAPTIVE", "MANUAL_OUTPUT"}


def _bool_value(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off", ""}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def _snapshot_from_flat(data: dict[str, Any]) -> dict[str, Any]:
    """Convert legacy flat settings/presets into a complete v2 snapshot."""
    sanitized = sanitize_settings_dict(data)
    raw_kind = str(data.get("default_sweep_kind", sanitized["default_sweep_kind"])).upper()
    kind = raw_kind if raw_kind in _VALID_SWEEP_KINDS else sanitized["default_sweep_kind"]
    legacy_auto = _bool_value(data.get("default_autorange"), bool(sanitized["default_autorange"]))
    auto_source = _bool_value(data.get("auto_source_range"), legacy_auto)
    auto_measure = _bool_value(data.get("auto_measure_range"), legacy_auto)

    sweep: dict[str, Any] = {
        "mode": sanitized["default_mode"],
        "kind": kind,
        "hysteresis": _bool_value(data.get("hysteresis", data.get("default_hysteresis")), False),
        "compliance": sanitized["default_compliance"],
        "nplc": sanitized["default_nplc"],
        "delay_s": sanitized["default_delay_s"],
        "auto_source_range": auto_source,
        "source_range": sanitized["default_source_range"],
        "auto_measure_range": auto_measure,
        "measure_range": sanitized["default_measure_range"],
    }
    if (
        "default_debug_model" in data
        and str(data["default_debug_model"]).strip()
        and ("default_debug" not in data or _bool_value(data.get("default_debug"), False))
    ):
        sweep["debug_model"] = sanitized["default_debug_model"]

    if kind == "TIME":
        parameters = {
            "constant_value": sanitized["default_constant_value"],
            "until_stop": sanitized["default_constant_until_stop"],
            "duration_s": sanitized["default_duration_s"],
            "interval_s": sanitized["default_interval_s"],
        }
    elif kind == "ADAPTIVE":
        parameters = {
            "segments": sanitized["default_adaptive_segments"],
            "remove_duplicates": sanitized["default_adaptive_remove_duplicates"],
        }
    elif kind == "STEP":
        parameters = {
            "start": sanitized["default_start"],
            "stop": sanitized["default_stop"],
            "step": sanitized["default_step"],
        }
    else:
        parameters = {}
    sweep["parameters"] = parameters
    sweep["acquisition"] = default_acquisition_state()

    return {
        "schema_version": PRESET_SCHEMA_VERSION,
        "hardware": {
            "port": sanitized["default_port"],
            "baud_rate": sanitized["default_baud_rate"],
            "terminal": sanitized["default_terminal"],
            "sense_mode": sanitized["default_sense_mode"],
        },
        "sweep": sweep,
    }


def _clean_v2(data: dict[str, Any]) -> dict[str, Any]:
    raw_hardware = data.get("hardware")
    hardware: dict[str, Any] = raw_hardware if isinstance(raw_hardware, dict) else {}
    raw_sweep = data.get("sweep")
    sweep: dict[str, Any] = raw_sweep if isinstance(raw_sweep, dict) else {}
    raw_parameters = sweep.get("parameters")
    parameters: dict[str, Any] = raw_parameters if isinstance(raw_parameters, dict) else {}
    flat: dict[str, Any] = {
        "default_port": hardware.get("port"),
        "default_baud_rate": hardware.get("baud_rate"),
        "default_terminal": hardware.get("terminal"),
        "default_sense_mode": hardware.get("sense_mode"),
        "default_mode": sweep.get("mode"),
        "default_sweep_kind": sweep.get("kind"),
        "default_compliance": sweep.get("compliance"),
        "default_nplc": sweep.get("nplc"),
        "default_delay_s": sweep.get("delay_s"),
        "auto_source_range": sweep.get("auto_source_range"),
        "auto_measure_range": sweep.get("auto_measure_range"),
        "default_source_range": sweep.get("source_range"),
        "default_measure_range": sweep.get("measure_range"),
    }
    kind = str(sweep.get("kind", "")).upper()
    if kind == "STEP":
        flat.update(
            {
                "default_start": parameters.get("start"),
                "default_stop": parameters.get("stop"),
                "default_step": parameters.get("step"),
            }
        )
    elif kind == "TIME":
        flat.update(
            {
                "default_constant_value": parameters.get("constant_value"),
                "default_constant_until_stop": parameters.get("until_stop"),
                "default_duration_s": parameters.get("duration_s"),
                "default_interval_s": parameters.get("interval_s"),
            }
        )
    elif kind == "ADAPTIVE":
        flat.update(
            {
                "default_adaptive_segments": parameters.get("segments", ""),
                "default_adaptive_remove_duplicates": parameters.get("remove_duplicates"),
            }
        )
    if "debug_model" in sweep:
        flat["default_debug_model"] = sweep["debug_model"]

    flat = {key: value for key, value in flat.items() if value is not None}
    cleaned = _snapshot_from_flat(flat)
    cleaned["sweep"]["hysteresis"] = (
        _bool_value(sweep.get("hysteresis"), False)
        if cleaned["sweep"]["kind"] in {"STEP", "ADAPTIVE"}
        else False
    )
    return cleaned


def default_sweep_preset() -> dict[str, Any]:
    """Return the built-in Hardware + Sweep preset snapshot."""
    return _snapshot_from_flat(asdict(AppSettings()))


def _clean_v3(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize a v2/v3 snapshot, preserving validated acquisition state."""

    cleaned = _clean_v2(data)
    raw_sweep = data.get("sweep")
    raw_acquisition = raw_sweep.get("acquisition") if isinstance(raw_sweep, dict) else None
    cleaned["sweep"]["acquisition"] = clean_acquisition_state(raw_acquisition)
    return cleaned


def _clean(data: dict[str, Any]) -> dict[str, Any]:
    if isinstance(data, dict) and data.get("schema_version") in (2, PRESET_SCHEMA_VERSION):
        # v2 presets normalize forward; missing acquisition data means
        # historical Standard behavior, never inferred Fast.
        return _clean_v3(data)
    # Legacy flat presets convert directly; _snapshot_from_flat stamps the
    # current version with a Standard acquisition block.
    return _snapshot_from_flat(data)


def normalize_preset(data: dict[str, Any]) -> dict[str, Any]:
    """Return a validated v2 Hardware + Sweep snapshot."""
    return _clean(data)


def load_presets(path: str | Path = PRESETS_PATH) -> dict[str, dict[str, Any]]:
    path = Path(path)
    out: dict[str, dict[str, Any]] = {"Default": default_sweep_preset()}
    if not path.exists():
        return out
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return out
    if not isinstance(raw, dict):
        return out
    for name, data in raw.items():
        if isinstance(name, str) and isinstance(data, dict) and name.strip():
            out[name] = _clean(data)
    out["Default"] = default_sweep_preset()
    return out


def save_preset(
    name: str, settings: dict[str, Any] | AppSettings, path: str | Path = PRESETS_PATH
) -> Path:
    name = name.strip()
    if not name:
        raise ValueError("Preset name cannot be empty.")
    if name == "Default":
        raise ValueError("Default preset is built in and cannot be overwritten.")
    data = asdict(settings) if isinstance(settings, AppSettings) else dict(settings)
    path = Path(path)
    presets = load_presets(path)
    presets[name] = _clean(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {key: value for key, value in presets.items() if key != "Default"}
    path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
    return path


def delete_preset(name: str, path: str | Path = PRESETS_PATH) -> Path:
    if name == "Default":
        return Path(path)
    path = Path(path)
    presets = load_presets(path)
    presets.pop(name, None)
    path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {key: value for key, value in presets.items() if key != "Default"}
    path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
    return path
