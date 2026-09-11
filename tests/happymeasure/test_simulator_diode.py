from __future__ import annotations

from keith_ivt.instrument.simulator import SimulatedKeithley
from keith_ivt.models import SweepConfig, SweepMode


def test_current_source_diode_numeric_inverse_roundtrip() -> None:
    simulator = SimulatedKeithley(model_name="Diode-like nonlinear")
    for voltage in (-0.2, 0.0, 0.2, 0.45, 0.65):
        current = simulator._current_from_voltage(voltage)
        recovered = simulator._voltage_from_current(current)
        assert abs(recovered - voltage) < 1e-3


def test_current_source_diode_reports_actual_current_when_compliance_limited() -> None:
    simulator = SimulatedKeithley(model_name="Diode-like nonlinear")
    simulator.noise_fraction = 0.0
    simulator.configure_for_sweep(
        SweepConfig(
            mode=SweepMode.CURRENT_SOURCE,
            start=-1e-3,
            stop=1e-3,
            step=1e-3,
            compliance=10.0,
        )
    )

    simulator.set_source("CURR", -1e-3)
    actual_current, measured_voltage = simulator.read_source_and_measure()
    assert measured_voltage <= -9.9
    assert abs(actual_current) < 2e-5
    assert abs(actual_current - simulator._current_from_voltage(measured_voltage)) < 1e-12

    simulator.set_source("CURR", 1e-3)
    actual_current, measured_voltage = simulator.read_source_and_measure()
    assert 0.7 < measured_voltage < 0.85
    assert abs(actual_current - 1e-3) < 1e-6
