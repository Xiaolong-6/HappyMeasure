from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np

try:
    import pyqtgraph as pg  # type: ignore[import-not-found, import-untyped]
    from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore[import-not-found]
except ImportError as exc:  # pragma: no cover - optional GUI dependency
    raise ImportError("PySide6 and pyqtgraph are required for the Map Reconstruction UI") from exc

from map_reconstruction.display_units import (
    DisplayUnit,
    display_unit_for_signal,
    format_display_value,
    to_display_values,
)
from map_reconstruction.importers.happymeasure import import_happymeasure_csv
from map_reconstruction.methods.dual_offset import reconstruct_map
from map_reconstruction.models import (
    DualOffsetParams,
    ReconstructionResult,
    ScanPattern,
    TimeSeriesData,
)
from map_reconstruction.processing import (
    BaselineMode,
    ColorRangeMode,
    MapProcessingConfig,
    NormalizationMode,
    ProcessedMap,
    ValueScale,
    ValueTransform,
    compute_color_limits,
    process_map,
)
from map_reconstruction.qc.distribution import make_histogram_data
from map_reconstruction.ui.style import (
    BORDER,
    GRID_MAJOR,
    PANEL,
    PRIMARY_TEXT,
    SECONDARY_TEXT,
    TRACE,
    apply_light_theme,
)

MAX_GUIDES_PER_FAMILY = 500


