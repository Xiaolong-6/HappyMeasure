from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
PySide6 = pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from PySide6 import QtWidgets

from map_reconstruction.models import TimeSeriesData
from map_reconstruction.ui.main_window import MAX_GUIDES_PER_FAMILY, MapReconstructionWindow


@pytest.fixture(scope="module")
def application():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _window_with_valid_reconstruction(application) -> MapReconstructionWindow:
    window = MapReconstructionWindow()
    time = np.linspace(0.0, 10.0, 10_001)
    current = 1e-6 * np.sin(time)
    voltage = np.cos(time)
    window.data = TimeSeriesData(time_s=time, signals={"Current_A": current, "Voltage_V": voltage})
    window.signal_combo.blockSignals(True)
    window.signal_combo.addItems(window.data.signal_names)
    window.signal_combo.setCurrentText("Current_A")
    window.signal_combo.blockSignals(False)
    window._set_anchor_bounds(window.data)
    window.rows_spin.setValue(2)
    window.cols_spin.setValue(2)
    window.rows_apart_spin.setValue(1)
    window.row_offset_spin.setValue(0)
    window.points_apart_spin.setValue(1)
    window.point_offset_spin.setValue(0)
    window.row_a_spin.setValue(0.0)
    window.row_b_spin.setValue(4.0)
    window.point_a_spin.setValue(0.5)
    window.point_b_spin.setValue(1.5)
    window._sync_point_period_from_anchors()
    window._set_raw_signal("Current_A")
    window._create_anchor_lines()
    window._set_loaded_view(True)
    window._reconstruct()
    assert window.result is not None
    return window


def test_signal_selection_keeps_raw_trace_and_map_in_sync(application) -> None:
    window = _window_with_valid_reconstruction(application)

    window.signal_combo.setCurrentText("Voltage_V")

    _, raw_values = window.raw_curve.getData()
    assert window.result is not None
    np.testing.assert_allclose(raw_values, window.data.signals["Voltage_V"])
    assert window.raw_plot.getAxis("left").label.toPlainText().strip() == "Voltage (V)"
    assert window.map_color_bar.getAxis("right").label.toPlainText().strip() == "Voltage (V)"
    window.close()


def test_fresh_geometry_is_unset(application) -> None:
    window = MapReconstructionWindow()

    assert window.findChild(QtWidgets.QFrame, "appHeader") is None
    assert window.inspector.isAncestorOf(window.open_button)
    assert window.inspector.isAncestorOf(window.export_button)
    assert window.rows_spin.value() == 0
    assert window.cols_spin.value() == 0
    assert window.rows_spin.specialValueText() == "—"
    assert window.cols_spin.specialValueText() == "—"
    long_name = "very_long_measurement_name_" * 12 + ".csv"
    window.inspector.set_file_name(long_name)
    assert window.file_label.toolTip() == long_name
    assert window.file_label.sizePolicy().horizontalPolicy() is QtWidgets.QSizePolicy.Policy.Ignored
    window.close()


def test_load_file_waits_for_geometry_then_initializes_fit_anchors(application) -> None:
    path = Path.cwd() / ".synthetic_single_v2_map_regression.csv"
    time = np.linspace(0.0, 10.0, 10_001)
    current = 2e-6 + 0.5e-6 * np.sin(time)
    voltage = np.cos(time)
    rows = [
        "# schema,single-v2",
        '# metadata,{"source":"synthetic regression"}',
        "# section,data",
        "Elapsed_s,Current_A,Voltage_V",
    ]
    rows.extend(f"{t:.9f},{i:.12g},{v:.12g}" for t, i, v in zip(time, current, voltage))
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    try:
        window = MapReconstructionWindow()
        window.load_file(path)

        _, raw_values = window.raw_curve.getData()
        assert raw_values.size == current.size
        assert np.isfinite(raw_values).all()
        assert window.result is None
        assert window.rows_spin.value() == 0
        assert window.cols_spin.value() == 0
        assert "Set Rows and Columns" in window.statusBar().currentMessage()
        assert window.row_b_spin.value() > window.row_a_spin.value()
        assert window.point_b_spin.value() > window.point_a_spin.value()
        assert window.row_a_spin.value() == pytest.approx(2.0)
        assert window.row_b_spin.value() == pytest.approx(7.0)
        assert window.point_a_spin.value() == pytest.approx(0.5)
        assert window.point_b_spin.value() == pytest.approx(0.6)
        assert window.point_period_spin.value() > 0.0

        window.rows_spin.setValue(2)
        window.cols_spin.setValue(2)

        assert window.result is not None
        assert window.inspector.timing_label.text() == "Timing valid: ✓"
        row_period = (
            window.row_b_spin.value() - window.row_a_spin.value()
        ) / window.rows_apart_spin.value()
        point_period = (
            window.point_b_spin.value() - window.point_a_spin.value()
        ) / window.points_apart_spin.value()
        last_row_end = (
            window.row_a_spin.value()
            + (window.rows_spin.value() - 1) * row_period
            + window.cols_spin.value() * point_period
        )
        assert last_row_end <= time[-1]
        assert window.cols_spin.value() * point_period < row_period
        window.close()
    finally:
        path.unlink(missing_ok=True)


