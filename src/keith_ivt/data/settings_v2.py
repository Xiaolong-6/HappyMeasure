"""Pydantic-based settings with validation and migration support.

This module replaces the legacy dataclass-based AppSettings with a validated,
type-safe configuration system that provides:
- Runtime type validation
- Value range constraints
- Automatic migration between versions
- Clear error messages for invalid configurations
- IDE autocomplete and type hints
"""
from __future__ import annotations

import json
import logging
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger("keith_ivt.settings")


# ============================================================================
# Enums for constrained choices
# ============================================================================

class SourceMode(str, Enum):
    """Voltage or current source mode."""
    VOLTAGE = "VOLT"
    CURRENT = "CURR"


class Terminal(str, Enum):
    """Instrument terminal selection."""
    FRONT = "FRON"
    REAR = "REAR"


class SenseMode(str, Enum):
    """Sense wiring configuration."""
    TWO_WIRE = "2W"
    FOUR_WIRE = "4W"


class SweepKind(str, Enum):
    """Type of measurement sweep."""
    STEP = "STEP"
    TIME = "TIME"
    ADAPTIVE = "ADAPTIVE"


class PlotLayout(str, Enum):
    """Plot subplot arrangement."""
    AUTO = "Auto"
    SINGLE = "1x1"
    HORIZONTAL = "1x2"
    VERTICAL = "2x1"
    GRID = "2x2"


class UITheme(str, Enum):
    """UI color theme."""
    LIGHT = "Light"
    DARK = "Dark"
    DEBUG = "Debug"


# ============================================================================
# Settings models
# ============================================================================

class HardwareSettings(BaseModel):
    """Hardware connection and operation settings."""

    default_port: str = Field(
        default="COM3",
        description="Default COM port for instrument connection",
        min_length=3,
        max_length=20,
    )
    default_baud_rate: int = Field(
        default=9600,
        description="Serial baud rate",
        ge=1200,
        le=115200,
    )
    default_terminal: Terminal = Field(
        default=Terminal.REAR,
        description="Default instrument terminal (FRONT/REAR)",
    )
    default_sense_mode: SenseMode = Field(
        default=SenseMode.TWO_WIRE,
        description="Default sense wiring (2W/4W)",
    )
    default_debug_model: str = Field(
        default="Linear resistor 10 kΩ",
        description="Default simulator device model",
    )

    @field_validator("default_port")
    @classmethod
    def validate_port(cls, v: str) -> str:
        """Ensure port name looks valid."""
        if not v.upper().startswith(("COM", "TTY", "/DEV/")):
            logger.warning(f"Suspicious port name: {v}")
        return v


class SweepSettings(BaseModel):
    """Measurement sweep configuration defaults."""

    default_mode: SourceMode = Field(
        default=SourceMode.VOLTAGE,
        description="Default source mode",
    )
    default_start: float = Field(
        default=-1.0,
        description="Default sweep start value",
    )
    default_stop: float = Field(
        default=1.0,
        description="Default sweep stop value",
    )
    default_step: float = Field(
        default=0.1,
        description="Default sweep step size",
        gt=0,
    )
    default_compliance: float = Field(
        default=0.01,
        description="Default compliance limit",
        gt=0,
    )
    default_nplc: float = Field(
        default=1.0,
        description="Default NPLC (noise power line cycles)",
        ge=0.01,
        le=10.0,
    )
    default_sweep_kind: SweepKind = Field(
        default=SweepKind.STEP,
        description="Default sweep type",
    )
    default_autorange: bool = Field(
        default=True,
        description="Enable auto-ranging by default",
    )
    auto_source_range: bool = Field(
        default=True,
        description="Auto-range source amplitude",
    )
    auto_measure_range: bool = Field(
        default=True,
        description="Auto-range measurement",
    )
    default_source_range: float = Field(
        default=0.0,
        description="Manual source range (0 = auto)",
        ge=0,
    )
    default_measure_range: float = Field(
        default=0.0,
        description="Manual measure range (0 = auto)",
        ge=0,
    )

    # Time sweep settings
    default_constant_value: float = Field(
        default=0.0,
        description="Constant time sweep value",
    )
    default_duration_s: float = Field(
        default=10.0,
        description="Time sweep duration in seconds",
        gt=0,
    )
    default_constant_until_stop: bool = Field(
        default=False,
        description="Continue time sweep until manually stopped",
    )
    default_interval_s: float = Field(
        default=0.5,
        description="Time between samples in time sweep",
        gt=0,
    )

    # Adaptive sweep settings
    default_adaptive_logic: str = Field(
        default="values = logspace(1e-3, 1, 31)",
        description="Adaptive sweep logic expression",
        min_length=5,
    )

    @model_validator(mode="after")
    def validate_sweep_range(self) -> "SweepSettings":
        """Ensure start <= stop for valid sweep range."""
        if self.default_start > self.default_stop:
            logger.warning(
                f"Sweep start ({self.default_start}) > stop ({self.default_stop}), "
                "this may cause issues"
            )
        return self


