"""Composition root for the standalone Map Reconstruction application."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

try:
    import pyqtgraph as _pyqtgraph  # type: ignore[import-not-found, import-untyped]  # noqa: F401
    from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore[import-not-found]
except ImportError as exc:  # pragma: no cover - optional GUI dependency
    raise ImportError("PySide6 and pyqtgraph are required for the Map Reconstruction UI") from exc

from map_reconstruction.display_units import (
    DisplayUnit,
    display_unit_for_signal,
)
from map_reconstruction.importers.happymeasure import import_happymeasure_csv
from map_reconstruction.methods.dual_offset import reconstruct_map
from map_reconstruction.models import DualOffsetParams, ReconstructionResult, TimeSeriesData
from map_reconstruction.processing import (
    MapProcessingConfig,
    NormalizationMode,
    ProcessedMap,
    ValueScale,
    ValueTransform,
    compute_color_limits,
    process_map,
)
from map_reconstruction.ui.exporting import (
    export_both,
    export_processed,
    export_raw,
    processed_export_metadata,
)
from map_reconstruction.ui.inspector import ReconstructionInspector
from map_reconstruction.ui.map_views import MapViews
from map_reconstruction.ui.style import apply_light_theme
from map_reconstruction.ui.trace_view import MAX_GUIDES_PER_FAMILY, TraceView  # noqa: F401


class MapReconstructionWindow(QtWidgets.QMainWindow):
    """Coordinate file lifecycle, reconstruction, processing, and view updates."""

    params: DualOffsetParams | None
    processing_config: MapProcessingConfig | None
    signal_combo: QtWidgets.QComboBox
    flip_y_check: QtWidgets.QCheckBox
    rows_spin: QtWidgets.QSpinBox
    cols_spin: QtWidgets.QSpinBox
    row_a_spin: QtWidgets.QDoubleSpinBox
    row_b_spin: QtWidgets.QDoubleSpinBox
    point_a_spin: QtWidgets.QDoubleSpinBox
    point_b_spin: QtWidgets.QDoubleSpinBox
    transform_combo: QtWidgets.QComboBox
    normalization_combo: QtWidgets.QComboBox
    scale_combo: QtWidgets.QComboBox

    def __init__(self, initial_path: Path | None = None) -> None:
        super().__init__()
        application = QtWidgets.QApplication.instance()
        if isinstance(application, QtWidgets.QApplication):
            apply_light_theme(application)
        self.data: TimeSeriesData | None = None
        self.result: ReconstructionResult | None = None
        self.params = None
        self.processed: ProcessedMap | None = None
        self.processing_config = None
        self._active_color_limits: tuple[float, float] | None = None
        self._loaded_filename: str | None = None
        self._syncing = False
        self.setWindowTitle("Map Reconstruction")
        icon_path = Path(__file__).resolve().parents[1] / "assets" / "map_reconstruction.png"
        self.setWindowIcon(QtGui.QIcon(str(icon_path)))
        self.resize(1280, 820)
        self._build_ui()
        if initial_path is not None:
            self.load_file(initial_path)

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(16, 14, 16, 10)
        root.setSpacing(12)
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        root.addWidget(splitter)
        root.setStretch(0, 1)
        self.setCentralWidget(central)

        self.inspector = ReconstructionInspector(self)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.inspector)
        scroll.setMinimumWidth(215)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        splitter.addWidget(scroll)

        right = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self.map_views = MapViews(self)
        self.trace_view = TraceView(parent=self)
        right.addWidget(self.map_views)
        right.addWidget(self.trace_view)
        right.setStretchFactor(0, 45)
        right.setStretchFactor(1, 55)
        right.setSizes([360, 440])
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([238, 942])

        self._expose_compatibility_attributes()
        self.inspector.signalChanged.connect(self._signal_changed)
        self.inspector.geometryChanged.connect(self._reconstruct)
        self.inspector.registrationChanged.connect(self._reconstruct)
        self.inspector.processingChanged.connect(self._processing_controls_changed)
        self.inspector.pointPeriodEdited.connect(self._point_period_edited)
        self.inspector.resetTraceRequested.connect(self._reset_views)
        self.inspector.openRequested.connect(self._choose_file)
        self.inspector.exportRawRequested.connect(self._export_raw_map)
        self.inspector.exportProcessedRequested.connect(self._export_processed_map)
        self.inspector.exportBothRequested.connect(self._export_both_maps)
        self.trace_view.anchorMoved.connect(self._anchor_moved)
        self.trace_view.anchorMoveFinished.connect(self._anchor_finished)
        self._set_loaded_view(False)

    def _expose_compatibility_attributes(self) -> None:
        """Keep the small existing UI regression surface stable during the split."""

        inspector_names = (
            "file_label",
            "open_button",
            "export_button",
            "raw_export_action",
            "processed_export_action",
            "both_export_action",
            "signal_combo",
            "rows_spin",
            "cols_spin",
            "scan_combo",
            "first_row_check",
            "flip_y_check",
            "median_check",
            "row_a_spin",
            "row_b_spin",
            "rows_apart_spin",
            "row_offset_spin",
            "row_offset_slider",
            "point_a_spin",
            "point_b_spin",
            "points_apart_spin",
            "point_period_spin",
            "point_offset_spin",
            "point_offset_slider",
            "transform_combo",
            "baseline_combo",
            "normalization_combo",
            "scale_combo",
            "color_range_combo",
            "baseline_value_spin",
            "baseline_percentile_spin",
            "custom_expression_edit",
            "normalization_reference_spin",
            "percentile_low_spin",
            "percentile_high_spin",
            "color_min_spin",
            "color_max_spin",
            "processing_summary",
            "timing_label",
            "qc_values",
            "qc_label",
        )
        for name in inspector_names:
            setattr(self, name, getattr(self.inspector, name))
        view_names = (
            "map_stack",
            "map_plot",
            "map_image",
            "map_color_bar",
            "count_stack",
            "count_plot",
            "count_image",
            "count_color_bar",
            "qc_tabs",
            "distribution_stack",
            "distribution_plot",
            "distribution_bars",
            "mean_line",
            "median_line",
            "distribution_stats",
            "raw_plot",
            "raw_curve",
            "raw_guide_key",
        )
        for name in view_names:
            source = self.map_views if hasattr(self.map_views, name) else self.trace_view
            setattr(self, name, getattr(source, name))

    @property
    def guide_items(self):
        return self.trace_view.guide_items

    @property
    def anchor_lines(self):
        return self.trace_view.anchor_lines

    @staticmethod
    def _guide_indices(count: int) -> np.ndarray:
        return TraceView.guide_indices(count)

    def _choose_file(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open HappyMeasure single-v2 CSV", "", "CSV files (*.csv);;All files (*.*)"
        )
        if path:
            self.load_file(Path(path))

    def load_file(self, path: Path) -> None:
        try:
            data = import_happymeasure_csv(path)
        except (OSError, ValueError) as exc:
            QtWidgets.QMessageBox.critical(self, "Could not open CSV", str(exc))
            return
        self.data = data
        self.result = None
        self.params = None
        self.processed = None
        self._active_color_limits = None
        self._loaded_filename = path.name
        self.inspector.set_file_name(path.name)
        preferred = "Current_A" if "Current_A" in data.signals else data.signal_names[-1]
        self.inspector.set_signal_names(data.signal_names, preferred)
        self._set_anchor_bounds(data)
        self._set_raw_signal(preferred)
        self._update_processing_units()
        self._create_anchor_lines()
        self._set_loaded_view(True)
        self._reconstruct()
        if self.rows_spin.value() <= 0 or self.cols_spin.value() <= 0:
            self.statusBar().showMessage("Set Rows and Columns to reconstruct.")

    def _set_loaded_view(self, loaded: bool) -> None:
        self.map_views.set_loaded(loaded)
        self.trace_view.show_loaded(loaded)
        self._set_export_availability()

    def _set_export_availability(self) -> None:
        raw_available = self.result is not None
        processed_available = bool(
            self.processed is not None and np.isfinite(self.processed.values).any()
        )
        self.inspector.set_export_availability(raw_available, processed_available)

    def _set_anchor_bounds(self, data: TimeSeriesData) -> None:
        lower, upper = float(data.time_s[0]), float(data.time_s[-1])
        self.inspector.set_anchor_bounds(data)
        self.trace_view.set_anchor_bounds(lower, upper)

    def _create_anchor_lines(self) -> None:
        self.trace_view.set_anchors(
            {
                "row_a_s": self.row_a_spin.value(),
                "row_b_s": self.row_b_spin.value(),
                "point_a_s": self.point_a_spin.value(),
                "point_b_s": self.point_b_spin.value(),
            }
        )

    def _set_raw_signal(self, signal_name: str) -> None:
        if self.data is None or signal_name not in self.data.signals:
            return
        unit = display_unit_for_signal(signal_name, self.data.signals[signal_name])
        self.trace_view.set_signal(self.data.time_s, self.data.signals[signal_name], unit)

    def _signal_changed(self, signal_name: str) -> None:
        if self.data is None:
            return
        self._set_raw_signal(signal_name)
        self._update_processing_units()
        self._reconstruct()

    def _anchor_moved(self, name: str, value: float) -> None:
        self.inspector.mark_anchors_user_edited()
        self._syncing = True
        getattr(self, name.replace("_s", "") + "_spin").setValue(value)
        self._syncing = False

    def _anchor_finished(self, _name: str, _value: float) -> None:
        self._sync_point_period_from_anchors()
        self._reconstruct()

    def _sync_point_period_from_anchors(self) -> None:
        self.inspector._sync_point_period_from_anchors()

    def _anchor_spin_finished(self) -> None:
        self.inspector._anchor_spin_finished()

    def _point_period_finished(self) -> None:
        self.inspector._point_period_finished()

    def _point_period_edited(self, point_b: float) -> None:
        if self.data is None:
            return
        if not self.point_b_spin.minimum() <= point_b <= self.point_b_spin.maximum():
            self._invalidate_reconstruction(
                "Point period places Point B outside the loaded time range."
            )
            return
        self.inspector.set_point_b_value(point_b)
        self.trace_view.set_anchor_value("point_b_s", point_b)
        self._reconstruct()

    def _current_display_unit(self) -> DisplayUnit:
        if self.processed is not None and self.processed.is_dimensionless:
            return DisplayUnit(self.processed.value_label, "", 1.0)
        raw = self._raw_display_unit()
        return (
            DisplayUnit(self.processed.value_label, raw.unit, raw.scale) if self.processed else raw
        )

    def _raw_display_unit(self) -> DisplayUnit:
        if self.data is None:
            return display_unit_for_signal(self.signal_combo.currentText())
        return display_unit_for_signal(
            self.signal_combo.currentText(), self.data.signals.get(self.signal_combo.currentText())
        )

    def _processing_display_scale(self) -> float:
        transform = ValueTransform(self.transform_combo.currentData())
        normalization = NormalizationMode(self.normalization_combo.currentData())
        scale = ValueScale(self.scale_combo.currentData())
        if transform is ValueTransform.CUSTOM or normalization is not NormalizationMode.NONE:
            return 1.0
        if scale is ValueScale.LOG10:
            return 1.0
        return self._raw_display_unit().scale

    def _normalization_reference_scale(self) -> float:
        transform = ValueTransform(self.transform_combo.currentData())
        return (
            self._raw_display_unit().scale
            if transform in (ValueTransform.RAW, ValueTransform.ABSOLUTE, ValueTransform.NEGATE)
            else 1.0
        )

    def _processing_config(self):
        return self.inspector.current_processing_config(
            self._raw_display_unit().scale,
            self._normalization_reference_scale(),
            self._processing_display_scale(),
        )

    def _update_processing_units(self) -> None:
        raw = self._raw_display_unit()
        transform = ValueTransform(self.transform_combo.currentData())
        dimensionless = (
            transform is ValueTransform.CUSTOM
            or NormalizationMode(self.normalization_combo.currentData())
            is not NormalizationMode.NONE
            or ValueScale(self.scale_combo.currentData()) is ValueScale.LOG10
        )
        normalization_reference = (
            raw
            if transform in (ValueTransform.RAW, ValueTransform.ABSOLUTE, ValueTransform.NEGATE)
            else DisplayUnit(raw.label, "", 1.0)
        )
        self.inspector.set_processing_units(
            raw,
            normalization_reference,
            DisplayUnit(raw.label, "", 1.0) if dimensionless else raw,
        )

    def _processing_controls_changed(self) -> None:
        self._update_processing_units()
        if self.result is not None:
            self._process_and_display()

    def _reconstruct(self) -> None:
        if self.data is None or self._syncing:
            return
        if self.rows_spin.value() <= 0 or self.cols_spin.value() <= 0:
            self._invalidate_reconstruction("Set Rows and Columns to reconstruct.")
            return
        if self.inspector.initialize_geometry_aware_anchors(self.data):
            self._create_anchor_lines()
        try:
            params = self.inspector.current_params()
            result = reconstruct_map(self.data, self.signal_combo.currentText(), params)
        except ValueError as exc:
            self._invalidate_reconstruction(str(exc))
            return
        self.params = params
        finite = np.isfinite(result.values)
        self.inspector.set_timing_solution(
            result.timing.row_period_s,
            result.timing.point_period_s,
            result.timing.row_period_s - params.cols * result.timing.point_period_s,
        )
        self.inspector.set_qc(
            100.0 * float(np.mean(finite)),
            float(np.median(result.sample_counts[finite])) if np.any(finite) else 0.0,
        )
        if not np.any(finite):
            self.result = None
            self.processed = None
            self._active_color_limits = None
            message = "No valid pixels for current timing."
            self.inspector.set_warning(" | ".join([message, *result.warnings]))
            self.map_views.clear_processed_views("No valid reconstructed pixels")
            self.map_views.show_sample_counts(result.sample_counts, self.flip_y_check.isChecked())
            self.trace_view.clear_guides()
            self._set_export_availability()
            self.statusBar().showMessage(message)
            return
        self.result = result
        self._process_and_display()
        self.map_views.show_sample_counts(result.sample_counts, self.flip_y_check.isChecked())
        self._update_guides(result)
        self._set_export_availability()

    def _process_and_display(self) -> None:
        if self.result is None or self.data is None:
            return
        try:
            config = self._processing_config()
            processed = process_map(self.result.values, config, self.signal_combo.currentText())
            limits = compute_color_limits(processed.values, config)
        except ValueError as exc:
            self.processed = None
            self._active_color_limits = None
            self.map_views.clear_processed_map_and_distribution("Processing unavailable")
            self.inspector.set_warning(str(exc))
            self._set_export_availability()
            self.statusBar().showMessage("Raw map reconstructed; processing unavailable.")
            return
        self.processing_config = config
        self.processed = processed
        display_unit = self._current_display_unit()
        self.inspector.set_processing_summary(
            f"{processed.value_label} - {config.value_scale.value}"
            + (f" - {len(processed.warnings)} warning(s)" if processed.warnings else "")
        )
        self.inspector.set_warning(" | ".join([*self.result.warnings, *processed.warnings]))
        if limits is None:
            self._active_color_limits = None
            self.map_views.show_empty_map(
                "No finite processed values", "Adjust processing settings."
            )
        else:
            display_limits = (
                limits.minimum * display_unit.scale,
                limits.maximum * display_unit.scale,
            )
            self._active_color_limits = display_limits
            self.map_views.show_processed_map(
                processed.values,
                display_unit,
                display_limits,
                self.flip_y_check.isChecked(),
                display_unit.axis_label,
            )
        self.map_views.show_distribution(processed, display_unit)
        self._set_export_availability()
        if np.isfinite(processed.values).any():
            self.statusBar().showMessage("Map reconstructed.")
        else:
            self.statusBar().showMessage("Raw map reconstructed; no finite processed values.")

    def _invalidate_reconstruction(self, message: str) -> None:
        self.result = None
        self.params = None
        self.processed = None
        self._active_color_limits = None
        self.inspector.clear_qc(message)
        self.map_views.clear_processed_views(message)
        self.trace_view.clear_guides()
        self._set_export_availability()
        self.statusBar().showMessage(message)

    def _update_guides(self, result: ReconstructionResult) -> None:
        if self.data is None or self.params is None:
            return
        timing = result.timing
        t_min, t_max = float(self.data.time_s[0]), float(self.data.time_s[-1])
        rows = timing.row_ref0_s + np.arange(self.params.rows) * timing.row_period_s
        row_index = int(np.floor((self.params.point_a_s - timing.row_ref0_s) / timing.row_period_s))
        row_base = timing.row_ref0_s + row_index * timing.row_period_s
        pixels = (
            row_base + timing.pixel1_phase_s + np.arange(self.params.cols) * timing.point_period_s
        )
        self.trace_view.set_guides(
            rows[(rows >= t_min) & (rows <= t_max)],
            pixels[(pixels >= t_min) & (pixels <= t_max)],
        )

    def _reset_views(self) -> None:
        self.trace_view.reset_view()
        self.map_views.reset_views()

    def _export_raw_map(self) -> None:
        export_raw(self)

    def _processed_export_metadata(self) -> dict[str, object]:
        return processed_export_metadata(self)

    def _export_processed_map(self) -> None:
        export_processed(self)

    def _export_both_maps(self) -> None:
        export_both(self)

    def _export_map(self) -> None:
        self._export_raw_map()


def run_app(path: Path | None = None) -> int:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    window = MapReconstructionWindow(path)
    window.show()
    return app.exec()
