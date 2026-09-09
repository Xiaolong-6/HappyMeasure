from __future__ import annotations

import numpy as np

from map_reconstruction.display_units import (
    display_unit_for_signal,
    format_display_value,
    scientific_unit_for_signal,
    to_display_values,
)


def test_current_display_uses_microamps_without_changing_scientific_values() -> None:
    scientific = np.asarray([-103e-6, 0.0, 125e-6])
    display_unit = display_unit_for_signal("Current_A")

    displayed = to_display_values(scientific, display_unit)

    assert display_unit.axis_label == "Current (µA)"
    np.testing.assert_allclose(displayed, [-103.0, 0.0, 125.0])
    np.testing.assert_allclose(scientific, [-103e-6, 0.0, 125e-6])
    assert format_display_value(-103e-6, display_unit) == "-103 µA"


def test_voltage_and_unknown_signals_remain_in_native_display_units() -> None:
    assert display_unit_for_signal("Voltage_V").axis_label == "Voltage (V)"
    assert display_unit_for_signal("Auxiliary").axis_label == "Auxiliary"
    assert scientific_unit_for_signal("Current_A") == "A"
    assert scientific_unit_for_signal("Voltage_V") == "V"
    assert scientific_unit_for_signal("Auxiliary") == ""