def test_invalid_timing_clears_stale_result_and_disables_export(application) -> None:
    window = _window_with_valid_reconstruction(application)

    window.row_b_spin.setValue(window.row_a_spin.value())
    window._reconstruct()

    assert window.result is None
    assert window.params is None
    assert not window.export_button.isEnabled()
    assert window.map_stack.currentIndex() == 0
    assert window.count_stack.currentIndex() == 0
    assert window.distribution_stack.currentIndex() == 0
    assert window.guide_items == []
    assert all(value.text() == "—" for value in window.qc_values.values())
    window.close()


def test_no_valid_pixels_uses_empty_map_state_without_zero_fabrication(application) -> None:
    window = MapReconstructionWindow()
    window.data = TimeSeriesData(
        time_s=np.asarray([0.0, 10.0]),
        signals={"Current_A": np.asarray([1e-6, 2e-6])},
    )
    window.signal_combo.addItem("Current_A")
    window._set_anchor_bounds(window.data)
    window.rows_spin.setValue(1)
    window.cols_spin.setValue(1)
    window.rows_apart_spin.setValue(1)
    window.row_offset_spin.setValue(0)
    window.points_apart_spin.setValue(1)
    window.point_offset_spin.setValue(0)
    window.row_a_spin.setValue(4.0)
    window.row_b_spin.setValue(5.0)
    window.point_a_spin.setValue(4.0)
    window.point_b_spin.setValue(5.0)
    window._set_raw_signal("Current_A")
    window._create_anchor_lines()
    window._set_loaded_view(True)
    window._reconstruct()

    assert window.result is None
    assert window.map_stack.currentIndex() == 0
    assert window.count_stack.currentIndex() == 1
    assert not window.export_button.isEnabled()
    window.close()


def test_point_period_edit_moves_point_b_and_guide_decimation_is_bounded(application) -> None:
    window = _window_with_valid_reconstruction(application)
    window.point_a_spin.setValue(1.0)
    window.points_apart_spin.setValue(2)
    window.point_period_spin.setValue(0.5)

    window._point_period_finished()

    assert window.point_b_spin.value() == pytest.approx(2.0)
    assert window._guide_indices(10_000).size == MAX_GUIDES_PER_FAMILY
    window.close()


def test_processing_changes_reuse_raw_result_and_keep_trace_signed(
    application, monkeypatch
) -> None:
    window = _window_with_valid_reconstruction(application)
    assert window.result is not None
    raw_values = window.result.values.copy()
    _, raw_before = window.raw_curve.getData()

    def unexpected_reconstruction(*_args, **_kwargs):
        raise AssertionError("processing-only changes must not rerun reconstruction")

    monkeypatch.setattr(
        "map_reconstruction.ui.main_window.reconstruct_map", unexpected_reconstruction
    )
    window.transform_combo.setCurrentIndex(1)  # Absolute value

    assert window.processed is not None
    np.testing.assert_array_equal(window.result.values, raw_values)
    np.testing.assert_array_equal(window.raw_curve.getData()[1], raw_before)
    assert np.nanmin(window.processed.values) >= 0
    window.close()


