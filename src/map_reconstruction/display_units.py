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


def display_unit_for_signal(signal_name: str, values: np.ndarray | None = None) -> DisplayUnit:
    """Choose an engineering display unit without changing scientific values."""

    if signal_name == "Current_A":
        return _engineering_unit(
            "Current", "A", values, ("A", 1.0), ("mA", 1e3), ("µA", 1e6), ("nA", 1e9), ("pA", 1e12)
        )
    if signal_name == "Voltage_V":
        return _engineering_unit("Voltage", "V", values, ("V", 1.0), ("mV", 1e3), ("µV", 1e6))
    return DisplayUnit(signal_name or "Signal", "")


def _engineering_unit(
    label: str,
    base_unit: str,
    values: np.ndarray | None,
    *candidates: tuple[str, float],
) -> DisplayUnit:
    if values is None:
        # µA is a useful compatibility default for current traces; volts remain volts.
        return DisplayUnit(label, "µA", 1e6) if base_unit == "A" else DisplayUnit(label, base_unit)
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    magnitude = float(np.max(np.abs(finite))) if finite.size else 0.0
    for unit, scale in candidates:
        if magnitude * scale >= 1.0 or unit == candidates[-1][0]:
            return DisplayUnit(label, unit, scale)
    return DisplayUnit(label, base_unit)


def to_display_values(values: np.ndarray, display_unit: DisplayUnit) -> np.ndarray:
    """Scale values for presentation only; callers retain scientific source arrays."""

    return np.asarray(values, dtype=float) * display_unit.scale


def format_display_value(value: float, display_unit: DisplayUnit) -> str:
    """Format one presentation value with the matching display unit."""

    suffix = f" {display_unit.unit}" if display_unit.unit else ""
    return f"{value * display_unit.scale:.6g}{suffix}"
