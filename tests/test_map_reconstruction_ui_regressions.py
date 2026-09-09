from __future__ import annotations

import os
import inspect
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
PySide6 = pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from PySide6 import QtWidgets

from map_reconstruction.models import TimeSeriesData
from map_reconstruction.project_io import save_project
import map_reconstruction.reporting as reporting
from map_reconstruction.reporting import generate_pdf_report, select_report_map
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


def test_project_round_trip_restores_ui_once_without_original_source(
    application, tmp_path: Path
) -> None:
    source = tmp_path / "measurement.csv"
    time = np.linspace(0.0, 1.0, 1001)
    source.write_text(
        "\n".join(
            [
                "# schema,single-v2",
                '# metadata,{"source":"synthetic"}',
                "# section,data",
                "Elapsed_s,Current_A,Voltage_V",
                *(f"{t:.6f},{1e-6 + t * 1e-6:.12g},{t:.12g}" for t in time),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    project = tmp_path / "session.hmmap"
    first = MapReconstructionWindow()
    try:
        first.load_file(source)
        assert first.project_export_action.isEnabled()
        assert first.summary_export_action.isEnabled()
        assert not first.pdf_export_action.isEnabled()
        first.rows_spin.setValue(2)
        first.cols_spin.setValue(2)
        first.rows_apart_spin.setValue(1)
        first.points_apart_spin.setValue(1)
        first.row_a_spin.setValue(0.100)
        first.row_b_spin.setValue(0.500)
        first.point_a_spin.setValue(0.150)
        first.point_b_spin.setValue(0.250)
        first.row_offset_spin.setValue(1)
        first.point_offset_spin.setValue(1)
        first._anchor_spin_finished()
        first.transform_combo.setCurrentIndex(first.transform_combo.findData("absolute"))
        first.baseline_combo.setCurrentIndex(first.baseline_combo.findData("manual"))
        first.baseline_value_spin.setValue(0.5)
        first.normalization_combo.setCurrentIndex(first.normalization_combo.findData("reference"))
        first.normalization_reference_spin.setValue(2.0)
        first.color_range_combo.setCurrentIndex(first.color_range_combo.findData("percentile"))
        first.percentile_low_spin.setValue(5.0)
        first.percentile_high_spin.setValue(95.0)
        first.custom_expression_edit.setText("abs(x) * 2")
        first.flip_y_check.setChecked(True)
        first._processing_controls_changed()
        assert first.result is not None
        assert first.pdf_export_action.isEnabled()
        state = first._project_state()
        values = first.result.values.copy()
        save_project(project, state, first._raw_source_bytes or b"")
    finally:
        first.close()
    source.unlink()

    second = MapReconstructionWindow()
    calls = 0
    original_reconstruct = second._reconstruct

    def counted_reconstruct() -> None:
        nonlocal calls
        calls += 1
        original_reconstruct()

    second._reconstruct = counted_reconstruct  # type: ignore[method-assign]
    try:
        second.load_project_file(project)
        assert calls == 1
        assert second._loaded_filename == "measurement.csv"
        assert second.file_label.toolTip() == "measurement.csv"
        assert second._project_state() == state
        assert second.result is not None
        np.testing.assert_allclose(second.result.values, values, equal_nan=True)
        np.testing.assert_allclose(second.data.time_s, time)
        assert second.raw_export_action.isEnabled()
        assert second.project_export_action.isEnabled()
        assert second.summary_export_action.isEnabled()
        assert second.pdf_export_action.isEnabled()
    finally:
        second.close()


def test_partial_project_restores_workspace_without_reconstruction(
    application, tmp_path: Path
) -> None:
    source = tmp_path / "partial.csv"
    raw = (
        b"# schema,single-v2\n"
        b"# section,data\n"
        b"Elapsed_s,Current_A\n"
        b"0,1e-6\n"
        b"0.1,2e-6\n"
    )
    source.write_bytes(raw)
    project = tmp_path / "partial.hmmap"
    first = MapReconstructionWindow()
    try:
        first.load_file(source)
        assert first.rows_spin.value() == 0
        assert first.cols_spin.value() == 0
        save_project(project, first._project_state(), raw)
    finally:
        first.close()

    second = MapReconstructionWindow()
    calls = 0
    original_reconstruct = second._reconstruct

    def counted_reconstruct() -> None:
        nonlocal calls
        calls += 1
        original_reconstruct()

    second._reconstruct = counted_reconstruct  # type: ignore[method-assign]
    try:
        second.load_project_file(project)
        assert calls == 0
        assert second.data is not None
        assert second.result is None
        assert second._project_state().is_geometry_set is False
        assert "Set Rows and Columns" in second.statusBar().currentMessage()
    finally:
        second.close()


def test_voltage_project_restore_uses_the_saved_signal_scale(application, tmp_path: Path) -> None:
    source = tmp_path / "voltage_measurement.csv"
    time = np.linspace(0.0, 1.0, 1001)
    source.write_text(
        "\n".join(
            [
                "# schema,single-v2",
                "# section,data",
                "Elapsed_s,Current_A,Voltage_V",
                *(f"{t:.6f},{1e-6 + t * 1e-6:.12g},{0.1 + 0.8 * t:.12g}" for t in time),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    project = tmp_path / "voltage.hmmap"
    first = MapReconstructionWindow()
    try:
        first.load_file(source)
        first.signal_combo.setCurrentText("Voltage_V")
        first.rows_spin.setValue(2)
        first.cols_spin.setValue(2)
        first.rows_apart_spin.setValue(1)
        first.points_apart_spin.setValue(1)
        first.row_a_spin.setValue(0.1)
        first.row_b_spin.setValue(0.7)
        first.point_a_spin.setValue(0.2)
        first.point_b_spin.setValue(0.4)
        first.baseline_combo.setCurrentIndex(first.baseline_combo.findData("manual"))
        first.baseline_value_spin.setValue(200.0)  # 200 mV = 0.2 V
        first.normalization_combo.setCurrentIndex(first.normalization_combo.findData("reference"))
        first.normalization_reference_spin.setValue(500.0)  # 500 mV = 0.5 V
        first.color_range_combo.setCurrentIndex(first.color_range_combo.findData("manual"))
        first.color_min_spin.setValue(-0.1)
        first.color_max_spin.setValue(0.8)
        first._processing_controls_changed()
        state = first._project_state()
        assert state.signal == "Voltage_V"
        assert state.processing.baseline_value == pytest.approx(0.2)
        assert state.processing.normalization_reference == pytest.approx(0.5)
        save_project(project, state, first._raw_source_bytes or b"")
    finally:
        first.close()

    second = MapReconstructionWindow()
    try:
        second.load_project_file(project)
        restored = second._processing_config()
        assert second.signal_combo.currentText() == "Voltage_V"
        assert restored.baseline_value == pytest.approx(0.2)
        assert restored.normalization_reference == pytest.approx(0.5)
        assert restored.color_min == pytest.approx(-0.1)
        assert restored.color_max == pytest.approx(0.8)
    finally:
        second.close()


def test_pdf_report_is_created_without_mutating_reconstruction(application, tmp_path: Path) -> None:
    window = _window_with_valid_reconstruction(application)
    assert window.result is not None
    original_values = window.result.values.copy()
    original_counts = window.result.sample_counts.copy()
    assert window.processed is not None
    original_processed = window.processed.values.copy()
    report = tmp_path / "report.pdf"
    unicode_state = replace(window._project_state(), original_filename="测量.csv")
    try:
        generate_pdf_report(
            report,
            unicode_state,
            window.data,
            window.result,
            window.processed,
            count_widget=window.count_plot,
            trace_widget=window.raw_plot,
        )
        assert report.read_bytes().startswith(b"%PDF")
        assert report.stat().st_size > 1_000
        assert "Rows × columns" in reporting.format_parameter_summary(unicode_state)
        assert "—" in reporting.format_parameter_summary(
            replace(unicode_state, rows=0, columns=0, row_offset=0, point_offset=0)
        )
        assert 'encode("ascii"' not in inspect.getsource(reporting.generate_pdf_report)
        np.testing.assert_array_equal(window.result.values, original_values)
        np.testing.assert_array_equal(window.result.sample_counts, original_counts)
        np.testing.assert_array_equal(window.processed.values, original_processed)
    finally:
        window.close()


def test_report_array_image_renders_partial_nan_pixels_as_neutral(application) -> None:
    values = np.asarray([[1.0, np.nan, 3.0], [4.0, 5.0, np.nan]])
    colors = np.asarray([[10, 20, 30], [110, 120, 130], [210, 220, 230]], dtype=float)

    image = reporting._array_image(values, colors, (1.0, 5.0))

    assert image.width() == 3
    assert image.height() == 2
    assert image.pixelColor(0, 0).getRgb()[:3] == (10, 20, 30)
    assert image.pixelColor(2, 0).getRgb()[:3] == (110, 120, 130)
    assert image.pixelColor(1, 1).getRgb()[:3] == (210, 220, 230)
    assert image.pixelColor(1, 0).getRgb()[:3] == (238, 238, 238)
    assert image.pixelColor(2, 1).getRgb()[:3] == (238, 238, 238)


def test_pdf_report_renders_partial_nan_raw_fallback_without_mutation(application) -> None:
    window = _window_with_valid_reconstruction(application)
    assert window.result is not None
    raw_values = np.asarray([[1e-6, np.nan], [3e-6, 5e-6]])
    counts = np.asarray([[1, 0], [2, 3]])
    result = type(window.result)(raw_values, counts, window.result.timing, window.result.warnings)
    state = replace(window._project_state(), flip_y=False)
    try:
        report_map = select_report_map(state, result, None)
        assert report_map.title == "Raw reconstructed map"
        assert report_map.color_limits == pytest.approx((1e-6, 5e-6))
        for flip_y in (False, True):
            report = Path.cwd() / f".raw_partial_nan_{flip_y}.pdf"
            generate_pdf_report(
                report,
                replace(state, flip_y=flip_y),
                window.data,
                result,
                None,
                count_widget=window.count_plot,
                trace_widget=window.raw_plot,
            )
            assert report.read_bytes().startswith(b"%PDF")
            assert report.stat().st_size > 1_000
        np.testing.assert_allclose(result.values, raw_values, equal_nan=True)
        np.testing.assert_array_equal(result.sample_counts, counts)
    finally:
        for flip_y in (False, True):
            (Path.cwd() / f".raw_partial_nan_{flip_y}.pdf").unlink(missing_ok=True)
        window.close()


def test_pdf_report_renders_partial_nan_processed_map_with_configured_limits(application) -> None:
    window = _window_with_valid_reconstruction(application)
    assert window.result is not None
    assert window.processed is not None
    raw_values = np.asarray([[1e-6, np.nan], [3e-6, 5e-6]])
    counts = np.asarray([[1, 0], [2, 3]])
    result = type(window.result)(raw_values, counts, window.result.timing, window.result.warnings)
    processed_values = np.asarray([[-0.5, np.nan], [0.25, 0.75]])
    processed = type(window.processed)(
        processed_values,
        window.processed.baseline_used,
        window.processed.warnings,
        window.processed.value_label,
        window.processed.is_dimensionless,
    )
    state = replace(
        window._project_state(),
        processing=replace(
            window._project_state().processing,
            color_range_mode="manual",
            color_min=-1.0,
            color_max=1.0,
        ),
    )
    report = Path.cwd() / ".processed_partial_nan.pdf"
    try:
        report_map = select_report_map(state, result, processed)
        assert report_map.title == "Processed map"
        assert report_map.color_limits == pytest.approx((-1.0, 1.0))
        generate_pdf_report(
            report,
            state,
            window.data,
            result,
            processed,
            count_widget=window.count_plot,
            trace_widget=window.raw_plot,
        )
        assert report.read_bytes().startswith(b"%PDF")
        assert report.stat().st_size > 1_000
        np.testing.assert_allclose(result.values, raw_values, equal_nan=True)
        np.testing.assert_array_equal(result.sample_counts, counts)
        np.testing.assert_allclose(processed.values, processed_values, equal_nan=True)
    finally:
        report.unlink(missing_ok=True)
        window.close()


def test_pdf_report_falls_back_to_raw_map_for_unavailable_processing(
    application, tmp_path: Path
) -> None:
    window = _window_with_valid_reconstruction(application)
    assert window.result is not None
    report = tmp_path / "raw_fallback.pdf"
    all_nan = window.processed
    assert all_nan is not None
    all_nan_values = np.full(all_nan.values.shape, np.nan)
    unavailable = type(all_nan)(
        all_nan_values,
        all_nan.baseline_used,
        all_nan.warnings,
        all_nan.value_label,
        all_nan.is_dimensionless,
    )
    try:
        assert (
            select_report_map(window._project_state(), window.result, None).title
            == "Raw reconstructed map"
        )
        assert (
            select_report_map(window._project_state(), window.result, unavailable).title
            == "Raw reconstructed map"
        )
        generate_pdf_report(
            report,
            window._project_state(),
            window.data,
            window.result,
            unavailable,
            count_widget=window.count_plot,
            trace_widget=window.raw_plot,
        )
        assert report.read_bytes().startswith(b"%PDF")
    finally:
        window.close()