def test_custom_reference_is_unitless_and_processing_error_preserves_raw_result(
    application,
) -> None:
    window = _window_with_valid_reconstruction(application)
    assert window.result is not None
    raw_result = window.result
    sample_counts = np.array(window.count_image.image, copy=True)

    window.normalization_combo.setCurrentIndex(3)
    raw_reference_label = window.inspector._processing_rows["normalization_reference"][0].text()
    assert raw_reference_label != "Normalization reference"
    window.normalization_reference_spin.setValue(2.0)
    window._processing_controls_changed()
    assert window.processed is not None
    assert window.count_stack.currentIndex() == 1

    window.transform_combo.setCurrentIndex(3)
    window.custom_expression_edit.setText("x * 2")
    window._update_processing_units()
    custom_reference_label = window.inspector._processing_rows["normalization_reference"][0].text()
    assert custom_reference_label == "Normalization reference"
    config = window._processing_config()
    assert config.normalization_reference == pytest.approx(2.0)

    window.result.values[:] = 0.0
    window.normalization_combo.setCurrentIndex(1)

    assert window.result is raw_result
    assert window.processed is None
    assert window.count_stack.currentIndex() == 1
    np.testing.assert_array_equal(window.count_image.image, sample_counts)
    assert window.export_button.isEnabled()
    assert "reference is zero" in window.qc_label.text()

    window.normalization_combo.setCurrentIndex(0)
    assert window.processed is not None
    assert window.count_stack.currentIndex() == 1
    assert window.distribution_stack.currentIndex() == 1
    np.testing.assert_array_equal(window.count_image.image, sample_counts)
    window.close()


def test_point_period_control_displays_seconds(application) -> None:
    window = MapReconstructionWindow()
    assert window.point_period_spin.suffix() == " s"
    data = TimeSeriesData(
        time_s=np.asarray([0.0, 1.0]),
        signals={"Current_A": np.asarray([1e-6, 2e-6])},
    )
    window.inspector.set_anchor_bounds(data)
    assert window.point_b_spin.value() > window.point_a_spin.value()
    assert window.point_period_spin.value() > 0.0
    window.close()


def test_user_edited_anchors_are_not_reinitialized_for_later_geometry_changes(application) -> None:
    window = _window_with_valid_reconstruction(application)
    window.row_a_spin.setValue(1.234)
    window._anchor_spin_finished()
    assert window.inspector.anchors_user_edited

    window.rows_spin.setValue(3)

    assert window.row_a_spin.value() == pytest.approx(1.234)
    window.close()


def test_timing_controls_use_native_buttons_and_explain_anchor_semantics(application) -> None:
    window = MapReconstructionWindow()

    for spin in (
        window.row_a_spin,
        window.row_b_spin,
        window.point_a_spin,
        window.point_b_spin,
        window.point_period_spin,
    ):
        assert spin.buttonSymbols() is QtWidgets.QAbstractSpinBox.ButtonSymbols.UpDownArrows
    assert window.row_a_spin.singleStep() == pytest.approx(0.01)
    assert window.point_period_spin.singleStep() == pytest.approx(0.001)
    assert window.row_a_spin.decimals() == 3
    assert window.row_b_spin.decimals() == 3
    assert window.point_a_spin.decimals() == 3
    assert window.point_b_spin.decimals() == 3
    assert window.point_period_spin.decimals() == 4
    assert "T_row = (YB - YA) / Rows apart" in window.rows_apart_spin.toolTip()
    assert "T_point = (XB - XA) / Points apart" in window.points_apart_spin.toolTip()
    labels = {label.text(): label for label in window.inspector.findChildren(QtWidgets.QLabel)}
    assert "First Y/row timing anchor" in labels["YA"].toolTip()
    assert "Second X/pixel timing anchor" in labels["XB"].toolTip()

    window.inspector.set_timing_solution(14.71044, 0.21544, 9.32456)
    assert window.inspector.qc_values["Row period"].text() == "14.7104 s"
    assert window.inspector.qc_values["Point period"].text() == "0.2154 s"
    assert window.inspector.qc_values["Unused / row"].text() == "9.325 s"
    window.close()


def test_trace_uses_ya_yb_xa_xb_labels(application) -> None:
    window = _window_with_valid_reconstruction(application)

    assert all(label in window.raw_guide_key.text() for label in ("YA", "YB", "XA", "XB"))
    assert window.anchor_lines["row_a_s"].label.format == "YA"
    assert window.anchor_lines["row_b_s"].label.format == "YB"
    assert window.anchor_lines["point_a_s"].label.format == "XA"
    assert window.anchor_lines["point_b_s"].label.format == "XB"
    window.close()


def test_raw_export_remains_available_when_log_processing_has_no_finite_values(application) -> None:
    window = _window_with_valid_reconstruction(application)
    assert window.result is not None
    window.result.values[:] = -1e-6

    window.scale_combo.setCurrentIndex(1)

    assert window.processed is not None
    assert not np.isfinite(window.processed.values).any()
    assert window.export_button.isEnabled()
    assert window.raw_export_action.isEnabled()
    assert not window.processed_export_action.isEnabled()
    assert not window.both_export_action.isEnabled()
    assert "no finite processed values" in window.statusBar().currentMessage().lower()
    window.close()
