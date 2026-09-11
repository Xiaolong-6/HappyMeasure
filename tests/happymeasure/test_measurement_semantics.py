from __future__ import annotations

import pytest

from keith_ivt.core.current_range import CurrentRangeControl, CurrentRangeState
from keith_ivt.drivers.base import (
    DriverCapabilities,
    instrument_model_from_idn,
    supports_fast_acquisition_for_idn,
)
from keith_ivt.models import SweepKind, SweepMode
from keith_ivt.ui.measurement_semantics import MeasurementSemanticsMixin


class _Var:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value) -> None:
        self.value = value


class _Combo:
    def __init__(self, value: str):
        self.value = value

    def get(self) -> str:
        return self.value


class _SemanticsBase:
    def start_sweep(self) -> None:
        self.started = True

    def _current_range_status_fragment(self) -> str:
        return "base"

    def _current_range_snapshot(self):
        return self._current_range_control.snapshot()

    def _refresh_front_panel_popup(self) -> None:
        pass

    def _current_source_measure_labels(self):
        if self.mode.get() == SweepMode.CURRENT_SOURCE.value:
            return "Isrc", "Vmeas", "V"
        return "Vsrc", "Imeas", "A"

    @staticmethod
    def _format_eng_value(value, unit: str) -> str:
        return f"{value} {unit}"

    def _refresh_front_panel_range_widgets(self) -> None:
        pass

    def _on_mode_changed(self, *_args) -> None:
        pass

    @staticmethod
    def _full_cap(name: str, vendor: str, family: str, *, fast_acquisition: bool = False):
        return DriverCapabilities(
            name=name,
            vendor=vendor,
            model_family=family,
            supports_fast_acquisition=fast_acquisition,
        )


class _SemanticsHarness(MeasurementSemanticsMixin, _SemanticsBase):
    def __init__(self) -> None:
        self.mode = _Var(SweepMode.VOLTAGE_SOURCE.value)
        self.sweep_kind = _Var(SweepKind.CONSTANT_TIME.value)
        self._live_config = None
        self._run_state = "idle"
        self._connected = True
        self.auto_measure_range = _Var(True)
        self.measure_range = _Var(1e-3)
        self.range_telemetry = _Var(False)
        self.acquisition_profile = _Var("Standard")
        self.compliance = _Var(1e-3)
        self.measurement_status_text = _Var("")
        self._last_source_value = 0.0
        self._last_measured_value = 0.0
        self._current_range_control = CurrentRangeControl(
            CurrentRangeState(autorange=True, actual_range_A=1e-6)
        )
        self._front_panel_range_combo = _Combo("10 uA (1e-05 A)")
        self.started = False


def test_range_actions_apply_only_during_active_run_and_voltage_measurement_is_guarded() -> None:
    app = _SemanticsHarness()

    app._front_panel_fixed_range_selected()
    assert app.measure_range.get() == pytest.approx(10e-6)
    assert app._current_range_control.drain_actions() == []

    app._run_state = "running"
    app._front_panel_fixed_range_selected()
    actions = app._current_range_control.drain_actions()
    assert len(actions) == 1 and actions[0].kind == "fixed_range"

    app.mode.set(SweepMode.CURRENT_SOURCE.value)
    app._live_config = None
    app.measure_range.set(5.0)
    app._front_panel_range_combo.value = "1 uA (1e-06 A)"
    app._front_panel_fixed_range_selected()
    assert app.measure_range.get() == pytest.approx(5.0)
    assert app._current_range_control.drain_actions() == []
    app._refresh_live_measurement_status()
    assert "Vrange N/A" in app.measurement_status_text.get()


def test_start_sweep_discards_stale_range_actions() -> None:
    app = _SemanticsHarness()
    app._current_range_control.request_fixed_range(1e-9)

    app.start_sweep()

    assert app.started is True
    assert app._current_range_control.drain_actions() == []


def test_effective_range_telemetry_follows_profile_and_sweep_kind() -> None:
    app = _SemanticsHarness()
    app.range_telemetry.set(False)

    app.acquisition_profile.set("Standard")
    assert app._effective_range_telemetry_enabled() is True
    app.acquisition_profile.set("Fast")
    assert app._effective_range_telemetry_enabled() is False
    app.acquisition_profile.set("Custom")
    assert app._effective_range_telemetry_enabled() is False
    app.range_telemetry.set(True)
    assert app._effective_range_telemetry_enabled() is True

    app.range_telemetry.set(False)
    app.acquisition_profile.set("Fast")
    for kind in (SweepKind.STEP, SweepKind.ADAPTIVE):
        app.sweep_kind.set(kind.value)
        assert app._effective_range_telemetry_enabled() is True


def test_keithley_model_detection_uses_model_field_not_serial_number_substrings() -> None:
    collision = "KEITHLEY INSTRUMENTS INC.,MODEL 2400,2401234,B02"
    validated = "KEITHLEY INSTRUMENTS INC.,MODEL 2401,24001234,B02"

    assert instrument_model_from_idn(collision) == "2400"
    assert supports_fast_acquisition_for_idn(collision) is False
    assert supports_fast_acquisition_for_idn(validated) is True

    app = _SemanticsHarness()
    assert app._detect_capabilities_from_idn(collision).supports_fast_acquisition is False
    assert app._detect_capabilities_from_idn(validated).supports_fast_acquisition is True