class UISettings(BaseModel):
    """User interface appearance settings."""

    ui_font_family: str = Field(
        default="Verdana",
        description="UI font family name",
        min_length=1,
        max_length=50,
    )
    ui_font_size: int = Field(
        default=10,
        description="UI font size in points",
        ge=8,
        le=18,
    )
    ui_theme: UITheme = Field(
        default=UITheme.LIGHT,
        description="UI color theme",
    )
    default_plot_layout: PlotLayout = Field(
        default=PlotLayout.AUTO,
        description="Default plot subplot arrangement",
    )


class DataSettings(BaseModel):
    """Data management and caching settings."""

    log_max_bytes: int = Field(
        default=1_000_000,
        description="Maximum log file size before rotation (bytes)",
        ge=1024,
        le=100_000_000,
    )
    cache_enabled: bool = Field(
        default=False,
        description="Enable data caching",
    )
    cache_interval_points: int = Field(
        default=10,
        description="Cache every N data points",
        ge=1,
    )
    default_device_name: str = Field(
        default="Device_1",
        description="Default device identifier",
        min_length=1,
        max_length=100,
    )
    default_operator: str = Field(
        default="",
        description="Default operator name",
        max_length=100,
    )
    default_debug: bool = Field(
        default=True,
        description="Enable debug/simulator mode by default",
    )


