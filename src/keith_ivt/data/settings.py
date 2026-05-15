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


def clamp_log_max_bytes(value: int) -> int:
    """Keep the log rotation limit in a practical range."""
    return max(1_024, min(int(value), 100_000_000))


def load_settings(path: str | Path = DEFAULT_SETTINGS_PATH) -> AppSettings:
    path = Path(path)
    if not path.exists():
        return AppSettings()
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return AppSettings()
    defaults = asdict(AppSettings())
    merged = {**defaults, **{k: v for k, v in data.items() if k in defaults}}
    merged["log_max_bytes"] = clamp_log_max_bytes(int(merged["log_max_bytes"]))
    merged["cache_interval_points"] = max(1, int(merged.get("cache_interval_points", 10)))
    merged["cache_enabled"] = bool(merged.get("cache_enabled", False))
    merged["default_autorange"] = bool(merged.get("default_autorange", True))
    merged["auto_source_range"] = bool(merged.get("auto_source_range", merged["default_autorange"]))
    merged["auto_measure_range"] = bool(merged.get("auto_measure_range", merged["default_autorange"]))
    merged["default_debug_model"] = str(merged.get("default_debug_model", "Linear resistor 10 kΩ"))
    merged["default_source_range"] = float(merged.get("default_source_range", 0.0))
    merged["default_measure_range"] = float(merged.get("default_measure_range", 0.0))
    merged["default_constant_until_stop"] = bool(merged.get("default_constant_until_stop", False))
    merged["ui_font_family"] = str(merged.get("ui_font_family", "Verdana"))
    merged["ui_font_size"] = max(8, min(int(merged.get("ui_font_size", 10)), 18))
    theme = str(merged.get("ui_theme", "Light"))
    if theme in {"Nordic Light"}:
        theme = "Light"
    elif theme in {"High contrast", "High Contrast"}:
        theme = "Debug"
    elif theme == "Nordic Dark":
        theme = "Dark"
    if theme not in {"Light", "Dark", "Debug"}:
        theme = "Light"
    merged["ui_theme"] = theme
    return AppSettings(**merged)


def save_settings(settings: AppSettings, path: str | Path = DEFAULT_SETTINGS_PATH) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    settings.log_max_bytes = clamp_log_max_bytes(settings.log_max_bytes)
    path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
    return path
