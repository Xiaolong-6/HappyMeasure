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
from map_reconstruction.importers.happymeasure import import_happymeasure_csv_bytes
from map_reconstruction.methods.dual_offset import reconstruct_map
from map_reconstruction.methods.phase_window import (
    convert_legacy_to_phase_window,
    effective_window_bounds,
    reconstruct_phase_window_map,
)
from map_reconstruction.models import (
    Aggregation,
    DualOffsetParams,
    PhaseWindowParams,
    PhaseWindowTimingSolution,
    ReconstructionResult,
    ScanPattern,
    TimeSeriesData,
    TimingSolution,
    WindowMode,
)
from map_reconstruction.processing import (
    MapProcessingConfig,
    NormalizationMode,
    ProcessedMap,
    ValueScale,
    ValueTransform,
    compute_color_limits,
    process_map,
)
from map_reconstruction.project_io import ProjectState, load_project
from map_reconstruction.preparation import PreparedSignal, SignalPreparationConfig, prepare_signal
from map_reconstruction.ui.exporting import (
    export_both,
    export_html_report,
    export_parameter_summary,
    export_prepared,
    export_processed,
    export_project,
    export_raw,
    processed_export_metadata,
)
from map_reconstruction.ui.inspector import ReconstructionInspector
from map_reconstruction.ui.map_views import MapViews
from map_reconstruction.ui.style import apply_light_theme
from map_reconstruction.ui.trace_view import MAX_GUIDES_PER_FAMILY, TraceView  # noqa: F401
from map_reconstruction.ui.analysis_page import MapAnalysisPage
from map_reconstruction.ui.preparation_page import SignalPreparationPage
from map_reconstruction.ui.workflow_header import WorkflowHeader


