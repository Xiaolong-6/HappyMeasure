"""Display-only signal units for the optional map workspace."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class DisplayUnit:
    """One scientific signal's GUI scaling without changing stored SI values."""

    label: str
    unit: str
    scale: float = 1.0

    @property
    def axis_label(self) -> str:
        return f"{self.label} ({self.unit})" if self.unit else self.label


def display_unit_for_signal(signal_name: str) -> DisplayUnit:
    """Choose compact, explicit display units for standard HappyMeasure signals."""

    if signal_name == "Current_A":
        return DisplayUnit("Current", "µA", 1e6)
    if signal_name == "Voltage_V":
        return DisplayUnit("Voltage", "V")
    return DisplayUnit(signal_name or "Signal", "")


def to_display_values(values: np.ndarray, display_unit: DisplayUnit) -> np.ndarray:
    """Scale values for presentation only; callers retain scientific source arrays."""

    return np.asarray(values, dtype=float) * display_unit.scale


def format_display_value(value: float, display_unit: DisplayUnit) -> str:
    """Format one presentation value with the matching display unit."""

    suffix = f" {display_unit.unit}" if display_unit.unit else ""
    return f"{value * display_unit.scale:.6g}{suffix}"
