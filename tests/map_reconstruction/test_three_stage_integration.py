from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from map_reconstruction.models import ScanPattern, TimeSeriesData
from map_reconstruction.processing import MapProcessingConfig, ProcessedMap
from map_reconstruction.project_io import ProjectState, save_project
from map_reconstruction.preparation import (
    DarkCorrectionMode,
    PhotocurrentPolarity,
    SignalPreparationConfig,
    prepare_signal,
)


def _data() -> TimeSeriesData:
    time = np.linspace(5.0, 15.0, 101)
    current = 2e-9 + 0.2e-9 * np.sin(time)
    return TimeSeriesData(time, {"Current_A": current})


def _raw_csv() -> bytes:
    return (
        b"# schema,single-v2\n"
        b"# section,data\n"
        b"Elapsed_s,Current_A\n"
        b"5.0,2e-9\n"
        b"10.0,1e-9\n"
        b"15.0,2e-9\n"
    )


def test_rolling_response_direction_selects_opposite_dark_envelopes() -> None:
    data = TimeSeriesData(
        np.asarray([0.0, 1.0, 2.0, 3.0]),
        {"Current_A": np.asarray([-10.0, -9.0, -8.0, -7.0])},
    )
    negative = prepare_signal(
        data,
        "Current_A",
        SignalPreparationConfig(
            dark_correction_mode=DarkCorrectionMode.ROLLING_QUANTILE,
            rolling_window_s=10.0,
            rolling_quantile=0.9,
            response_direction=PhotocurrentPolarity.NEGATIVE,
        ),
    )
    positive = prepare_signal(
        data,
        "Current_A",
        SignalPreparationConfig(
            dark_correction_mode=DarkCorrectionMode.ROLLING_QUANTILE,
            rolling_window_s=10.0,
            rolling_quantile=0.9,
            response_direction=PhotocurrentPolarity.POSITIVE,
        ),
    )

    assert negative.baseline is not None
    assert positive.baseline is not None
    assert negative.baseline[0] > positive.baseline[0]
    assert negative.metadata["effective_dark_quantile"] == pytest.approx(0.9)
    assert positive.metadata["effective_dark_quantile"] == pytest.approx(0.1)


def test_literal_historical_v1_and_v2_states_restore_identity_preparation() -> None:
    processing = {
        "baseline_mode": "none",
        "baseline_value": None,
        "baseline_percentile": 50.0,
        "transform": "raw",
        "custom_expression": "x",
        "normalization": "none",
        "normalization_reference": None,
        "value_scale": "linear",
        "color_range_mode": "auto",
        "color_min": None,
        "color_max": None,
        "percentile_low": 1.0,
        "percentile_high": 99.0,
    }
    common = {
        "source": {"original_filename": "historical.csv", "signal": "Current_A"},
        "geometry": {
            "rows": 0,
            "columns": 0,
            "scan_pattern": "serpentine",
            "first_row_ltr": True,
            "aggregation": "median",
        },
        "processing": processing,
        "display": {"flip_y": False},
    }
    v1 = {
        **common,
        "schema": "map-reconstruction-project-v1",
        "registration": {
            "method": "dual_offset",
            "row_a_s": 0.0,
            "row_b_s": 1.0,
            "rows_apart": 1,
            "row_offset": 0,
            "point_a_s": 0.0,
            "point_b_s": 0.1,
            "points_apart": 1,
            "point_offset": 0,
        },
    }
    v2 = {
        **common,
        "schema": "map-reconstruction-project-v2",
        "registration": {
            "method": "dual_offset_phase_window",
            "row_a_s": 0.0,
            "row_b_s": 1.0,
            "rows_apart": 1,
            "row_offset": 0,
            "point_a_s": 0.0,
            "point_b_s": 0.1,
            "points_apart": 1,
            "y_phase_fraction": 0.0,
            "x_period_offset": 0,
            "x_phase_fraction": 0.0,
            "window_mode": "fraction",
            "window_fraction": 0.65,
            "window_duration_s": None,
        },
    }

    assert ProjectState.from_project_dict(v1).preparation.is_identity
    assert ProjectState.from_project_dict(v2).preparation.is_identity


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")
from PySide6 import QtWidgets  # noqa: E402

from map_reconstruction.display_units import DisplayUnit  # noqa: E402
from map_reconstruction.ui.main_window import MapReconstructionWindow  # noqa: E402
from map_reconstruction.ui.preparation_page import SignalPreparationPage  # noqa: E402