class MapReconstructionWindow(QtWidgets.QMainWindow):
    """Resizable timing, trace, and map workspace for v1 reconstruction."""

    def __init__(self, initial_path: Path | None = None) -> None:
        super().__init__()
        application = QtWidgets.QApplication.instance()
        if isinstance(application, QtWidgets.QApplication):
            apply_light_theme(application)
        pg.setConfigOption("imageAxisOrder", "row-major")
        self.data: TimeSeriesData | None = None
        self.result: ReconstructionResult | None = None
        self.params: DualOffsetParams | None = None
        self.processed: ProcessedMap | None = None
        self.processing_config = MapProcessingConfig()
        self._active_color_limits: tuple[float, float] | None = None
        self._loaded_filename: str | None = None
        self.anchor_lines: dict[str, pg.InfiniteLine] = {}
        self.guide_items: list[pg.InfiniteLine] = []
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
        root_layout = QtWidgets.QVBoxLayout(central)
        root_layout.setContentsMargins(16, 14, 16, 10)
        root_layout.setSpacing(12)
        self._build_header(root_layout)
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        root_layout.addWidget(splitter)
        root_layout.setStretch(1, 1)
        self.setCentralWidget(central)

        controls = QtWidgets.QWidget()
        controls_layout = QtWidgets.QVBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 8, 0)
        controls_layout.setSpacing(10)

        data_section, data_layout = self._inspector_section("DATA")
        self.file_label = QtWidgets.QLabel("No file loaded")
        self.file_label.setObjectName("fileLabel")
        self.file_label.setWordWrap(False)
        self.file_label.setToolTip("No file loaded")
        data_layout.addWidget(self.file_label)
        data_form = QtWidgets.QFormLayout()
        data_form.setContentsMargins(0, 3, 0, 0)
        data_form.setHorizontalSpacing(12)
        data_form.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        data_form.setRowWrapPolicy(QtWidgets.QFormLayout.RowWrapPolicy.WrapLongRows)
        self.signal_combo = QtWidgets.QComboBox()
        self.signal_combo.currentTextChanged.connect(self._signal_changed)
        self._add_form_row(data_form, "Signal", self.signal_combo)
        data_layout.addLayout(data_form)
        controls_layout.addWidget(data_section)

        geometry_section, geometry_layout = self._inspector_section("GEOMETRY")
        geometry_form = QtWidgets.QFormLayout()
        geometry_form.setContentsMargins(0, 0, 0, 0)
        geometry_form.setHorizontalSpacing(12)
        geometry_form.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        geometry_form.setRowWrapPolicy(QtWidgets.QFormLayout.RowWrapPolicy.WrapLongRows)
        self.rows_spin = self._int_spin(36, 1, 10000)
        self.cols_spin = self._int_spin(36, 1, 10000)
        self._add_form_row(geometry_form, "Rows", self.rows_spin)
        self._add_form_row(geometry_form, "Columns", self.cols_spin)
        self.scan_combo = QtWidgets.QComboBox()
        self.scan_combo.addItem("Same direction", ScanPattern.SAME_DIRECTION)
        self.scan_combo.addItem("Serpentine", ScanPattern.SERPENTINE)
        self._add_form_row(geometry_form, "Scan pattern", self.scan_combo)
        self.first_row_check = QtWidgets.QCheckBox("First row L → R")
        self.first_row_check.setChecked(True)
        self._add_form_row(geometry_form, "Orientation", self.first_row_check)
        self.flip_y_check = QtWidgets.QCheckBox("Flip Y display")
        self._add_form_row(geometry_form, "Display", self.flip_y_check)
        self.median_check = QtWidgets.QCheckBox("Median / pixel")
        self.median_check.setChecked(True)
        self._add_form_row(geometry_form, "Aggregation", self.median_check)
        geometry_layout.addLayout(geometry_form)
        controls_layout.addWidget(geometry_section)

        registration_section, registration_layout = self._inspector_section("REGISTRATION")
        method_row = QtWidgets.QHBoxLayout()
        method_label = QtWidgets.QLabel("Method")
        method_label.setObjectName("fieldLabel")
        method_value = QtWidgets.QLabel("Dual Offset")
        method_value.setObjectName("methodValue")
        method_row.addWidget(method_label)
        method_row.addStretch(1)
        method_row.addWidget(method_value)
        registration_layout.addLayout(method_row)
        registration_layout.addSpacing(4)

        self.row_a_spin = self._float_spin()
        self.row_b_spin = self._float_spin()
        self.point_a_spin = self._float_spin()
        self.point_b_spin = self._float_spin()
        self.rows_apart_spin = self._int_spin(10, 1, 100000)
        self.row_offset_spin = self._int_spin(0, 0, 100000)
        self.points_apart_spin = self._int_spin(10, 1, 100000)
        self.point_period_spin = self._float_spin()
        self.point_period_spin.setRange(1e-12, 1e15)
        self.point_offset_spin = self._int_spin(0, 0, 100000)
        self.row_offset_slider = self._offset_slider()
        self.point_offset_slider = self._offset_slider()
        row_offset_control = QtWidgets.QWidget()
        row_offset_layout = QtWidgets.QHBoxLayout(row_offset_control)
        row_offset_layout.setContentsMargins(0, 0, 0, 0)
        row_offset_layout.addWidget(self.row_offset_spin)
        row_offset_layout.addWidget(self.row_offset_slider)
        point_offset_control = QtWidgets.QWidget()
        point_offset_layout = QtWidgets.QHBoxLayout(point_offset_control)
        point_offset_layout.setContentsMargins(0, 0, 0, 0)
        point_offset_layout.addWidget(self.point_offset_spin)
        point_offset_layout.addWidget(self.point_offset_slider)
        row_timing = QtWidgets.QFormLayout()
        row_timing.setContentsMargins(0, 0, 0, 0)
        row_timing.setHorizontalSpacing(12)
        row_timing.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        row_timing.setRowWrapPolicy(QtWidgets.QFormLayout.RowWrapPolicy.WrapLongRows)
        row_header = self._subsection_header("ROW TIMING")
        registration_layout.addWidget(row_header)
        self._add_form_row(row_timing, "Row A", self.row_a_spin)
        self._add_form_row(row_timing, "Row B", self.row_b_spin)
        self._add_form_row(row_timing, "Rows apart", self.rows_apart_spin)
        self._add_form_row(row_timing, "Row offset", row_offset_control)
        registration_layout.addLayout(row_timing)
        registration_layout.addSpacing(7)
        point_header = self._subsection_header("POINT TIMING")
        registration_layout.addWidget(point_header)
        point_timing = QtWidgets.QFormLayout()
        point_timing.setContentsMargins(0, 0, 0, 0)
        point_timing.setHorizontalSpacing(12)
        point_timing.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        point_timing.setRowWrapPolicy(QtWidgets.QFormLayout.RowWrapPolicy.WrapLongRows)
        self._add_form_row(point_timing, "Point A", self.point_a_spin)
        self._add_form_row(point_timing, "Point B", self.point_b_spin)
        self._add_form_row(point_timing, "Points apart", self.points_apart_spin)
        self._add_form_row(point_timing, "Point period", self.point_period_spin)
        self._add_form_row(point_timing, "Point offset", point_offset_control)
        registration_layout.addLayout(point_timing)
        controls_layout.addWidget(registration_section)

        processing_section, processing_layout = self._inspector_section("MAP VALUES")
        processing_form = QtWidgets.QFormLayout()
        processing_form.setContentsMargins(0, 0, 0, 0)
        processing_form.setHorizontalSpacing(12)
        processing_form.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        processing_form.setRowWrapPolicy(QtWidgets.QFormLayout.RowWrapPolicy.WrapLongRows)
        self.transform_combo = self._enum_combo(
            (
                ("Raw signed", ValueTransform.RAW),
                ("Absolute value", ValueTransform.ABSOLUTE),
                ("Negate", ValueTransform.NEGATE),
                ("Custom expression", ValueTransform.CUSTOM),
            )
        )
        self.baseline_combo = self._enum_combo(
            (
                ("None", BaselineMode.NONE),
                ("Manual", BaselineMode.MANUAL),
                ("Mean", BaselineMode.MEAN),
                ("Median", BaselineMode.MEDIAN),
                ("Minimum", BaselineMode.MINIMUM),
                ("Maximum", BaselineMode.MAXIMUM),
                ("Percentile", BaselineMode.PERCENTILE),
            )
        )
        self.normalization_combo = self._enum_combo(
            (
                ("None", NormalizationMode.NONE),
                ("Max magnitude", NormalizationMode.MAX_MAGNITUDE),
                ("Min-max", NormalizationMode.MIN_MAX),
                ("Reference", NormalizationMode.REFERENCE),
            )
        )
        self.scale_combo = self._enum_combo(
            (("Linear", ValueScale.LINEAR), ("Log10", ValueScale.LOG10))
        )
        self.color_range_combo = self._enum_combo(
            (
                ("Auto data range", ColorRangeMode.AUTO),
                ("Percentile", ColorRangeMode.PERCENTILE),
                ("Manual", ColorRangeMode.MANUAL),
            )
        )
        self.baseline_value_spin = self._value_spin()
        self.baseline_percentile_spin = self._percent_spin(50.0)
        self.custom_expression_edit = QtWidgets.QLineEdit("x")
        self.custom_expression_edit.setPlaceholderText("e.g. abs(x) * 2")
        self.normalization_reference_spin = self._value_spin()
        self.percentile_low_spin = self._percent_spin(1.0)
        self.percentile_high_spin = self._percent_spin(99.0)
        self.color_min_spin = self._value_spin()
        self.color_max_spin = self._value_spin()
        self._processing_field_rows: dict[str, tuple[QtWidgets.QLabel, QtWidgets.QWidget]] = {}
        self._add_processing_row(processing_form, "Value", self.transform_combo)
        self._add_processing_row(processing_form, "Baseline", self.baseline_combo)
        self._add_processing_row(processing_form, "Normalization", self.normalization_combo)
        self._add_processing_row(processing_form, "Scale", self.scale_combo)
        self._add_processing_row(processing_form, "Color limits", self.color_range_combo)
        self._add_processing_row(
            processing_form, "Baseline value", self.baseline_value_spin, "baseline_value"
        )
        self._add_processing_row(
            processing_form,
            "Baseline percentile",
            self.baseline_percentile_spin,
            "baseline_percentile",
        )
        self._add_processing_row(
            processing_form, "f(x)", self.custom_expression_edit, "custom_expression"
        )
        self._add_processing_row(
            processing_form,
            "Normalization reference",
            self.normalization_reference_spin,
            "normalization_reference",
        )
        self._add_processing_row(
            processing_form, "Low percentile", self.percentile_low_spin, "color_percentile"
        )
        self._add_processing_row(
            processing_form, "High percentile", self.percentile_high_spin, "color_percentile"
        )
        self._add_processing_row(
            processing_form, "Color minimum", self.color_min_spin, "color_manual"
        )
        self._add_processing_row(
            processing_form, "Color maximum", self.color_max_spin, "color_manual"
        )
        processing_layout.addLayout(processing_form)
        self.processing_summary = QtWidgets.QLabel("Raw signed values · linear")
        self.processing_summary.setObjectName("processingSummary")
        self.processing_summary.setWordWrap(True)
        processing_layout.addWidget(self.processing_summary)
        reset_processing = QtWidgets.QPushButton("Reset processing")
        reset_processing.clicked.connect(self._reset_processing)
        processing_layout.addWidget(reset_processing)
        controls_layout.addWidget(processing_section)

        reconstruction_section, reconstruction_layout = self._inspector_section("RECONSTRUCTION")
        self.timing_label = QtWidgets.QLabel("Timing valid: —")
        self.timing_label.setObjectName("fieldLabel")
        reconstruction_layout.addWidget(self.timing_label)
        qc_grid = QtWidgets.QGridLayout()
        qc_grid.setContentsMargins(0, 4, 0, 0)
        qc_grid.setHorizontalSpacing(14)
        qc_grid.setVerticalSpacing(5)
        self.qc_values: dict[str, QtWidgets.QLabel] = {}
        for row, name in enumerate(
            (
                "Row period",
                "Point period",
                "Unused / row",
                "Valid pixels",
                "Median samples/pixel",
            )
        ):
            label = QtWidgets.QLabel(name)
            label.setObjectName("fieldLabel")
            value = QtWidgets.QLabel("—")
            value.setObjectName("qcValue")
            value.setAlignment(
                QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
            qc_grid.addWidget(label, row, 0)
            qc_grid.addWidget(value, row, 1)
            self.qc_values[name] = value
        reconstruction_layout.addLayout(qc_grid)
        self.qc_label = QtWidgets.QLabel("")
        self.qc_label.setObjectName("warningLabel")
        self.qc_label.setWordWrap(True)
        self.qc_label.setVisible(False)
        reconstruction_layout.addWidget(self.qc_label)
        button_row = QtWidgets.QHBoxLayout()
        self.reset_button = QtWidgets.QPushButton("Reset trace view")
        self.reset_button.clicked.connect(self._reset_views)
        button_row.addWidget(self.reset_button)
        button_row.addStretch(1)
        reconstruction_layout.addLayout(button_row)
        controls_layout.addWidget(reconstruction_section)
        controls_layout.addStretch(1)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(controls)
        scroll.setMinimumWidth(260)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        splitter.addWidget(scroll)

        right_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        map_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.map_stack, self.map_plot, self.map_image, self.map_color_bar = self._make_image_panel(
            "Reconstructed map",
            "No reconstruction yet",
            "Open a CSV to reconstruct a map.",
            "Signal",
        )
        self.count_stack, self.count_plot, self.count_image, self.count_color_bar = (
            self._make_image_panel(
                "Samples / pixel",
                "No sample counts yet",
                "Sample counts appear after reconstruction.",
                "Samples",
            )
        )
        self.qc_tabs = QtWidgets.QTabWidget()
        self.qc_tabs.setDocumentMode(True)
        self.qc_tabs.addTab(self.count_stack, "Samples / pixel")
        (
            self.distribution_stack,
            self.distribution_plot,
            self.distribution_bars,
            self.mean_line,
            self.median_line,
            self.distribution_stats,
        ) = self._make_distribution_panel()
        self.qc_tabs.addTab(self.distribution_stack, "Distribution")
        map_splitter.addWidget(self.map_stack)
        map_splitter.addWidget(self.qc_tabs)
        right_splitter.addWidget(map_splitter)

        self.raw_stack, self.raw_plot, self.raw_guide_key = self._make_trace_panel()
        self.raw_curve = self.raw_plot.plot([], [], pen=pg.mkPen(TRACE, width=1.15))
        right_splitter.addWidget(self.raw_stack)
        right_splitter.setStretchFactor(0, 45)
        right_splitter.setStretchFactor(1, 55)
        splitter.addWidget(right_splitter)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([270, 910])
        right_splitter.setSizes([360, 440])

        self.statusBar().showMessage("Open a HappyMeasure single-v2 CSV to begin.")
        for widget in (
            self.rows_spin,
            self.cols_spin,
            self.scan_combo,
            self.first_row_check,
            self.flip_y_check,
            self.median_check,
            self.rows_apart_spin,
            self.row_offset_spin,
            self.points_apart_spin,
            self.point_offset_spin,
        ):
            if isinstance(widget, QtWidgets.QComboBox):
                widget.currentIndexChanged.connect(self._reconstruct)
            elif isinstance(widget, QtWidgets.QCheckBox):
                widget.stateChanged.connect(self._reconstruct)
            else:
                widget.valueChanged.connect(self._reconstruct)
        self.rows_spin.valueChanged.connect(self._update_offset_ranges)
        self.cols_spin.valueChanged.connect(self._update_offset_ranges)
        self.row_offset_spin.valueChanged.connect(self.row_offset_slider.setValue)
        self.point_offset_spin.valueChanged.connect(self.point_offset_slider.setValue)
        self.row_offset_slider.valueChanged.connect(self.row_offset_spin.setValue)
        self.point_offset_slider.valueChanged.connect(self.point_offset_spin.setValue)
        self.points_apart_spin.valueChanged.connect(self._sync_point_period_from_anchors)
        self.point_period_spin.editingFinished.connect(self._point_period_finished)
        for spin in (self.row_a_spin, self.row_b_spin, self.point_a_spin, self.point_b_spin):
            spin.editingFinished.connect(self._anchor_spin_finished)
        for combo in (
            self.transform_combo,
            self.baseline_combo,
            self.normalization_combo,
            self.scale_combo,
            self.color_range_combo,
        ):
            combo.currentIndexChanged.connect(self._processing_controls_changed)
        for widget in (
            self.baseline_value_spin,
            self.baseline_percentile_spin,
            self.custom_expression_edit,
            self.normalization_reference_spin,
            self.percentile_low_spin,
            self.percentile_high_spin,
            self.color_min_spin,
            self.color_max_spin,
        ):
            if isinstance(widget, QtWidgets.QLineEdit):
                widget.editingFinished.connect(self._processing_controls_changed)
            else:
                widget.editingFinished.connect(self._processing_controls_changed)

        self._update_processing_fields()
        self._set_loaded_view(False)

    def _build_header(self, layout: QtWidgets.QVBoxLayout) -> None:
        header = QtWidgets.QFrame()
        header.setObjectName("appHeader")
        header.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Maximum
        )
        header.setMaximumHeight(76)
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 12, 10)
        title_layout = QtWidgets.QVBoxLayout()
        title_layout.setSpacing(1)
        title = QtWidgets.QLabel("Map Reconstruction")
        title.setObjectName("appTitle")
        self.header_subtitle = QtWidgets.QLabel("HappyMeasure time-series workspace")
        self.header_subtitle.setObjectName("appSubtitle")
        title_layout.addWidget(title)
        title_layout.addWidget(self.header_subtitle)
        header_layout.addLayout(title_layout)
        header_layout.addStretch(1)
        self.open_button = QtWidgets.QPushButton("Open CSV")
        self.open_button.setObjectName("primaryAction")
        self.open_button.clicked.connect(self._choose_file)
        self.export_button = QtWidgets.QPushButton("Export Map")
        export_menu = QtWidgets.QMenu(self.export_button)
        export_menu.addAction("Raw reconstructed map", self._export_raw_map)
        export_menu.addAction("Processed map", self._export_processed_map)
        export_menu.addAction("Both", self._export_both_maps)
        self.export_button.setMenu(export_menu)
        self.export_button.clicked.connect(self._export_raw_map)
        self.export_button.setEnabled(False)
        header_layout.addWidget(self.open_button)
        header_layout.addWidget(self.export_button)
        layout.addWidget(header)

    @staticmethod
    def _inspector_section(title: str) -> tuple[QtWidgets.QFrame, QtWidgets.QVBoxLayout]:
        section = QtWidgets.QFrame()
        section.setObjectName("inspectorSection")
        layout = QtWidgets.QVBoxLayout(section)
        layout.setContentsMargins(12, 11, 12, 12)
        layout.setSpacing(8)
        header = QtWidgets.QLabel(title)
        header.setObjectName("sectionHeader")
        layout.addWidget(header)
        return section, layout

    @staticmethod
    def _subsection_header(title: str) -> QtWidgets.QLabel:
        header = QtWidgets.QLabel(title)
        header.setObjectName("subsectionHeader")
        return header

    @staticmethod
    def _add_form_row(form: QtWidgets.QFormLayout, label: str, widget: QtWidgets.QWidget) -> None:
        label_widget = QtWidgets.QLabel(label)
        label_widget.setObjectName("fieldLabel")
        form.addRow(label_widget, widget)

    @staticmethod
    def _int_spin(value: int, minimum: int, maximum: int) -> QtWidgets.QSpinBox:
        spin = QtWidgets.QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        spin.setMinimumWidth(72)
        return spin

    @staticmethod
    def _float_spin() -> QtWidgets.QDoubleSpinBox:
        spin = QtWidgets.QDoubleSpinBox()
        spin.setDecimals(6)
        spin.setRange(-1e15, 1e15)
        spin.setSingleStep(0.1)
        spin.setSuffix(" s")
        spin.setButtonSymbols(QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons)
        spin.setKeyboardTracking(False)
        spin.setMinimumWidth(84)
        return spin

    @staticmethod
    def _value_spin() -> QtWidgets.QDoubleSpinBox:
        spin = QtWidgets.QDoubleSpinBox()
        spin.setDecimals(12)
        spin.setRange(-1e15, 1e15)
        spin.setSingleStep(1.0)
        spin.setButtonSymbols(QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons)
        spin.setKeyboardTracking(False)
        spin.setMinimumWidth(84)
        return spin

    @staticmethod
    def _percent_spin(value: float) -> QtWidgets.QDoubleSpinBox:
        spin = MapReconstructionWindow._value_spin()
        spin.setRange(0.0, 100.0)
        spin.setSingleStep(1.0)
        spin.setValue(value)
        spin.setSuffix(" %")
        return spin

    @staticmethod
    def _enum_combo(items: tuple[tuple[str, object], ...]) -> QtWidgets.QComboBox:
        combo = QtWidgets.QComboBox()
        for label, value in items:
            combo.addItem(label, value)
        return combo

    def _add_processing_row(
        self,
        form: QtWidgets.QFormLayout,
        label: str,
        widget: QtWidgets.QWidget,
        key: str | None = None,
    ) -> None:
        label_widget = QtWidgets.QLabel(label)
        label_widget.setObjectName("fieldLabel")
        form.addRow(label_widget, widget)
        if key is not None:
            self._processing_field_rows[key] = (label_widget, widget)

    @staticmethod
    def _offset_slider() -> QtWidgets.QSlider:
        slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        slider.setRange(0, 0)
        slider.setMinimumWidth(64)
        return slider

    def _make_empty_panel(self, title: str, message: str, *, action: bool) -> QtWidgets.QFrame:
        panel = QtWidgets.QFrame()
        panel.setObjectName("emptyState")
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        title_label = QtWidgets.QLabel(title)
        title_label.setObjectName("emptyTitle")
        title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        message_label = QtWidgets.QLabel(message)
        message_label.setObjectName("emptyMessage")
        message_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        message_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addSpacing(4)
        layout.addWidget(message_label)
        if action:
            open_empty_button = QtWidgets.QPushButton("Open CSV")
            open_empty_button.setObjectName("primaryAction")
            open_empty_button.clicked.connect(self._choose_file)
            layout.addSpacing(12)
            layout.addWidget(open_empty_button, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        return panel

    @staticmethod
    def _configure_plot(plot: pg.PlotWidget, title: str) -> None:
        plot.setBackground(PANEL)
        plot.setTitle(title, color=PRIMARY_TEXT, size="11pt")
        for axis_name in ("left", "bottom", "right", "top"):
            axis = plot.getAxis(axis_name)
            axis.setPen(GRID_MAJOR)
            axis.setTextPen(SECONDARY_TEXT)
            axis.setStyle(tickTextOffset=7)
        plot.showGrid(x=True, y=True, alpha=0.24)

    @staticmethod
    def _make_colormap(colors: list[str]) -> pg.ColorMap:
        return pg.ColorMap(np.linspace(0.0, 1.0, len(colors)), colors)

    def _make_image_panel(
        self, title: str, empty_title: str, empty_message: str, scale_label: str
    ) -> tuple[QtWidgets.QStackedWidget, pg.PlotWidget, pg.ImageItem, pg.ColorBarItem]:
        stack = QtWidgets.QStackedWidget()
        stack.addWidget(self._make_empty_panel(empty_title, empty_message, action=False))
        plot = pg.PlotWidget()
        self._configure_plot(plot, title)
        plot.setAspectLocked(True)
        image = pg.ImageItem()
        plot.addItem(image)
        colors = (
            ["#122C5A", "#1D65B9", "#20A4A6", "#C8D84D", "#F7E85A"]
            if scale_label == "Signal"
            else ["#EFF6FF", "#BFDBFE", "#60A5FA", "#2563EB", "#173E8C"]
        )
        color_bar = pg.ColorBarItem(
            colorMap=self._make_colormap(colors),
            interactive=False,
            width=12,
            label=scale_label,
            colorMapMenu=False,
        )
        color_bar.setImageItem(image, insert_in=plot.getPlotItem())
        color_bar.getAxis("right").setPen(BORDER)
        color_bar.getAxis("right").setTextPen(SECONDARY_TEXT)
        stack.addWidget(plot)
        return stack, plot, image, color_bar

    def _make_trace_panel(
        self,
    ) -> tuple[QtWidgets.QStackedWidget, pg.PlotWidget, QtWidgets.QLabel]:
        stack = QtWidgets.QStackedWidget()
        stack.addWidget(
            self._make_empty_panel(
                "Raw trace", "Open a HappyMeasure time-series CSV to begin.", action=True
            )
        )
        plot = pg.PlotWidget()
        self._configure_plot(plot, "Raw time trace")
        plot.setLabel("bottom", "Elapsed time", units="s", color=SECONDARY_TEXT)
        plot.setLabel("left", "Signal", color=SECONDARY_TEXT)
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        guide_key = QtWidgets.QLabel(
            "<span style='color:#e53935'>●</span> Row A &nbsp; "
            "<span style='color:#00bcd4'>●</span> Row B &nbsp; "
            "<span style='color:#2979ff'>●</span> Point A &nbsp; "
            "<span style='color:#d500f9'>●</span> Point B &nbsp; "
            "<span style='color:#888888'>⋮</span> Row refs &nbsp; "
            "<span style='color:#d4a017'>¦</span> Pixel starts"
        )
        guide_key.setObjectName("guideKey")
        guide_key.setTextFormat(QtCore.Qt.TextFormat.RichText)
        layout.addWidget(guide_key)
        layout.addWidget(plot, 1)
        stack.addWidget(panel)
        return stack, plot, guide_key

    def _make_distribution_panel(
        self,
    ) -> tuple[
        QtWidgets.QStackedWidget,
        pg.PlotWidget,
        pg.BarGraphItem,
        pg.InfiniteLine,
        pg.InfiniteLine,
        QtWidgets.QLabel,
    ]:
        """Create the read-only reconstructed-value distribution QC view."""

        stack = QtWidgets.QStackedWidget()
        stack.addWidget(
            self._make_empty_panel(
                "Value distribution",
                "A histogram of finite reconstructed values appears here.",
                action=False,
            )
        )
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        plot = pg.PlotWidget()
        self._configure_plot(plot, "Value distribution")
        plot.setLabel("bottom", "Signal", color=SECONDARY_TEXT)
        plot.setLabel("left", "Pixels", color=SECONDARY_TEXT)
        bars = pg.BarGraphItem(
            x0=np.array([], dtype=float),
            x1=np.array([], dtype=float),
            height=np.array([], dtype=float),
            brush="#60A5FA",
            pen=pg.mkPen("#2563EB", width=0.5),
        )
        plot.addItem(bars)
        mean_line = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pg.mkPen("#D97706", width=1.5),
            label="mean",
            labelOpts={"color": "#9A6700", "position": 0.92},
        )
        median_line = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pg.mkPen("#7C3AED", width=1.5),
            label="median",
            labelOpts={"color": "#6941C6", "position": 0.08},
        )
        plot.addItem(mean_line)
        plot.addItem(median_line)
        mean_line.hide()
        median_line.hide()
        stats = QtWidgets.QLabel()
        stats.setObjectName("distributionStats")
        stats.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(plot, 1)
        layout.addWidget(stats)
        stack.addWidget(panel)
        return stack, plot, bars, mean_line, median_line, stats

    def _set_loaded_view(self, loaded: bool) -> None:
        index = 1 if loaded else 0
        for stack in (self.map_stack, self.count_stack, self.raw_stack):
            stack.setCurrentIndex(index)
        self.raw_guide_key.setVisible(loaded)
        if not loaded:
            self._clear_distribution()
        self.export_button.setEnabled(loaded and self.result is not None)

    def _update_processing_fields(self) -> None:
        baseline_mode = self._processing_enum(self.baseline_combo, BaselineMode)
        transform = self._processing_enum(self.transform_combo, ValueTransform)
        normalization = self._processing_enum(self.normalization_combo, NormalizationMode)
        color_range = self._processing_enum(self.color_range_combo, ColorRangeMode)
        self._set_processing_row_visible("baseline_value", baseline_mode is BaselineMode.MANUAL)
        self._set_processing_row_visible(
            "baseline_percentile", baseline_mode is BaselineMode.PERCENTILE
        )
        self._set_processing_row_visible("custom_expression", transform is ValueTransform.CUSTOM)
        self._set_processing_row_visible(
            "normalization_reference", normalization is NormalizationMode.REFERENCE
        )
        self._set_processing_row_visible(
            "color_percentile", color_range is ColorRangeMode.PERCENTILE
        )
        self._set_processing_row_visible("color_manual", color_range is ColorRangeMode.MANUAL)
        unit = self._raw_display_unit()
        dimensionless = (
            transform is ValueTransform.CUSTOM
            or normalization is not NormalizationMode.NONE
            or self._processing_enum(self.scale_combo, ValueScale) is ValueScale.LOG10
        )
        color_unit = DisplayUnit(unit.label, "", 1.0) if dimensionless else unit
        for key in ("baseline_value", "normalization_reference", "color_min", "color_max"):
            row = self._processing_field_rows.get(key)
            if row is not None:
                selected_unit = color_unit if key in {"color_min", "color_max"} else unit
                row[0].setText(
                    {
                        "baseline_value": "Baseline value",
                        "normalization_reference": "Normalization reference",
                        "color_min": "Color minimum",
                        "color_max": "Color maximum",
                    }[key]
                    + (f" ({selected_unit.unit})" if selected_unit.unit else "")
                )

    def _set_processing_row_visible(self, key: str, visible: bool) -> None:
        row = self._processing_field_rows.get(key)
        if row is None:
            return
        row[0].setVisible(visible)
        row[1].setVisible(visible)

    def _raw_display_unit(self) -> DisplayUnit:
        if self.data is None:
            return display_unit_for_signal(self.signal_combo.currentText())
        return display_unit_for_signal(
            self.signal_combo.currentText(), self.data.signals.get(self.signal_combo.currentText())
        )

    def _processing_display_scale(self) -> float:
        if self._processing_enum(self.transform_combo, ValueTransform) is ValueTransform.CUSTOM:
            return 1.0
        if (
            self._processing_enum(self.normalization_combo, NormalizationMode)
            is not NormalizationMode.NONE
        ):
            return 1.0
        if self._processing_enum(self.scale_combo, ValueScale) is ValueScale.LOG10:
            return 1.0
        return self._raw_display_unit().scale

    @staticmethod
    def _processing_enum(combo: QtWidgets.QComboBox, enum_type: type) -> object:
        return enum_type(combo.currentData())

    def _processing_config(self) -> MapProcessingConfig:
        raw_scale = self._raw_display_unit().scale
        processed_scale = self._processing_display_scale()
        return MapProcessingConfig(
            baseline_mode=self._processing_enum(self.baseline_combo, BaselineMode),
            baseline_value=(self.baseline_value_spin.value() / raw_scale),
            baseline_percentile=self.baseline_percentile_spin.value(),
            transform=self._processing_enum(self.transform_combo, ValueTransform),
            custom_expression=self.custom_expression_edit.text().strip() or "x",
            normalization=self._processing_enum(self.normalization_combo, NormalizationMode),
            normalization_reference=(self.normalization_reference_spin.value() / raw_scale),
            value_scale=self._processing_enum(self.scale_combo, ValueScale),
            color_range_mode=self._processing_enum(self.color_range_combo, ColorRangeMode),
            color_min=(self.color_min_spin.value() / processed_scale),
            color_max=(self.color_max_spin.value() / processed_scale),
            percentile_low=self.percentile_low_spin.value(),
            percentile_high=self.percentile_high_spin.value(),
        )

    def _processing_controls_changed(self, *_args: object) -> None:
        self._update_processing_fields()
        if self.result is not None:
            self._process_and_display()

    def _reset_processing(self) -> None:
        widgets = (
            self.transform_combo,
            self.baseline_combo,
            self.normalization_combo,
            self.scale_combo,
            self.color_range_combo,
        )
        for combo in widgets:
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
        self.baseline_value_spin.setValue(0.0)
        self.baseline_percentile_spin.setValue(50.0)
        self.custom_expression_edit.setText("x")
        self.normalization_reference_spin.setValue(1.0)
        self.percentile_low_spin.setValue(1.0)
        self.percentile_high_spin.setValue(99.0)
        self.color_min_spin.setValue(0.0)
        self.color_max_spin.setValue(1.0)
        self._processing_controls_changed()

    def _choose_file(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open HappyMeasure single-v2 CSV",
            "",
            "CSV files (*.csv);;All files (*.*)",
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
        self._refresh_file_label()
        self.header_subtitle.setText("Loaded time-series data")
        self.signal_combo.blockSignals(True)
        self.signal_combo.clear()
        self.signal_combo.addItems(data.signal_names)
        preferred = "Current_A" if "Current_A" in data.signals else data.signal_names[-1]
        self.signal_combo.setCurrentText(preferred)
        self.signal_combo.blockSignals(False)
        self._set_anchor_bounds(data)
        self._set_raw_signal(preferred)
        self._update_processing_fields()
        self._create_anchor_lines()
        self._set_loaded_view(True)
        self._reconstruct()
        self.statusBar().showMessage(f"Loaded {data.sample_count} samples from {path.name}")

    def _refresh_file_label(self) -> None:
        if self._loaded_filename is None:
            self.file_label.setText("No file loaded")
            self.file_label.setToolTip("No file loaded")
            return
        width = max(140, self.file_label.width())
        text = QtGui.QFontMetrics(self.file_label.font()).elidedText(
            self._loaded_filename,
            QtCore.Qt.TextElideMode.ElideMiddle,
            width,
        )
        self.file_label.setText(text)
        self.file_label.setToolTip(self._loaded_filename)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._refresh_file_label()

    def _current_display_unit(self) -> DisplayUnit:
        if self.processed is not None and self.processed.is_dimensionless:
            return DisplayUnit(self.processed.value_label, "", 1.0)
        if self.processed is not None:
            raw_unit = self._raw_display_unit()
            return DisplayUnit(self.processed.value_label, raw_unit.unit, raw_unit.scale)
        return self._raw_display_unit()

    def _set_raw_signal(self, signal_name: str) -> None:
        if self.data is None or signal_name not in self.data.signals:
            return
        display_unit = display_unit_for_signal(signal_name, self.data.signals[signal_name])
        self.raw_curve.setData(
            self.data.time_s,
            to_display_values(self.data.signals[signal_name], display_unit),
        )
        self.raw_plot.setLabel("left", display_unit.axis_label, color=SECONDARY_TEXT)

    def _signal_changed(self, signal_name: str) -> None:
        """Keep the raw trace, map, and QC data on one selected signal."""

        if self.data is None:
            return
        self._set_raw_signal(signal_name)
        self._update_processing_fields()
        self._reconstruct()

    def _set_anchor_bounds(self, data: TimeSeriesData) -> None:
        lower, upper = float(data.time_s[0]), float(data.time_s[-1])
        span = max(upper - lower, 1e-6)
        point_gap = span / max(100.0, self.cols_spin.value() * 4.0)
        point_a = lower + 0.05 * span
        point_b = min(upper, point_a + point_gap)
        if point_b <= point_a:
            point_a = lower
            point_b = upper
        defaults = {
            self.row_a_spin: lower + 0.20 * span,
            self.row_b_spin: lower + 0.70 * span,
            self.point_a_spin: point_a,
            self.point_b_spin: point_b,
        }
        for spin, value in defaults.items():
            spin.setRange(lower, upper)
            spin.setSingleStep(span / 1000.0)
            spin.setValue(float(np.clip(value, lower, upper)))
        self._update_offset_ranges()
        self._sync_point_period_from_anchors()

    def _update_offset_ranges(self) -> None:
        row_max = max(0, self.rows_spin.value() - 1)
        point_max = max(0, self.cols_spin.value() - 1)
        self.row_offset_spin.setRange(0, row_max)
        self.point_offset_spin.setRange(0, point_max)
        self.row_offset_slider.setRange(0, row_max)
        self.point_offset_slider.setRange(0, point_max)

    def _sync_point_period_from_anchors(self, *_args: object) -> None:
        """Show the period implied by the current Point A/B anchor pair."""

        if self.data is None:
            return
        period = (
            self.point_b_spin.value() - self.point_a_spin.value()
        ) / self.points_apart_spin.value()
        if period <= 0:
            return
        self.point_period_spin.blockSignals(True)
        self.point_period_spin.setValue(period)
        self.point_period_spin.blockSignals(False)

    def _point_period_finished(self) -> None:
        """Apply an edited Point period by moving Point B, as in the MATLAB workflow."""

        if self.data is None or self._syncing:
            return
        point_b = (
            self.point_a_spin.value()
            + self.points_apart_spin.value() * self.point_period_spin.value()
        )
        if not self.point_b_spin.minimum() <= point_b <= self.point_b_spin.maximum():
            self._invalidate_reconstruction(
                "Point period places Point B outside the loaded time range."
            )
            return
        self._syncing = True
        self.point_b_spin.setValue(point_b)
        if "point_b_s" in self.anchor_lines:
            self.anchor_lines["point_b_s"].setValue(point_b)
        self._syncing = False
        self._reconstruct()

    def _create_anchor_lines(self) -> None:
        for line in self.anchor_lines.values():
            self.raw_plot.removeItem(line)
        self.anchor_lines = {}
        specs = (
            ("row_a_s", self.row_a_spin, "#e53935", "Row A"),
            ("row_b_s", self.row_b_spin, "#00bcd4", "Row B"),
            ("point_a_s", self.point_a_spin, "#2979ff", "Point A"),
            ("point_b_s", self.point_b_spin, "#d500f9", "Point B"),
        )
        for key, spin, color, label in specs:
            line = pg.InfiniteLine(
                pos=spin.value(),
                angle=90,
                movable=True,
                pen=pg.mkPen(color, width=2),
                label=label,
                labelOpts={"color": color, "position": 0.1},
            )
            line.sigPositionChanged.connect(self._anchor_line_moved)
            line.sigPositionChangeFinished.connect(self._anchor_line_finished)
            self.raw_plot.addItem(line)
            self.anchor_lines[key] = line

    def _anchor_line_moved(self, line: pg.InfiniteLine) -> None:
        for key, current in self.anchor_lines.items():
            if current is not line:
                continue
            spin = getattr(self, f"{key.replace('_s', '')}_spin")
            self._syncing = True
            spin.setValue(float(line.value()))
            self._syncing = False
            return

    def _anchor_line_finished(self, _line: pg.InfiniteLine) -> None:
        self._sync_point_period_from_anchors()
        self._reconstruct()

    def _anchor_spin_finished(self) -> None:
        if self._syncing:
            return
        for key, spin in (
            ("row_a_s", self.row_a_spin),
            ("row_b_s", self.row_b_spin),
            ("point_a_s", self.point_a_spin),
            ("point_b_s", self.point_b_spin),
        ):
            if key in self.anchor_lines:
                self.anchor_lines[key].setValue(spin.value())
        self._sync_point_period_from_anchors()
        self._reconstruct()

    def _current_params(self) -> DualOffsetParams:
        return DualOffsetParams(
            rows=self.rows_spin.value(),
            cols=self.cols_spin.value(),
            row_a_s=self.row_a_spin.value(),
            row_b_s=self.row_b_spin.value(),
            rows_apart=self.rows_apart_spin.value(),
            row_offset=self.row_offset_spin.value(),
            point_a_s=self.point_a_spin.value(),
            point_b_s=self.point_b_spin.value(),
            points_apart=self.points_apart_spin.value(),
            point_offset=self.point_offset_spin.value(),
            scan_pattern=self.scan_combo.currentData(),
            first_row_ltr=self.first_row_check.isChecked(),
            use_median=self.median_check.isChecked(),
        )

    def _reconstruct(self) -> None:
        if self.data is None or self._syncing:
            return
        try:
            params = self._current_params()
            result = reconstruct_map(self.data, self.signal_combo.currentText(), params)
        except ValueError as exc:
            self._invalidate_reconstruction(str(exc))
            return
        self.params = params
        timing = result.timing
        self.timing_label.setText("Timing valid: ✓")
        finite = np.isfinite(result.values)
        valid_percent = 100.0 * float(np.mean(finite))
        median_samples = float(np.median(result.sample_counts[finite])) if np.any(finite) else 0.0
        self.qc_values["Row period"].setText(f"{timing.row_period_s:.6g} s")
        self.qc_values["Point period"].setText(f"{timing.point_period_s:.6g} s")
        self.qc_values["Unused / row"].setText(
            f"{timing.row_period_s - params.cols * timing.point_period_s:.6g} s"
        )
        self.qc_values["Valid pixels"].setText(f"{valid_percent:.0f} %")
        self.qc_values["Median samples/pixel"].setText(f"{median_samples:.3g}")
        if not np.any(finite):
            self.result = None
            self.processed = None
            self._active_color_limits = None
            warnings = ["No valid pixels for current timing.", *result.warnings]
            self.qc_label.setText(" | ".join(warnings))
            self.qc_label.setVisible(True)
            self._show_empty_panel(
                self.map_stack,
                "No valid reconstructed pixels",
                "Adjust timing anchors or offsets to place pixel windows within the trace.",
            )
            self.map_image.clear()
            self._set_image(self.count_plot, self.count_image, result.sample_counts)
            self.count_stack.setCurrentIndex(1)
            self._clear_distribution()
            self._update_guides(result)
            self.export_button.setEnabled(False)
            self.statusBar().showMessage("No valid reconstructed pixels for current timing.")
            return

        self.result = result
        self._process_and_display()
        self.map_stack.setCurrentIndex(1)
        self._set_image(self.count_plot, self.count_image, result.sample_counts)
        self.count_stack.setCurrentIndex(1)
        self._update_guides(result)
        if self.processed is not None:
            self.statusBar().showMessage("Map reconstructed.")

    def _update_value_axis_labels(self, label: str | None = None) -> None:
        """Keep raw, map, and distribution axes in the current display units."""

        label = label or self._current_display_unit().axis_label
        self.map_color_bar.setLabel("right", label, enableAutoSIPrefix=False)
        self.map_color_bar.getAxis("right").enableAutoSIPrefix(False)
        self.distribution_plot.setLabel("bottom", label, color=SECONDARY_TEXT)
        self.raw_plot.setLabel("left", self._raw_display_unit().axis_label, color=SECONDARY_TEXT)

    def _processed_display_unit(self, processed: ProcessedMap) -> DisplayUnit:
        if processed.is_dimensionless:
            return DisplayUnit(processed.value_label, "", 1.0)
        raw_unit = self._raw_display_unit()
        return DisplayUnit(processed.value_label, raw_unit.unit, raw_unit.scale)

    def _process_and_display(self) -> None:
        if self.result is None or self.data is None:
            return
        try:
            config = self._processing_config()
            processed = process_map(
                self.result.values,
                config,
                self.signal_combo.currentText(),
            )
            limits = compute_color_limits(processed.values, config)
        except ValueError as exc:
            self.processed = None
            self._active_color_limits = None
            self._show_empty_panel(self.map_stack, "Processing unavailable", str(exc))
            self.map_image.clear()
            self._clear_distribution()
            self.qc_label.setText(str(exc))
            self.qc_label.setVisible(True)
            self.export_button.setEnabled(self.result is not None)
            self.statusBar().showMessage(str(exc))
            return

        self.processing_config = config
        self.processed = processed
        display_unit = self._processed_display_unit(processed)
        self.processing_summary.setText(
            f"{processed.value_label} - {config.value_scale.value}"
            + (f" - {len(processed.warnings)} warning(s)" if processed.warnings else "")
        )
        warnings = [*self.result.warnings, *processed.warnings]
        self.qc_label.setText(" | ".join(warnings))
        self.qc_label.setVisible(bool(warnings))
        self._update_value_axis_labels(display_unit.axis_label)
        if limits is None:
            self._active_color_limits = None
            self._show_empty_panel(
                self.map_stack, "No finite processed values", "Adjust processing settings."
            )
            self.map_image.clear()
        else:
            display_limits = (
                limits.minimum * display_unit.scale,
                limits.maximum * display_unit.scale,
            )
            self._active_color_limits = display_limits
            self._set_image(
                self.map_plot,
                self.map_image,
                processed.values,
                display_unit=display_unit,
                levels=display_limits,
            )
            self.map_stack.setCurrentIndex(1)
            self.map_color_bar.setLevels(display_limits)
        self._update_distribution_processed(processed, display_unit)
        self.export_button.setEnabled(bool(np.isfinite(processed.values).any()))
        self.statusBar().showMessage("Map values processed.")

    def _update_distribution_processed(
        self, processed: ProcessedMap, display_unit: DisplayUnit
    ) -> None:
        """Render finite processed values without display-orientation transforms."""

        histogram = make_histogram_data(processed.values)
        if histogram is None:
            self._clear_distribution()
            return

        self.distribution_bars.setOpts(
            x0=to_display_values(histogram.edges[:-1], display_unit),
            x1=to_display_values(histogram.edges[1:], display_unit),
            height=histogram.counts,
        )
        self.mean_line.setValue(histogram.mean * display_unit.scale)
        self.median_line.setValue(histogram.median * display_unit.scale)
        self.mean_line.show()
        self.median_line.show()
        self.distribution_stats.setText(
            "Finite pixels "
            f"{histogram.finite_count} / {histogram.total_count}    "
            f"Mean {format_display_value(histogram.mean, display_unit)}    "
            f"Median {format_display_value(histogram.median, display_unit)}"
        )
        self.distribution_stack.setCurrentIndex(1)
        self.distribution_plot.enableAutoRange()

    def _set_image(
        self,
        plot: pg.PlotWidget,
        image: pg.ImageItem,
        values: np.ndarray,
        *,
        display_unit: DisplayUnit | None = None,
        levels: tuple[float, float] | None = None,
    ) -> bool:
        display = np.asarray(values, dtype=float)
        if display_unit is not None:
            display = to_display_values(display, display_unit)
        if self.flip_y_check.isChecked():
            display = np.flipud(display)
        if not np.isfinite(display).any():
            image.clear()
            return False
        image.setImage(display, autoLevels=levels is None, levels=levels)
        plot.enableAutoRange()
        return True

    def _show_empty_panel(self, stack: QtWidgets.QStackedWidget, title: str, message: str) -> None:
        panel = stack.widget(0)
        title_label = panel.findChild(QtWidgets.QLabel, "emptyTitle")
        message_label = panel.findChild(QtWidgets.QLabel, "emptyMessage")
        if title_label is not None:
            title_label.setText(title)
        if message_label is not None:
            message_label.setText(message)
        stack.setCurrentIndex(0)

    def _clear_distribution(self) -> None:
        self.distribution_bars.setOpts(
            x0=np.array([], dtype=float),
            x1=np.array([], dtype=float),
            height=np.array([], dtype=float),
        )
        self.distribution_stats.clear()
        self.mean_line.hide()
        self.median_line.hide()
        self.distribution_stack.setCurrentIndex(0)

    def _clear_guides(self) -> None:
        for guide in self.guide_items:
            self.raw_plot.removeItem(guide)
        self.guide_items = []

    def _invalidate_reconstruction(self, message: str) -> None:
        """Clear stale derived state after invalid timing or oversized geometry."""

        self.result = None
        self.params = None
        self.processed = None
        self._active_color_limits = None
        self.timing_label.setText("Timing valid: no")
        for value in self.qc_values.values():
            value.setText("—")
        self.qc_label.setText(message)
        self.qc_label.setVisible(True)
        self._show_empty_panel(self.map_stack, "Reconstruction unavailable", message)
        self._show_empty_panel(self.count_stack, "Sample counts unavailable", message)
        self.map_image.clear()
        self.count_image.clear()
        self._clear_distribution()
        self._clear_guides()
        self.export_button.setEnabled(False)
        self.statusBar().showMessage(message)

    @staticmethod
    def _guide_indices(count: int) -> np.ndarray:
        if count <= MAX_GUIDES_PER_FAMILY:
            return np.arange(count)
        return np.unique(np.linspace(0, count - 1, MAX_GUIDES_PER_FAMILY, dtype=int))

    def _update_guides(self, result: ReconstructionResult) -> None:
        self._clear_guides()
        if self.data is None or self.params is None:
            return
        t_min, t_max = float(self.data.time_s[0]), float(self.data.time_s[-1])
        timing = result.timing
        for row in self._guide_indices(self.params.rows):
            position = timing.row_ref0_s + row * timing.row_period_s
            if t_min <= position <= t_max:
                self._add_guide(position, "#888888", QtCore.Qt.PenStyle.DotLine)
        row_index = int(np.floor((self.params.point_a_s - timing.row_ref0_s) / timing.row_period_s))
        row_base = timing.row_ref0_s + row_index * timing.row_period_s
        for column in self._guide_indices(self.params.cols):
            position = row_base + timing.pixel1_phase_s + column * timing.point_period_s
            if t_min <= position <= t_max:
                self._add_guide(position, "#d4a017", QtCore.Qt.PenStyle.DashLine)

    def _add_guide(self, position: float, color: str, style: QtCore.Qt.PenStyle) -> None:
        guide = pg.InfiniteLine(
            pos=position,
            angle=90,
            movable=False,
            pen=pg.mkPen(color, width=1, style=style),
        )
        self.raw_plot.addItem(guide)
        self.guide_items.append(guide)

    def _reset_views(self) -> None:
        self.raw_plot.enableAutoRange()
        self.map_plot.enableAutoRange()
        self.count_plot.enableAutoRange()
        self.distribution_plot.enableAutoRange()

    def _export_raw_map(self) -> None:
        if self.result is None or self.data is None:
            QtWidgets.QMessageBox.information(
                self, "No map", "Load a CSV and reconstruct a map first."
            )
            return
        default = f"{self.data.source_path.stem if self.data.source_path else 'map'}_map_raw.csv"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export raw reconstructed map", default, "CSV files (*.csv);;All files (*.*)"
        )
        if not path:
            return
        try:
            np.savetxt(path, self.result.values, delimiter=",", fmt="%.12g")
        except OSError as exc:
            QtWidgets.QMessageBox.critical(self, "Export failed", str(exc))
            return
        self.statusBar().showMessage(f"Exported raw map to {path}")

    def _export_processed_map(self) -> None:
        if (
            self.data is None
            or self.processed is None
            or not np.isfinite(self.processed.values).any()
        ):
            QtWidgets.QMessageBox.information(
                self,
                "No processed map",
                "Apply valid processing settings to a reconstructed map first.",
            )
            return
        default = (
            f"{self.data.source_path.stem if self.data.source_path else 'map'}_map_processed.csv"
        )
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export processed map", default, "CSV files (*.csv);;All files (*.*)"
        )
        if not path:
            return
        try:
            np.savetxt(path, self.processed.values, delimiter=",", fmt="%.12g")
            sidecar = Path(path).with_suffix(".json")
            sidecar.write_text(
                json.dumps(self._processed_export_metadata(), indent=2), encoding="utf-8"
            )
        except (OSError, TypeError, ValueError) as exc:
            QtWidgets.QMessageBox.critical(self, "Export failed", str(exc))
            return
        self.statusBar().showMessage(f"Exported processed map to {path}")

    def _export_both_maps(self) -> None:
        self._export_raw_map()
        if self.result is not None:
            self._export_processed_map()

    def _processed_export_metadata(self) -> dict[str, object]:
        config = self.processing_config
        config_payload = {
            key: (value.value if hasattr(value, "value") else value)
            for key, value in asdict(config).items()
        }
        raw_unit = self._raw_display_unit()
        return {
            "source_signal": self.signal_combo.currentText(),
            "baseline_used_si": self.processed.baseline_used if self.processed else None,
            "processing": config_payload,
            "processing_warnings": list(self.processed.warnings) if self.processed else [],
            "value_label": self.processed.value_label if self.processed else "",
            "raw_physical_unit": raw_unit.unit,
            "dimensionless": bool(self.processed.is_dimensionless) if self.processed else False,
            "display_color_limits": self._active_color_limits,
        }

    def _export_map(self) -> None:
        """Backward-compatible raw-export entry point for older UI automation."""

        self._export_raw_map()


def run_app(path: Path | None = None) -> int:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    window = MapReconstructionWindow(path)
    window.show()
    return app.exec()
