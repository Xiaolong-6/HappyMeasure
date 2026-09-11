from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from keith_ivt.core.current_range import CurrentRangeControl, CurrentRangeState
from keith_ivt.data.exporters import result_metadata, save_combined_csv
from keith_ivt.data.importers import load_csv
from keith_ivt.drivers.base import (
    DriverCapabilities,
    instrument_model_from_idn,
    supports_fast_acquisition_for_idn,
)
from keith_ivt.models import SweepConfig, SweepKind, SweepMode, SweepPoint, SweepResult
from keith_ivt.ui.app_mixins import AppChromeMixin
from keith_ivt.ui.measurement_semantics import MeasurementSemanticsMixin
from map_reconstruction.models import ScanPattern
from map_reconstruction.processing import MapProcessingConfig, ValueTransform, process_map
from map_reconstruction.project_io import ProjectState, load_project, save_project
from map_reconstruction.preparation import (
    DarkCorrectionMode,
    DarkRegion,
    SignalPreparationConfig,
)


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


def _time_result(name: str, *, interval_s: float, elapsed: list[float], warning: str | None = None):
    config = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0.0,
        stop=0.0,
        step=1.0,
        compliance=1e-3,
        nplc=0.1,
        delay_s=0.0,
        device_name=name,
        sweep_kind=SweepKind.CONSTANT_TIME,
        constant_value=0.0,
        duration_s=1.0,
        interval_s=interval_s,
        auto_source_range=False,
        auto_measure_range=False,
        source_range=20.0,
        measure_range=1e-3,
        fast_acquisition=True,
    )
    points = [
        SweepPoint(0.0, float(index + 1) * 1e-6, elapsed_s=value)
        for index, value in enumerate(elapsed)
    ]
    return SweepResult(config, points, warnings=[warning] if warning else [])


def _project_state(preparation: SignalPreparationConfig) -> ProjectState:
    return ProjectState(
        original_filename="measurement.csv",
        signal="Current_A",
        rows=2,
        columns=2,
        scan_pattern=ScanPattern.SAME_DIRECTION,
        first_row_ltr=True,
        aggregation="median",
        row_a_s=0.0,
        row_b_s=1.0,
        rows_apart=1,
        row_offset=0,
        point_a_s=0.0,
        point_b_s=0.1,
        points_apart=1,
        point_offset=0,
        preparation=preparation,
    )


def _raw_csv() -> bytes:
    return (
        b"# schema,single-v2\r\n"
        b"# section,data\r\n"
        b"Elapsed_s,Current_A,Voltage_V\r\n"
        b"0,1e-6,0.1\r\n"
        b"0.1,2e-6,0.1\r\n"
    )


def test_app_mro_wires_measurement_semantics_guard() -> None:
    assert issubclass(AppChromeMixin, MeasurementSemanticsMixin)


def test_range_actions_are_runtime_only_and_voltage_measure_is_guarded() -> None:
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


def test_effective_telemetry_follows_profile_not_hidden_raw_variable() -> None:
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


def test_non_time_sweeps_ignore_stale_fast_profile_for_range_telemetry() -> None:
    app = _SemanticsHarness()
    app.acquisition_profile.set("Fast")
    app.range_telemetry.set(False)

    for kind in (SweepKind.STEP, SweepKind.ADAPTIVE):
        app.sweep_kind.set(kind.value)
        assert app._effective_range_telemetry_enabled() is True


def test_keithley_model_parser_does_not_match_serial_number_substrings() -> None:
    collision = "KEITHLEY INSTRUMENTS INC.,MODEL 2400,2401234,B02"
    assert instrument_model_from_idn(collision) == "2400"
    assert supports_fast_acquisition_for_idn(collision) is False
    assert supports_fast_acquisition_for_idn(
        "KEITHLEY INSTRUMENTS INC.,MODEL 2401,24001234,B02"
    ) is True

    app = _SemanticsHarness()
    assert app._detect_capabilities_from_idn(collision).supports_fast_acquisition is False
    assert (
        app._detect_capabilities_from_idn(
            "KEITHLEY INSTRUMENTS INC.,MODEL 2401,24001234,B02"
        ).supports_fast_acquisition
        is True
    )


def test_fast_metadata_separates_configured_interval_from_execution_policy() -> None:
    a = _time_result("same", interval_s=0.1, elapsed=[0.01, 0.02])
    b = _time_result("same", interval_s=0.5, elapsed=[0.01, 0.02])
    ma = result_metadata(a)
    mb = result_metadata(b)

    assert ma["interval_s"] == pytest.approx(0.1)
    assert mb["interval_s"] == pytest.approx(0.5)
    assert ma["configured_interval_s"] == pytest.approx(0.1)
    assert mb["configured_interval_s"] == pytest.approx(0.5)
    assert ma["sampling_policy"] == mb["sampling_policy"] == "as_fast_as_possible"
    assert ma["effective_interval_s"] is None
    assert mb["effective_interval_s"] is None
    assert ma["effective_nplc"] == mb["effective_nplc"] == pytest.approx(0.1)
    assert ma["effective_software_delay_s"] == mb["effective_software_delay_s"] == 0.0
    assert ma["config_fingerprint"] == mb["config_fingerprint"]


def test_combined_csv_uses_long_format_for_different_elapsed_and_keeps_warnings(
    tmp_path: Path,
) -> None:
    a = _time_result("a", interval_s=0.1, elapsed=[0.01, 0.10], warning="warning a")
    b = _time_result("b", interval_s=0.1, elapsed=[0.02, 0.11], warning="warning b")
    path = save_combined_csv([a, b], tmp_path / "different_elapsed.csv")

    text = path.read_text(encoding="utf-8")
    assert "# format,long-v2" in text.replace("\r", "")
    loaded = {result.config.device_name: result for result in load_csv(path)}
    assert [point.elapsed_s for point in loaded["a"].points] == [0.01, 0.10]
    assert [point.elapsed_s for point in loaded["b"].points] == [0.02, 0.11]
    assert loaded["a"].warnings == ["warning a"]
    assert loaded["b"].warnings == ["warning b"]


@pytest.mark.parametrize(
    "preparation",
    [
        SignalPreparationConfig(
            dark_correction_mode=DarkCorrectionMode.MANUAL_REGIONS,
            manual_dark_regions=(DarkRegion(0.0, 0.1),),
            apply_baseline=False,
        ),
        SignalPreparationConfig(
            dark_correction_mode=DarkCorrectionMode.ROLLING_QUANTILE,
            apply_baseline=False,
        ),
    ],
)
def test_nondefault_preparation_round_trips_even_when_baseline_is_not_applied(
    tmp_path: Path, preparation: SignalPreparationConfig
) -> None:
    path = tmp_path / "configured_preparation.hmmap"
    state = _project_state(preparation)
    save_project(path, state, _raw_csv())
    loaded = load_project(path)

    assert loaded.project_metadata["schema"] == "map-reconstruction-project-v3"
    assert loaded.state.preparation == preparation


def test_custom_map_processing_converts_generated_inf_to_nan_with_warning() -> None:
    with np.errstate(divide="ignore", invalid="ignore"):
        processed = process_map(
            np.asarray([[0.0, 2.0]]),
            MapProcessingConfig(transform=ValueTransform.CUSTOM, custom_expression="1 / x"),
        )

    assert np.isnan(processed.values[0, 0])
    assert processed.values[0, 1] == pytest.approx(0.5)
    assert any("non-finite" in warning for warning in processed.warnings)