class MapReconstructionWindow(QtWidgets.QMainWindow):
    """Coordinate file lifecycle, reconstruction, processing, and view updates."""

    params: DualOffsetParams | PhaseWindowParams | None
    processing_config: MapProcessingConfig | None
    signal_combo: QtWidgets.QComboBox
    scan_combo: QtWidgets.QComboBox
    flip_y_check: QtWidgets.QCheckBox
    first_row_check: QtWidgets.QCheckBox
    aggregation_combo: QtWidgets.QComboBox
    rows_spin: QtWidgets.QSpinBox
    cols_spin: QtWidgets.QSpinBox
    row_a_spin: QtWidgets.QDoubleSpinBox
    row_b_spin: QtWidgets.QDoubleSpinBox
    rows_apart_spin: QtWidgets.QSpinBox
    row_offset_spin: QtWidgets.QSpinBox
    point_a_spin: QtWidgets.QDoubleSpinBox
    point_b_spin: QtWidgets.QDoubleSpinBox
    points_apart_spin: QtWidgets.QSpinBox
    point_offset_spin: QtWidgets.QSpinBox
    method_combo: QtWidgets.QComboBox
    x_period_offset_spin: QtWidgets.QSpinBox
    y_phase_spin: QtWidgets.QDoubleSpinBox
    x_phase_spin: QtWidgets.QDoubleSpinBox
    window_mode_combo: QtWidgets.QComboBox
    window_fraction_spin: QtWidgets.QDoubleSpinBox
    window_duration_spin: QtWidgets.QDoubleSpinBox
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
        self.preparation_config = SignalPreparationConfig()
        self.prepared: PreparedSignal | None = None
        self._active_color_limits: tuple[float, float] | None = None
        self._loaded_filename: str | None = None
        self._raw_source_bytes: bytes | None = None
        self._restoring_project = False
        self._syncing = False
        self.setWindowTitle("Map Reconstruction")
        self.setMinimumSize(0, 0)
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
        self.workflow_header = WorkflowHeader(self)
        root.addWidget(self.workflow_header)
        self.workflow_stack = QtWidgets.QStackedWidget()
        root.addWidget(self.workflow_stack, 1)
        self.setCentralWidget(central)

        self.preparation_page = SignalPreparationPage(self)
        self.analysis_page = MapAnalysisPage(self)
        self.workflow_stack.addWidget(self.preparation_page)

        reconstruction_page = QtWidgets.QWidget()
        reconstruction_layout = QtWidgets.QVBoxLayout(reconstruction_page)
        reconstruction_layout.setContentsMargins(0, 0, 0, 0)
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        reconstruction_layout.addWidget(splitter)
        self.workflow_stack.addWidget(reconstruction_page)
        self.workflow_stack.addWidget(self.analysis_page)

        self.inspector = ReconstructionInspector(self)
        # Stage 2 is reconstruction-only. Stage 3 creates and owns its live
        # processing controls; no widget is reparented between scientific stages.
        self.inspector.data_section.hide()
        self.inspector.processing_section.hide()
        self.inspector.flip_y_check.hide()
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.inspector)
        scroll.setMinimumWidth(340)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        splitter.addWidget(scroll)

        right = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self.map_views = MapViews(self)
        self.analysis_map_views = MapViews(self, presentation="analysis")
        self.analysis_page.attach_views(self.analysis_map_views)
        self.trace_view = TraceView(parent=self)
        right.addWidget(self.map_views)
        right.addWidget(self.trace_view)
        right.setStretchFactor(0, 45)
        right.setStretchFactor(1, 55)
        right.setSizes([360, 440])
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([340, 840])

        self._expose_compatibility_attributes()
        self.preparation_page.signal_combo.currentTextChanged.connect(self._signal_changed)
        self.preparation_page.configurationChanged.connect(self._preparation_changed)
        self.analysis_page.displayChanged.connect(self._display_changed)
        self.preparation_page.exportRequested.connect(lambda: export_prepared(self))
        self.preparation_page.openCsvRequested.connect(self._choose_file)
        self.preparation_page.openProjectRequested.connect(self._choose_project)
        self.workflow_header.stageSelected.connect(self._select_stage)
        self.inspector.geometryChanged.connect(self._reconstruct)
        self.inspector.registrationChanged.connect(self._reconstruct)
        self.inspector.convertPhaseWindowRequested.connect(self._convert_legacy_to_phase_window)
        self.analysis_page.processingChanged.connect(self._processing_controls_changed)
        self.analysis_page.colorLimitsChanged.connect(self._color_limits_changed)
        self.analysis_page.exportProcessedRequested.connect(self._export_processed_map)
        self.analysis_page.exportSummaryRequested.connect(self._export_parameter_summary)
        self.analysis_page.exportPdfRequested.connect(self._export_html_report)
        self.analysis_page.saveProjectRequested.connect(self._export_project)
        self.map_views.distributionControlsChanged.connect(self._distribution_controls_changed)
        self.map_views.useMapLimitsRequested.connect(self._use_map_limits_for_distribution)
        self.analysis_map_views.distributionControlsChanged.connect(
            self._distribution_controls_changed
        )
        self.analysis_map_views.useMapLimitsRequested.connect(self._use_map_limits_for_distribution)
        self.inspector.pointPeriodEdited.connect(self._point_period_edited)
        self.trace_view.resetViewRequested.connect(self._reset_views)
        self.trace_view.traceSourceChanged.connect(
            lambda _source: self.trace_view._refresh_trace_curve()
        )
        self.inspector.openRequested.connect(self._choose_file)
        self.inspector.openProjectRequested.connect(self._choose_project)
        self.inspector.exportRawRequested.connect(self._export_raw_map)
        self.inspector.exportProcessedRequested.connect(self._export_processed_map)
        self.inspector.exportBothRequested.connect(self._export_both_maps)
        self.inspector.exportProjectRequested.connect(self._export_project)
        self.inspector.exportSummaryRequested.connect(self._export_parameter_summary)
        self.inspector.exportPdfRequested.connect(self._export_html_report)
        self.trace_view.anchorMoved.connect(self._anchor_moved)
        self.trace_view.anchorMoveFinished.connect(self._anchor_finished)
        self._set_loaded_view(False)

    def _select_stage(self, index: int) -> None:
        self.workflow_stack.setCurrentIndex(max(0, min(index, self.workflow_stack.count() - 1)))

    def _display_changed(self, *_args: object) -> None:
        """Refresh figure state without touching reconstruction or processing."""

        if self.sender() is self.analysis_page.flip_y_check:
            blocker = QtCore.QSignalBlocker(self.flip_y_check)
            self.flip_y_check.setChecked(self.analysis_page.flip_y_check.isChecked())
            del blocker
        elif self.analysis_page.flip_y_check.isChecked() != self.flip_y_check.isChecked():
            blocker = QtCore.QSignalBlocker(self.analysis_page.flip_y_check)
            self.analysis_page.flip_y_check.setChecked(self.flip_y_check.isChecked())
            del blocker
        palette = self.analysis_page.palette_combo.currentText()
        inverted = self.analysis_page.invert_palette_check.isChecked()
        self.map_views.set_palette(palette, inverted=inverted)
        self.analysis_map_views.set_palette(palette, inverted=inverted)
        if self.processed is not None:
            self._refresh_processed_display()
            self._update_distribution()
        if self.result is not None:
            flipped = self.flip_y_check.isChecked()
            self.map_views.show_sample_counts(self.result.sample_counts, flipped)
            self.analysis_map_views.show_sample_counts(self.result.sample_counts, flipped)

    def _sync_preparation_controls(self, config: SignalPreparationConfig) -> None:
        self.preparation_page.set_configuration(config)

    def _preparation_changed(self) -> None:
        if self._restoring_project or self.data is None:
            return
        try:
            self.preparation_config = self.preparation_page.configuration()
            self.prepared = prepare_signal(
                self.data, self.signal_combo.currentText(), self.preparation_config
            )
            self.preparation_page.set_prepared(self.prepared)
            self.trace_view.set_prepared_signal(self.prepared.values)
            self.preparation_page.set_diagnostics(
                f"Samples: {self.prepared.sample_count}\n"
                f"Baseline: {('none' if self.prepared.baseline is None else f'{self.prepared.baseline[0]:.6g} → {self.prepared.baseline[-1]:.6g}')}\n"
                + (
                    "; ".join(self.prepared.warnings)
                    if self.prepared.warnings
                    else "Prepared signal ready."
                )
            )
        except ValueError as exc:
            self.prepared = None
            self.preparation_page.set_prepared(None)
            self._invalidate_reconstruction(str(exc))
            self.preparation_page.set_diagnostics(str(exc))
            self.workflow_header.set_status(False, False, False)
            return
        self._reconstruct()

    def _expose_compatibility_attributes(self) -> None:
        """Keep the small existing UI regression surface stable during the split."""

        inspector_names = (
            "file_label",
            "open_button",
            "open_project_button",
            "export_button",
            "raw_export_action",
            "processed_export_action",
            "both_export_action",
            "project_export_action",
            "summary_export_action",
            "pdf_export_action",
            "signal_combo",
            "rows_spin",
            "cols_spin",
            "scan_combo",
            "first_row_check",
            "flip_y_check",
            "aggregation_combo",
            "row_a_spin",
            "row_b_spin",
            "rows_apart_spin",
            "row_offset_spin",
            "point_a_spin",
            "point_b_spin",
            "points_apart_spin",
            "point_period_spin",
            "point_offset_spin",
            "method_combo",
            "x_period_offset_spin",
            "y_phase_spin",
            "x_phase_spin",
            "window_mode_combo",
            "window_fraction_spin",
            "window_duration_spin",
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
        for name in (
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
            "flip_y_check",
        ):
            setattr(self, name, getattr(self.analysis_page, name))
        # The visible Preparation selector is the sole source-signal authority.
        self.signal_combo = self.preparation_page.signal_combo
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
            "qc_splitter",
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

    def _choose_project(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open Map Reconstruction project",
            "",
            "Map Reconstruction Project (*.hmmap)",
        )
        if path:
            self.load_project_file(Path(path))

    def load_file(self, path: Path) -> None:
        try:
            raw_bytes = path.read_bytes()
            data = import_happymeasure_csv_bytes(raw_bytes, path.name, source_path=path)
        except (OSError, ValueError) as exc:
            QtWidgets.QMessageBox.critical(self, "Could not open CSV", str(exc))
            return
        self._load_data(data, raw_bytes, path.name)

    def load_project_file(self, path: Path) -> None:
        try:
            loaded = load_project(path)
            data = import_happymeasure_csv_bytes(
                loaded.raw_csv_bytes,
                loaded.state.original_filename,
                source_path=Path(loaded.state.original_filename),
            )
            if loaded.state.signal not in data.signals:
                raise ValueError(f"Project source signal {loaded.state.signal!r} is unavailable.")
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            QtWidgets.QMessageBox.critical(self, "Could not open project", str(exc))
            return
        self._restoring_project = True
        try:
            self._load_data(
                data, loaded.raw_csv_bytes, loaded.state.original_filename, reconstruct=False
            )
            project_unit = display_unit_for_signal(
                loaded.state.signal, data.signals[loaded.state.signal]
            )
            self.inspector.restore_project_state(loaded.state, project_unit.scale)
            self.analysis_page.set_processing_config(loaded.state.processing, project_unit.scale)
            self.analysis_page.flip_y_check.setChecked(loaded.state.flip_y)
            self.preparation_config = loaded.state.preparation
            self._sync_preparation_controls(self.preparation_config)
            self.preparation_page.signal_combo.setCurrentText(loaded.state.signal)
            self.prepared = prepare_signal(data, loaded.state.signal, self.preparation_config)
            self.preparation_page.set_prepared(self.prepared)
            self.trace_view.set_prepared_signal(self.prepared.values)
            self._set_raw_signal(loaded.state.signal)
            self._update_processing_units()
            self._create_anchor_lines()
        finally:
            self._restoring_project = False
        if loaded.state.is_geometry_set:
            self._reconstruct()
        else:
            self._set_export_availability()
            self.statusBar().showMessage("Project opened. Set Rows and Columns to reconstruct.")

    def _load_data(
        self,
        data: TimeSeriesData,
        raw_bytes: bytes,
        original_filename: str,
        *,
        reconstruct: bool = True,
    ) -> None:
        self.data = data
        self.result = None
        self.params = None
        self.processed = None
        self._active_color_limits = None
        self._raw_source_bytes = raw_bytes
        self._loaded_filename = original_filename
        self._clear_reconstruction_outputs()
        self.workflow_header.set_filename(original_filename)
        self.inspector.set_file_name(original_filename)
        preferred = "Current_A" if "Current_A" in data.signals else data.signal_names[-1]
        self.inspector.set_signal_names(data.signal_names, preferred)
        self.preparation_page.set_signals(data.signal_names, preferred)
        self.preparation_config = SignalPreparationConfig()
        self._sync_preparation_controls(self.preparation_config)
        self.analysis_page.flip_y_check.setChecked(False)
        self.prepared = prepare_signal(data, preferred, self.preparation_config)
        self.preparation_page.set_source(data.time_s, data.signals[preferred])
        self.preparation_page.set_prepared(self.prepared)
        self.trace_view.set_prepared_signal(self.prepared.values)
        self.workflow_header.set_status(True, False, False)
        self._set_anchor_bounds(data)
        self._set_raw_signal(preferred)
        self._update_processing_units()
        self._create_anchor_lines()
        self._set_loaded_view(True)
        # Loading a source without valid geometry must not expose the previous
        # map/count images while the new source waits for reconstruction.
        self._clear_reconstruction_outputs()
        if reconstruct:
            self._reconstruct()
        if reconstruct and (self.rows_spin.value() <= 0 or self.cols_spin.value() <= 0):
            self.statusBar().showMessage("Set Rows and Columns to reconstruct.")

    def _set_loaded_view(self, loaded: bool) -> None:
        self.map_views.set_loaded(loaded)
        self.analysis_map_views.set_loaded(loaded)
        self.trace_view.show_loaded(loaded)
        self._set_export_availability()

    def _clear_reconstruction_outputs(self) -> None:
        """Remove derived output from the previous source before a reload."""
        self.map_views.clear_processed_views("No reconstruction yet")
        self.analysis_map_views.clear_processed_views("No processed map available")
        self.trace_view.clear_guides()
        self.inspector.clear_qc("Reconstruction unavailable until the new source is ready.")

    def _set_export_availability(self) -> None:
        raw_available = self.result is not None
        processed_available = bool(
            self.processed is not None and np.isfinite(self.processed.values).any()
        )
        source_available = self.data is not None and bool(self._raw_source_bytes)
        self.inspector.set_export_availability(raw_available, processed_available, source_available)
        self.analysis_page.set_export_availability(
            source_available=source_available,
            raw_available=raw_available,
            processed_available=processed_available,
        )

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
        if self.inspector.signal_combo.currentText() != signal_name:
            self.inspector.signal_combo.blockSignals(True)
            self.inspector.signal_combo.setCurrentText(signal_name)
            self.inspector.signal_combo.blockSignals(False)
        if self.preparation_page.signal_combo.currentText() != signal_name:
            self.preparation_page.signal_combo.blockSignals(True)
            self.preparation_page.signal_combo.setCurrentText(signal_name)
            self.preparation_page.signal_combo.blockSignals(False)
        try:
            self.prepared = prepare_signal(self.data, signal_name, self.preparation_config)
            self.preparation_page.set_source(self.data.time_s, self.data.signals[signal_name])
            self.preparation_page.set_prepared(self.prepared)
            self.trace_view.set_prepared_signal(self.prepared.values)
        except ValueError as exc:
            self.prepared = None
            self.preparation_page.set_prepared(None)
            self._invalidate_reconstruction(str(exc))
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
        return self.analysis_page.current_processing_config(
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
        self.analysis_page.set_processing_units(
            raw,
            normalization_reference,
            DisplayUnit(raw.label, "", 1.0) if dimensionless else raw,
        )

    def _processing_controls_changed(self) -> None:
        self._update_processing_units()
        if self.result is not None:
            self._process_and_display()

    def _color_limits_changed(self) -> None:
        """Remap colors only; the processed scientific array remains untouched."""

        config = self._processing_config()
        self.processing_config = config
        if self.processed is not None:
            self._refresh_processed_display(config)

    def _refresh_processed_display(self, config: MapProcessingConfig | None = None) -> None:
        if self.processed is None:
            return
        config = config or self._processing_config()
        self.processing_config = config
        display_unit = self._current_display_unit()
        try:
            limits = compute_color_limits(self.processed.values, config)
        except ValueError as exc:
            self._active_color_limits = None
            self.map_views.show_empty_map("Invalid color limits", str(exc))
            self.inspector.set_warning(str(exc))
            return
        if limits is None:
            self._active_color_limits = None
            self.map_views.show_empty_map(
                "No finite processed values", "Adjust processing settings."
            )
            return
        display_limits = (limits.minimum * display_unit.scale, limits.maximum * display_unit.scale)
        self._active_color_limits = display_limits
        self.map_views.show_processed_map(
            self.processed.values,
            display_unit,
            display_limits,
            self.flip_y_check.isChecked(),
            display_unit.axis_label,
        )
        self.analysis_map_views.show_processed_map(
            self.processed.values,
            display_unit,
            display_limits,
            self.flip_y_check.isChecked(),
            display_unit.axis_label,
        )

    def _distribution_controls_changed(self) -> None:
        """Refresh only the QC histogram; its controls never reprocess a map."""

        if self.processed is not None:
            self._update_distribution()

    def _use_map_limits_for_distribution(self) -> None:
        if self._active_color_limits is None:
            self.map_views.show_distribution_error("Map color limits are not available.")
            return
        self.map_views.set_manual_distribution_range(*self._active_color_limits)
        self.analysis_map_views.set_manual_distribution_range(*self._active_color_limits)

    def _update_distribution(self) -> None:
        if self.processed is None:
            return
        display_unit = self._current_display_unit()
        try:
            config = self.map_views.histogram_config(display_unit.scale)
            self.map_views.show_distribution(self.processed, display_unit, config)
            self.analysis_map_views.show_distribution(self.processed, display_unit, config)
        except ValueError as exc:
            self.map_views.show_distribution_error(str(exc))
            self.analysis_map_views.show_distribution_error(str(exc))

    def _reconstruct(self) -> None:
        if self.data is None or self._syncing or self._restoring_project:
            return
        if self.prepared is None:
            # Keep the existing headless/UI compatibility surface usable for
            # callers that inject ``data`` directly (the identity preparation
            # is numerically identical to the legacy raw path).
            try:
                self.prepared = prepare_signal(
                    self.data, self.signal_combo.currentText(), self.preparation_config
                )
            except ValueError:
                self._invalidate_reconstruction("Signal preparation is unavailable.")
                return
        if self.rows_spin.value() <= 0 or self.cols_spin.value() <= 0:
            self._invalidate_reconstruction("Set Rows and Columns to reconstruct.")
            return
        if self.inspector.initialize_geometry_aware_anchors(self.data):
            self._create_anchor_lines()
        try:
            params = self.inspector.current_params()
            reconstruction_data = TimeSeriesData(
                self.prepared.time_s,
                {self.prepared.source_signal: self.prepared.values},
                metadata={"prepared": True},
            )
            result = (
                reconstruct_phase_window_map(
                    reconstruction_data, self.prepared.source_signal, params
                )
                if isinstance(params, PhaseWindowParams)
                else reconstruct_map(reconstruction_data, self.prepared.source_signal, params)
            )
        except ValueError as exc:
            self._invalidate_reconstruction(str(exc))
            return
        self.params = params
        finite = np.isfinite(result.values)
        self.inspector.set_timing_solution(
            result.timing.row_period_s,
            result.timing.point_period_s,
            result.timing.row_period_s - params.cols * result.timing.point_period_s,
            phase_window=isinstance(params, PhaseWindowParams),
        )
        nonzero_counts = result.sample_counts[finite]
        self.inspector.set_qc(
            100.0 * float(np.mean(finite)),
            float(np.median(nonzero_counts)) if np.any(finite) else 0.0,
            100.0 * float(np.mean(result.sample_counts == 0)),
            100.0 * float(np.mean(result.sample_counts == 1)),
            float(np.percentile(nonzero_counts, 10.0)) if np.any(finite) else 0.0,
        )
        if not np.any(finite):
            self.result = None
            self.processed = None
            self._active_color_limits = None
            message = "No valid pixels for current timing."
            self.inspector.set_warning(" | ".join([message, *result.warnings]))
            self.map_views.clear_processed_views("No valid reconstructed pixels")
            self.analysis_map_views.clear_processed_views("No valid reconstructed pixels")
            self.map_views.show_sample_counts(result.sample_counts, self.flip_y_check.isChecked())
            self.analysis_map_views.show_sample_counts(
                result.sample_counts, self.flip_y_check.isChecked()
            )
            self.trace_view.clear_guides()
            self._set_export_availability()
            self.statusBar().showMessage(message)
            return
        self.result = result
        self.workflow_header.set_status(self.prepared is not None, True, self.processed is not None)
        self._process_and_display()
        self.map_views.show_sample_counts(result.sample_counts, self.flip_y_check.isChecked())
        self.analysis_map_views.show_sample_counts(
            result.sample_counts, self.flip_y_check.isChecked()
        )
        self._update_guides(result)
        self._set_export_availability()

    def _convert_legacy_to_phase_window(self) -> None:
        """Explicitly convert only if the current raw reconstruction is identical."""

        if self.data is None:
            return
        try:
            legacy = self.inspector.current_params()
            if not isinstance(legacy, DualOffsetParams):
                return
            conversion = convert_legacy_to_phase_window(legacy)
            reconstruction_data = TimeSeriesData(
                self.prepared.time_s if self.prepared is not None else self.data.time_s,
                {
                    self.signal_combo.currentText(): (
                        self.prepared.values
                        if self.prepared is not None
                        else self.data.signals[self.signal_combo.currentText()]
                    )
                },
            )
            legacy_result = reconstruct_map(
                reconstruction_data, self.signal_combo.currentText(), legacy
            )
            phase_result = reconstruct_phase_window_map(
                reconstruction_data, self.signal_combo.currentText(), conversion.params
            )
            if not (
                np.array_equal(legacy_result.sample_counts, phase_result.sample_counts)
                and np.allclose(legacy_result.values, phase_result.values, equal_nan=True)
            ):
                raise ValueError("Conversion could not reproduce the current Legacy pixel windows.")
        except ValueError as exc:
            self.inspector.set_warning(str(exc))
            self.statusBar().showMessage("Legacy conversion was not applied.")
            return
        widgets = (
            self.method_combo,
            self.y_phase_spin,
            self.x_period_offset_spin,
            self.x_phase_spin,
            self.window_mode_combo,
            self.window_fraction_spin,
        )
        blockers = [QtCore.QSignalBlocker(widget) for widget in widgets]
        try:
            self.method_combo.setCurrentIndex(
                self.method_combo.findData("dual_offset_phase_window")
            )
            self.y_phase_spin.setValue(conversion.params.y_phase_fraction * 100.0)
            self.x_period_offset_spin.setValue(conversion.params.x_period_offset)
            self.x_phase_spin.setValue(conversion.params.x_phase_fraction * 100.0)
            self.window_mode_combo.setCurrentIndex(
                self.window_mode_combo.findData(conversion.params.window_mode)
            )
            self.window_fraction_spin.setValue(conversion.params.window_fraction * 100.0)
        finally:
            del blockers
        self.inspector._update_phase_window_fields()
        self._reconstruct()
        self.statusBar().showMessage(
            "Converted Legacy timing to Phase Window without changing pixels."
        )

    def _process_and_display(self) -> None:
        if self.result is None or self.data is None:
            return
        try:
            config = self._processing_config()
            processed = process_map(self.result.values, config, self.signal_combo.currentText())
        except ValueError as exc:
            self.processed = None
            self._active_color_limits = None
            self.map_views.clear_processed_map_and_distribution("Processing unavailable")
            self.analysis_map_views.clear_processed_map_and_distribution("Processing unavailable")
            self.inspector.set_warning(str(exc))
            self._set_export_availability()
            self.statusBar().showMessage("Raw map reconstructed; processing unavailable.")
            return
        self.processing_config = config
        self.processed = processed
        self.workflow_header.set_status(self.prepared is not None, self.result is not None, True)
        self.inspector.set_processing_summary(
            f"{processed.value_label} - {config.value_scale.value}"
            + (f" - {len(processed.warnings)} warning(s)" if processed.warnings else "")
        )
        self.inspector.set_warning(" | ".join([*self.result.warnings, *processed.warnings]))
        self._refresh_processed_display()
        self._update_distribution()
        self._set_export_availability()
        if np.isfinite(processed.values).any():
            self.statusBar().showMessage("Map reconstructed.")
        else:
            self.statusBar().showMessage("Raw map reconstructed; no finite processed values.")

    def _invalidate_reconstruction(
        self, message: str, *, analysis_message: str | None = None
    ) -> None:
        self.result = None
        self.params = None
        self.processed = None
        self._active_color_limits = None
        self.inspector.clear_qc(message)
        self.map_views.clear_processed_views(message)
        self.analysis_map_views.clear_processed_views(analysis_message or message)
        self.trace_view.clear_guides()
        self._set_export_availability()
        self.statusBar().showMessage(message)
        self.workflow_header.set_status(self.prepared is not None, False, False)

    def _update_guides(self, result: ReconstructionResult) -> None:
        if self.data is None or self.params is None:
            return
        timing = result.timing
        t_min, t_max = float(self.data.time_s[0]), float(self.data.time_s[-1])
        if isinstance(self.params, PhaseWindowParams):
            assert isinstance(timing, PhaseWindowTimingSolution)
            rows = timing.row0_s + np.arange(self.params.rows) * timing.row_period_s
            bounds = effective_window_bounds(self.params, timing)
            self.trace_view.set_phase_window_guides(
                rows[(rows >= t_min) & (rows <= t_max)],
                bounds,
                self.prepared.time_s if self.prepared is not None else self.data.time_s,
                (
                    self.prepared.values
                    if self.prepared is not None
                    else self.data.signals[self.signal_combo.currentText()]
                ),
                self._raw_display_unit(),
            )
            return
        assert isinstance(timing, TimingSolution)
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

    def _export_raw_map(self) -> None:
        export_raw(self)

    def _processed_export_metadata(self) -> dict[str, object]:
        return processed_export_metadata(self)

    def _export_processed_map(self) -> None:
        export_processed(self)

    def _export_both_maps(self) -> None:
        export_both(self)

    def _project_state(self) -> ProjectState:
        config = self._processing_config()
        return ProjectState(
            original_filename=self._loaded_filename or "measurement.csv",
            signal=self.signal_combo.currentText(),
            rows=self.rows_spin.value(),
            columns=self.cols_spin.value(),
            scan_pattern=ScanPattern(self.scan_combo.currentData()),
            first_row_ltr=self.first_row_check.isChecked(),
            aggregation=Aggregation(self.aggregation_combo.currentData()).value,
            row_a_s=self.row_a_spin.value(),
            row_b_s=self.row_b_spin.value(),
            rows_apart=self.rows_apart_spin.value(),
            row_offset=self.row_offset_spin.value(),
            point_a_s=self.point_a_spin.value(),
            point_b_s=self.point_b_spin.value(),
            points_apart=self.points_apart_spin.value(),
            point_offset=self.point_offset_spin.value(),
            processing=config,
            flip_y=self.flip_y_check.isChecked(),
            method=self.method_combo.currentData(),
            y_phase_fraction=self.y_phase_spin.value() / 100.0,
            x_period_offset=self.x_period_offset_spin.value(),
            x_phase_fraction=self.x_phase_spin.value() / 100.0,
            window_mode=self.window_mode_combo.currentData(),
            window_fraction=self.window_fraction_spin.value() / 100.0,
            window_duration_s=(
                self.window_duration_spin.value()
                if WindowMode(self.window_mode_combo.currentData()) is WindowMode.FIXED_DURATION
                else None
            ),
            preparation=self.preparation_config,
        )

    def _export_project(self) -> None:
        export_project(self)

    def _export_parameter_summary(self) -> None:
        export_parameter_summary(self)

    def _export_html_report(self) -> None:
        export_html_report(self)

    def _export_map(self) -> None:
        self._export_raw_map()


def run_app(path: Path | None = None) -> int:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    window = MapReconstructionWindow(path)
    window.show()
    return app.exec()