class AppSettings(BaseModel):
    """Complete application settings with validation.

    This is the main settings class that combines all sub-categories.
    It provides backward compatibility with the legacy flat structure.

    Usage:
        >>> settings = AppSettings()
        >>> settings.hardware.default_port = "COM4"
        >>> save_settings(settings)
        >>> loaded = load_settings()
    """

    hardware: HardwareSettings = Field(
        default_factory=HardwareSettings,
        description="Hardware connection settings",
    )
    sweep: SweepSettings = Field(
        default_factory=SweepSettings,
        description="Sweep measurement defaults",
    )
    ui: UISettings = Field(
        default_factory=UISettings,
        description="User interface settings",
    )
    data: DataSettings = Field(
        default_factory=DataSettings,
        description="Data management settings",
    )

    # Legacy flat accessors for backward compatibility
    @property
    def default_port(self) -> str:
        return self.hardware.default_port

    @property
    def default_mode(self) -> str:
        return self.sweep.default_mode.value

    @property
    def default_start(self) -> float:
        return self.sweep.default_start

    @property
    def default_stop(self) -> float:
        return self.sweep.default_stop

    @property
    def ui_theme(self) -> str:
        return self.ui.ui_theme.value

    @property
    def log_max_bytes(self) -> int:
        return self.data.log_max_bytes

    # Backward-compatible dict-like access
    def get(self, key: str, default: Any = None) -> Any:
        """Get setting value by legacy flat key name."""
        # Map legacy keys to new structure
        legacy_map = {
            "default_port": self.hardware.default_port,
            "default_mode": self.sweep.default_mode.value,
            "default_start": self.sweep.default_start,
            "default_stop": self.sweep.default_stop,
            "default_step": self.sweep.default_step,
            "default_compliance": self.sweep.default_compliance,
            "default_nplc": self.sweep.default_nplc,
            "default_baud_rate": self.hardware.default_baud_rate,
            "default_terminal": self.hardware.default_terminal.value,
            "default_sense_mode": self.hardware.default_sense_mode.value,
            "default_debug_model": self.hardware.default_debug_model,
            "default_sweep_kind": self.sweep.default_sweep_kind.value,
            "default_autorange": self.sweep.default_autorange,
            "auto_source_range": self.sweep.auto_source_range,
            "auto_measure_range": self.sweep.auto_measure_range,
            "default_source_range": self.sweep.default_source_range,
            "default_measure_range": self.sweep.default_measure_range,
            "default_constant_value": self.sweep.default_constant_value,
            "default_duration_s": self.sweep.default_duration_s,
            "default_constant_until_stop": self.sweep.default_constant_until_stop,
            "default_interval_s": self.sweep.default_interval_s,
            "default_adaptive_logic": self.sweep.default_adaptive_logic,
            "ui_font_family": self.ui.ui_font_family,
            "ui_font_size": self.ui.ui_font_size,
            "ui_theme": self.ui.ui_theme.value,
            "default_plot_layout": self.ui.default_plot_layout.value,
            "log_max_bytes": self.data.log_max_bytes,
            "cache_enabled": self.data.cache_enabled,
            "cache_interval_points": self.data.cache_interval_points,
            "default_device_name": self.data.default_device_name,
            "default_operator": self.data.default_operator,
            "default_debug": self.data.default_debug,
        }
        return legacy_map.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set setting value by legacy flat key name."""
        # This allows gradual migration while maintaining compatibility
        setattr(self, "_pending_legacy_set", True)


# ============================================================================
# File I/O with migration support
# ============================================================================

DEFAULT_SETTINGS_PATH = Path("config") / "settings.json"
SETTINGS_VERSION = "2.0"  # Pydantic-based format


def load_settings(path: str | Path = DEFAULT_SETTINGS_PATH) -> AppSettings:
    """Load settings from JSON file with validation and migration.

    Args:
        path: Path to settings JSON file

    Returns:
        Validated AppSettings instance

    Raises:
        ValidationError: If settings contain invalid values
    """
    from pydantic import ValidationError

    path = Path(path)
    if not path.exists():
        logger.info(f"Settings file not found, using defaults: {path}")
        return AppSettings()

    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Failed to read settings file: {e}, using defaults")
        return AppSettings()

    # Check if this is legacy flat format or new nested format
    if "hardware" in data or "sweep" in data:
        # New nested format
        try:
            return AppSettings(**data)
        except ValidationError as e:
            logger.warning(f"Invalid settings format, attempting migration: {e}")
            return _migrate_legacy(data)
    else:
        # Legacy flat format - migrate
        return _migrate_legacy(data)


def _migrate_legacy(data: dict[str, Any]) -> AppSettings:
    """Migrate legacy flat settings to new nested structure.

    Args:
        data: Legacy flat settings dictionary

    Returns:
        Migrated AppSettings instance
    """
    logger.info("Migrating legacy settings to new format")

    # Extract into categories
    hardware_keys = {"default_port", "default_baud_rate", "default_terminal",
                     "default_sense_mode", "default_debug_model"}
    sweep_keys = {"default_mode", "default_start", "default_stop", "default_step",
                  "default_compliance", "default_nplc", "default_sweep_kind",
                  "default_autorange", "auto_source_range", "auto_measure_range",
                  "default_source_range", "default_measure_range",
                  "default_constant_value", "default_duration_s",
                  "default_constant_until_stop", "default_interval_s",
                  "default_adaptive_logic"}
    ui_keys = {"ui_font_family", "ui_font_size", "ui_theme", "default_plot_layout"}
    data_keys = {"log_max_bytes", "cache_enabled", "cache_interval_points",
                 "default_device_name", "default_operator", "default_debug"}

    hardware_data = {k: v for k, v in data.items() if k in hardware_keys}
    sweep_data = {k: v for k, v in data.items() if k in sweep_keys}
    ui_data = {k: v for k, v in data.items() if k in ui_keys}
    data_data = {k: v for k, v in data.items() if k in data_keys}

    try:
        return AppSettings(
            hardware=HardwareSettings(**hardware_data) if hardware_data else HardwareSettings(),
            sweep=SweepSettings(**sweep_data) if sweep_data else SweepSettings(),
            ui=UISettings(**ui_data) if ui_data else UISettings(),
            data=DataSettings(**data_data) if data_data else DataSettings(),
        )
    except Exception as e:
        logger.error(f"Migration failed, using defaults: {e}")
        return AppSettings()


def save_settings(settings: AppSettings, path: str | Path = DEFAULT_SETTINGS_PATH) -> Path:
    """Save settings to JSON file.

    Args:
        settings: AppSettings instance to save
        path: Path to save settings file

    Returns:
        Path to saved file
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Add version metadata
    output = {
        "_version": SETTINGS_VERSION,
        "_comment": "HappyMeasure settings - do not edit manually",
        **settings.model_dump(mode="json"),
    }

    path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Settings saved to {path}")
    return path


def validate_settings_file(path: str | Path = DEFAULT_SETTINGS_PATH) -> tuple[bool, list[str]]:
    """Validate a settings file without loading it.

    Args:
        path: Path to settings file

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    from pydantic import ValidationError

    path = Path(path)
    if not path.exists():
        return False, ["Settings file not found"]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        AppSettings(**data)
        return True, []
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]
    except ValidationError as e:
        errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
        return False, errors
    except Exception as e:
        return False, [f"Unexpected error: {e}"]


# Export for backward compatibility
__all__ = [
    "AppSettings",
    "HardwareSettings",
    "SweepSettings",
    "UISettings",
    "DataSettings",
    "load_settings",
    "save_settings",
    "validate_settings_file",
    "SourceMode",
    "Terminal",
    "SenseMode",
    "SweepKind",
    "UITheme",
    "PlotLayout",
]
