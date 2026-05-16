from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class AppSettings:
    """User-editable alpha settings persisted as JSON.

    The file is intentionally small and stable so future agents can extend it
    without needing a migration framework during the offline alpha phase.
    """

    log_max_bytes: int = 1_000_000
    default_mode: str = "VOLT"
    default_start: float = -1.0
    default_stop: float = 1.0
    default_step: float = 0.1
    default_compliance: float = 0.01
    default_nplc: float = 1.0
    default_port: str = "COM3"
    default_baud_rate: int = 9600
    default_terminal: str = "REAR"
    default_sense_mode: str = "2W"
    default_debug: bool = True
    default_debug_model: str = "Linear resistor 10 kΩ"
    default_device_name: str = "Device_1"
    default_operator: str = ""
    default_plot_layout: str = "Auto"
    cache_enabled: bool = False
    cache_interval_points: int = 10
    default_autorange: bool = True
    auto_source_range: bool = True
    auto_measure_range: bool = True
    default_source_range: float = 0.0
    default_measure_range: float = 0.0
    default_sweep_kind: str = "STEP"
    default_constant_value: float = 0.0
    default_duration_s: float = 10.0
    default_constant_until_stop: bool = False
    default_interval_s: float = 0.5
    default_adaptive_logic: str = "values = logspace(1e-3, 1, 31)"
    ui_font_family: str = "Verdana"
    ui_font_size: int = 10
    ui_theme: str = "Light"


DEFAULT_SETTINGS_PATH = Path("config") / "settings.json"

_TRUE_STRINGS = {"1", "true", "yes", "y", "on"}
_FALSE_STRINGS = {"0", "false", "no", "n", "off", ""}


def clamp_log_max_bytes(value: int) -> int:
    """Keep the log rotation limit in a practical range."""
    return max(1_024, min(int(value), 100_000_000))


def _coerce_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in _TRUE_STRINGS:
            return True
        if lowered in _FALSE_STRINGS:
            return False
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def _coerce_int(value: Any, default: int, *, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        coerced = int(value)
    except (TypeError, ValueError, OverflowError):
        coerced = int(default)
    if minimum is not None:
        coerced = max(minimum, coerced)
    if maximum is not None:
        coerced = min(maximum, coerced)
    return coerced


def _coerce_float(value: Any, default: float, *, minimum: float | None = None) -> float:
    try:
        coerced = float(value)
    except (TypeError, ValueError, OverflowError):
        coerced = float(default)
    if minimum is not None:
        coerced = max(minimum, coerced)
    return coerced


def _coerce_choice(value: Any, default: str, allowed: set[str], *, aliases: dict[str, str] | None = None) -> str:
    text = str(value).strip() if value is not None else ""
    upper = text.upper()
    if aliases and upper in aliases:
        return aliases[upper]
    for allowed_value in allowed:
        if upper == allowed_value.upper():
            return allowed_value
    return default


def _normalize_theme(value: Any) -> str:
    theme = str(value).strip() if value is not None else "Light"
    aliases = {
        "Nordic Light": "Light",
        "Nordic Dark": "Dark",
        "High contrast": "Debug",
        "High Contrast": "Debug",
    }
    theme = aliases.get(theme, theme)
    return theme if theme in {"Light", "Dark", "Debug"} else "Light"


def sanitize_settings_dict(data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a backward-compatible, type-safe flat settings dictionary.

    Legacy alpha settings were intentionally stored as a simple flat JSON file.
    User-edited or older files can therefore contain missing keys, unknown keys,
    strings for booleans, or invalid numeric values. This sanitizer preserves
    known values when they can be interpreted safely and falls back to defaults
    instead of crashing the UI during startup.
    """
    defaults = asdict(AppSettings())
    raw = data if isinstance(data, dict) else {}
    merged = {**defaults, **{k: v for k, v in raw.items() if k in defaults}}

    merged["log_max_bytes"] = clamp_log_max_bytes(
        _coerce_int(merged.get("log_max_bytes"), defaults["log_max_bytes"])
    )
    merged["default_baud_rate"] = _coerce_int(
        merged.get("default_baud_rate"), defaults["default_baud_rate"], minimum=1200, maximum=115200
    )
    merged["cache_interval_points"] = _coerce_int(
        merged.get("cache_interval_points"), defaults["cache_interval_points"], minimum=1
    )
    merged["ui_font_size"] = _coerce_int(
        merged.get("ui_font_size"), defaults["ui_font_size"], minimum=8, maximum=18
    )

    for key in (
        "default_start",
        "default_stop",
        "default_step",
        "default_compliance",
        "default_nplc",
        "default_source_range",
        "default_measure_range",
        "default_constant_value",
        "default_duration_s",
        "default_interval_s",
    ):
        minimum = 0.0 if key in {"default_step", "default_compliance", "default_nplc", "default_duration_s", "default_interval_s"} else None
        merged[key] = _coerce_float(merged.get(key), defaults[key], minimum=minimum)

    for key in (
        "cache_enabled",
        "default_autorange",
        "auto_source_range",
        "auto_measure_range",
        "default_constant_until_stop",
        "default_debug",
    ):
        merged[key] = _coerce_bool(merged.get(key), defaults[key])

    merged["default_mode"] = _coerce_choice(merged.get("default_mode"), defaults["default_mode"], {"VOLT", "CURR"})
    merged["default_terminal"] = _coerce_choice(
        merged.get("default_terminal"), defaults["default_terminal"], {"FRON", "REAR"}, aliases={"FRONT": "FRON"}
    )
    merged["default_sense_mode"] = _coerce_choice(merged.get("default_sense_mode"), defaults["default_sense_mode"], {"2W", "4W"})
    merged["default_sweep_kind"] = _coerce_choice(
        merged.get("default_sweep_kind"), defaults["default_sweep_kind"], {"STEP", "TIME", "ADAPTIVE"}
    )
    merged["default_plot_layout"] = _coerce_choice(
        merged.get("default_plot_layout"), defaults["default_plot_layout"], {"Auto", "1x1", "1x2", "2x1", "2x2"}
    )
    merged["ui_theme"] = _normalize_theme(merged.get("ui_theme"))

    for key in (
        "default_port",
        "default_debug_model",
        "default_device_name",
        "default_operator",
        "default_adaptive_logic",
        "ui_font_family",
    ):
        merged[key] = str(merged.get(key, defaults[key]))

    if not merged["default_device_name"].strip():
        merged["default_device_name"] = defaults["default_device_name"]
    if not merged["ui_font_family"].strip():
        merged["ui_font_family"] = defaults["ui_font_family"]
    if not merged["default_adaptive_logic"].strip():
        merged["default_adaptive_logic"] = defaults["default_adaptive_logic"]

    return merged


def load_settings(path: str | Path = DEFAULT_SETTINGS_PATH) -> AppSettings:
    path = Path(path)
    if not path.exists():
        return AppSettings()
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return AppSettings()
    if not isinstance(loaded, dict):
        return AppSettings()
    return AppSettings(**sanitize_settings_dict(loaded))


def save_settings(settings: AppSettings, path: str | Path = DEFAULT_SETTINGS_PATH) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = sanitize_settings_dict(asdict(settings))
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