@pytest.fixture(scope="module")
def application():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_manual_region_has_bounded_drag_and_numeric_edit_path(application) -> None:
    page = SignalPreparationPage()
    data = _data()
    page.set_display_unit(DisplayUnit("Current", "nA", 1e9))
    page.set_source(data.time_s, data.signals["Current_A"])
    page.mode_combo.setCurrentIndex(page.mode_combo.findData(DarkCorrectionMode.MANUAL_REGIONS))
    page._add_region()

    assert len(page.configuration().manual_dark_regions) == 1
    region = page.configuration().manual_dark_regions[0]
    assert data.time_s[0] <= region.start_s < region.end_s <= data.time_s[-1]
    assert page.region_start_spin.isEnabled()
    page.region_start_spin.setValue(6.0)
    page.region_end_spin.setValue(7.0)
    page._region_editor_finished()
    edited = page.configuration().manual_dark_regions[0]
    assert edited.start_s == pytest.approx(6.0)
    assert edited.end_s == pytest.approx(7.0)
    assert page.constant_baseline_spin.suffix().strip() == "nA"
    page.close()


def test_invalid_preparation_cannot_be_revived_by_geometry_change(application) -> None:
    window = MapReconstructionWindow()
    data = _data()
    window._load_data(data, b"loaded-source", "measurement.csv", reconstruct=False)
    window.preparation_page.mode_combo.setCurrentIndex(
        window.preparation_page.mode_combo.findData(DarkCorrectionMode.MANUAL_REGIONS)
    )

    assert window.prepared is None
    assert window.preparation_config.dark_correction_mode is DarkCorrectionMode.MANUAL_REGIONS
    window.rows_spin.setValue(2)
    window.cols_spin.setValue(2)

    assert window.prepared is None
    assert window.result is None
    assert "requires at least 1 valid regions" in window.statusBar().currentMessage()
    window.close()


def test_invalid_gate_does_not_fall_back_to_previous_valid_preparation(application) -> None:
    window = MapReconstructionWindow()
    data = _data()
    window._load_data(data, b"loaded-source", "measurement.csv", reconstruct=False)
    page = window.preparation_page
    page.mode_combo.setCurrentIndex(page.mode_combo.findData(DarkCorrectionMode.ROLLING_QUANTILE))
    assert window.prepared is not None

    page.value_gate_check.setChecked(True)
    page.gate_min_spin.setValue(3.0)
    page.gate_max_spin.setValue(1.0)
    window._preparation_changed()

    assert window.prepared is None
    assert window._preparation_error is not None
    window._reconstruct()
    assert window.prepared is None
    assert window.result is None
    assert "min <= max" in window.statusBar().currentMessage()
    window.close()


def test_analysis_histogram_controls_drive_and_sync_both_view_instances(application) -> None:
    window = MapReconstructionWindow()
    data = _data()
    window._load_data(data, b"loaded-source", "measurement.csv", reconstruct=False)
    window.processed = ProcessedMap(
        np.asarray([[1.0, 2.0], [3.0, 4.0]]), None, (), "Current", False
    )
    analysis = window.analysis_map_views
    reconstruction = window.map_views

    analysis.distribution_range_combo.setCurrentIndex(1)
    analysis.distribution_min_spin.setValue(1.5)
    analysis.distribution_max_spin.setValue(3.5)
    analysis.distributionControlsChanged.emit()

    assert reconstruction.distribution_range_combo.currentIndex() == 1
    assert reconstruction.distribution_min_spin.value() == pytest.approx(1.5)
    assert reconstruction.distribution_max_spin.value() == pytest.approx(3.5)
    window.close()


def test_stage_local_exports_replace_the_global_header_menu(application) -> None:
    window = MapReconstructionWindow()
    assert not hasattr(window.workflow_header, "export_menu")
    assert window.preparation_page.export_button.text() == "Export prepared trace"
    assert window.analysis_page.export_processed_button.text() == "Export processed map"
    assert window.analysis_page.export_report_button.text() == "Export report"
    window.close()


def test_project_with_incomplete_manual_preparation_opens_as_repairable_workspace(
    application, tmp_path: Path
) -> None:
    project = tmp_path / "draft.hmmap"
    state = ProjectState(
        original_filename="measurement.csv",
        signal="Current_A",
        rows=0,
        columns=0,
        scan_pattern=ScanPattern.SERPENTINE,
        first_row_ltr=True,
        aggregation="median",
        row_a_s=5.0,
        row_b_s=10.0,
        rows_apart=1,
        row_offset=0,
        point_a_s=5.0,
        point_b_s=6.0,
        points_apart=1,
        point_offset=0,
        processing=MapProcessingConfig(),
        flip_y=False,
        preparation=SignalPreparationConfig(dark_correction_mode=DarkCorrectionMode.MANUAL_REGIONS),
    )
    save_project(project, state, _raw_csv())

    window = MapReconstructionWindow()
    window.load_project_file(project)

    assert window.data is not None
    assert window.prepared is None
    assert window.result is None
    assert window.preparation_config.dark_correction_mode is DarkCorrectionMode.MANUAL_REGIONS
    assert "Fix Signal Preparation" in window.preparation_page.diagnostics.text()
    window.close()
