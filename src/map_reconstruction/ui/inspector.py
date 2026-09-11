"""Left-hand semantic controls for the Map Reconstruction workspace."""

from __future__ import annotations

from typing import TypeVar

from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore[import-not-found]

from map_reconstruction.display_units import DisplayUnit
from map_reconstruction.models import (
    Aggregation,
    DualOffsetParams,
    PhaseWindowParams,
    ScanPattern,
    TimeSeriesData,
    WindowMode,
)
from map_reconstruction.processing import (
    BaselineMode,
    ColorRangeMode,
    MapProcessingConfig,
    NormalizationMode,
    ValueScale,
    ValueTransform,
)
from map_reconstruction.project_io import ProjectState

EnumT = TypeVar("EnumT")


class ReconstructionInspector(QtWidgets.QWidget):
    """Own the left inspector and emit semantic changes to the coordinator."""

    signalChanged = QtCore.Signal(str)
    geometryChanged = QtCore.Signal()
    registrationChanged = QtCore.Signal()
    convertPhaseWindowRequested = QtCore.Signal()
    processingChanged = QtCore.Signal()
    colorLimitsChanged = QtCore.Signal()
    pointPeriodEdited = QtCore.Signal(float)
    openRequested = QtCore.Signal()
    openProjectRequested = QtCore.Signal()
    exportRawRequested = QtCore.Signal()
    exportProcessedRequested = QtCore.Signal()
    exportBothRequested = QtCore.Signal()
    exportProjectRequested = QtCore.Signal()
    exportSummaryRequested = QtCore.Signal()
    exportPdfRequested = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        self._has_data = False
        self._syncing = False
        self._anchors_user_edited = False
        self._build_ui()

    def _build_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 8, 0)
        root.setSpacing(9)

        data_section, data_layout = self._inspector_section("DATA")
        self.data_section = data_section
        data_actions = QtWidgets.QHBoxLayout()
        data_actions.setContentsMargins(0, 0, 0, 0)
        data_actions.setSpacing(6)
        self.open_button = QtWidgets.QPushButton("Open CSV")
        self.open_button.setObjectName("primaryAction")
        self.open_button.clicked.connect(self.openRequested)
        self.open_project_button = QtWidgets.QPushButton("Open Project")
        self.open_project_button.clicked.connect(self.openProjectRequested)
        self.export_button = QtWidgets.QPushButton("Export Map")
        self.export_button.setEnabled(False)
        self.raw_export_action = QtGui.QAction("Raw reconstructed map", self)
        self.processed_export_action = QtGui.QAction("Processed map", self)
        self.both_export_action = QtGui.QAction("Both", self)
        self.project_export_action = QtGui.QAction("Project...", self)
        self.summary_export_action = QtGui.QAction("Parameter summary...", self)
        self.pdf_export_action = QtGui.QAction("HTML report...", self)
        self.raw_export_action.triggered.connect(self.exportRawRequested)
        self.processed_export_action.triggered.connect(self.exportProcessedRequested)
        self.both_export_action.triggered.connect(self.exportBothRequested)
        self.project_export_action.triggered.connect(self.exportProjectRequested)
        self.summary_export_action.triggered.connect(self.exportSummaryRequested)
        self.pdf_export_action.triggered.connect(self.exportPdfRequested)
        export_menu = QtWidgets.QMenu(self.export_button)
        export_menu.addAction(self.raw_export_action)
        export_menu.addAction(self.processed_export_action)
        export_menu.addAction(self.both_export_action)
        export_menu.addSeparator()
        export_menu.addAction(self.project_export_action)
        export_menu.addAction(self.summary_export_action)
        export_menu.addAction(self.pdf_export_action)
        self.export_button.setMenu(export_menu)
        self.export_button.clicked.connect(self.exportRawRequested)
        data_actions.addWidget(self.open_button)
        data_actions.addWidget(self.open_project_button)
        data_actions.addStretch(1)
        data_layout.addLayout(data_actions)
        self.file_label = QtWidgets.QLabel("No file loaded")
        self.file_label.setObjectName("fileLabel")
        self.file_label.setWordWrap(False)
        self.file_label.setMinimumWidth(0)
        self.file_label.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred
        )
        self.file_label.setToolTip("No file loaded")
        data_layout.addWidget(self.file_label)
        data_form = self._form_layout()
        self.signal_combo = QtWidgets.QComboBox()
        self.signal_combo.setMaximumWidth(145)
        self.signal_combo.currentTextChanged.connect(self.signalChanged)
        self._add_form_row(data_form, "Signal", self.signal_combo)
        data_layout.addLayout(data_form)
        export_layout = QtWidgets.QHBoxLayout()
        export_layout.setContentsMargins(0, 0, 0, 0)
        export_layout.addWidget(self.export_button)
        export_layout.addStretch(1)
        data_layout.addLayout(export_layout)
        root.addWidget(data_section)

        geometry_section, geometry_layout = self._inspector_section("GEOMETRY")
        self.geometry_section = geometry_section
        geometry_form = self._form_layout()
        self.rows_spin = self._int_spin(0, 0, 10000)
        self.cols_spin = self._int_spin(0, 0, 10000)
        self.rows_spin.setSpecialValueText("—")
        self.cols_spin.setSpecialValueText("—")
        self.geometry_dimensions = self._compact_pair(
            "Rows", self.rows_spin, "Columns", self.cols_spin, "geometryDimensions"
        )
        geometry_layout.addWidget(self.geometry_dimensions)
        self.scan_combo = self._enum_combo(
            (("Same direction", ScanPattern.SAME_DIRECTION), ("Serpentine", ScanPattern.SERPENTINE))
        )
        self._add_form_row(geometry_form, "Scan pattern", self.scan_combo)
        self.first_row_check = QtWidgets.QCheckBox("First row L → R")
        self.first_row_check.setChecked(True)
        self._add_form_row(geometry_form, "Orientation", self.first_row_check)
        self.flip_y_check = QtWidgets.QCheckBox("Flip Y display")
        self._add_form_row(geometry_form, "Display", self.flip_y_check)
        self.aggregation_combo = self._enum_combo(
            (("Median", Aggregation.MEDIAN), ("Mean", Aggregation.MEAN))
        )
        self._add_form_row(geometry_form, "Aggregation", self.aggregation_combo)
        geometry_layout.addLayout(geometry_form)
        root.addWidget(geometry_section)

        registration_section, registration_layout = self._inspector_section("REGISTRATION")
        self.registration_section = registration_section
        method_row = QtWidgets.QHBoxLayout()
        method_label = QtWidgets.QLabel("Method")
        method_label.setObjectName("fieldLabel")
        self.method_combo = self._enum_combo(
            (
                ("Dual Offset (Legacy)", "dual_offset"),
                ("Dual Offset — Phase Window", "dual_offset_phase_window"),
            )
        )
        self.method_combo.setToolTip("Legacy projects remain Legacy until explicitly converted.")
        method_row.addWidget(method_label)
        method_row.addStretch(1)
        method_row.addWidget(self.method_combo)
        registration_layout.addLayout(method_row)
        registration_layout.addSpacing(4)

        self.row_a_spin = self._float_spin()
        self.row_b_spin = self._float_spin()
        self.point_a_spin = self._float_spin()
        self.point_b_spin = self._float_spin()
        self.row_a_spin.setToolTip("First Y/row timing anchor used to determine row period.")
        self.row_b_spin.setToolTip("Second Y/row timing anchor.")
        self.point_a_spin.setToolTip("First X/pixel timing anchor used to determine point period.")
        self.point_b_spin.setToolTip("Second X/pixel timing anchor.")
        self.rows_apart_spin = self._int_spin(10, 1, 100000)
        self.rows_apart_spin.setToolTip("T_row = (YB - YA) / Rows apart.")
        self.row_offset_spin = self._int_spin(0, 0, 100000)
        self.points_apart_spin = self._int_spin(10, 1, 100000)
        self.points_apart_spin.setToolTip("T_point = (XB - XA) / Points apart.")
        self.point_period_spin = self._value_spin()
        self.point_period_spin.setRange(1e-12, 1e15)
        self.point_period_spin.setDecimals(4)
        self.point_period_spin.setSingleStep(0.001)
        self.point_period_spin.setSuffix(" s")
        self.point_period_spin.setButtonSymbols(
            QtWidgets.QAbstractSpinBox.ButtonSymbols.UpDownArrows
        )
        self.point_period_spin.setToolTip(
            "Derived from XA, XB, and Points apart. Editing it moves XB."
        )
        self.point_offset_spin = self._int_spin(0, 0, 100000)
        self.x_period_offset_spin = self._int_spin(0, 0, 100000)
        self.y_phase_spin = self._phase_spin(0.0)
        self.x_phase_spin = self._phase_spin(0.0)
        self.window_mode_combo = self._enum_combo(
            (
                ("Fraction of period", WindowMode.FRACTION),
                ("Fixed duration", WindowMode.FIXED_DURATION),
            )
        )
        self.window_fraction_spin = self._percent_spin(65.0)
        self.window_duration_spin = self._float_spin()
        self.y_phase_control = self._slider_spin_control(
            self.y_phase_spin, 0, 999, 10.0, "yPhaseControl"
        )
        self.x_phase_control = self._slider_spin_control(
            self.x_phase_spin, 0, 999, 10.0, "xPhaseControl"
        )
        self.window_fraction_spin.setMinimum(0.1)
        self.window_fraction_control = self._slider_spin_control(
            self.window_fraction_spin, 1, 1000, 10.0, "windowFractionControl"
        )
        row_timing = QtWidgets.QVBoxLayout()
        row_timing.setContentsMargins(0, 0, 0, 0)
        row_timing.setSpacing(6)
        registration_layout.addWidget(self._subsection_header("ROW TIMING"))
        row_timing.addWidget(
            self._compact_pair("YA", self.row_a_spin, "YB", self.row_b_spin, "rowAnchorPair")
        )
        row_timing.addWidget(
            self._compact_pair(
                "Rows apart", self.rows_apart_spin, "Offset", self.row_offset_spin, "rowOffsetPair"
            )
        )
        row_timing.addWidget(
            self._compact_labeled_control("Y phase", self.y_phase_control, "yPhaseRow")
        )
        registration_layout.addLayout(row_timing)
        registration_layout.addSpacing(7)
        point_timing = QtWidgets.QVBoxLayout()
        point_timing.setContentsMargins(0, 0, 0, 0)
        point_timing.setSpacing(6)
        registration_layout.addWidget(self._subsection_header("POINT TIMING"))
        point_timing.addWidget(
            self._compact_pair("XA", self.point_a_spin, "XB", self.point_b_spin, "pointAnchorPair")
        )
        self.point_offset_control = self._compact_labeled_control(
            "Point offset", self.point_offset_spin, "pointOffsetRow"
        )
        self.x_offset_control = self._compact_pair(
            "Points apart",
            self.points_apart_spin,
            "X offset",
            self.x_period_offset_spin,
            "pointOffsetPair",
        )
        point_timing.addWidget(self.x_offset_control)
        point_timing.addWidget(
            self._compact_labeled_control("Point period", self.point_period_spin, "pointPeriodRow")
        )
        point_timing.addWidget(self.point_offset_control)
        point_timing.addWidget(
            self._compact_labeled_control("X phase", self.x_phase_control, "xPhaseRow")
        )
        registration_layout.addLayout(point_timing)
        self.phase_window_section = QtWidgets.QWidget()
        phase_form = QtWidgets.QVBoxLayout()
        phase_form.setContentsMargins(0, 0, 0, 0)
        phase_form.setSpacing(6)
        phase_form.addWidget(self._subsection_header("SAMPLE WINDOW"))
        phase_form.addWidget(
            self._compact_labeled_control("Mode", self.window_mode_combo, "windowModeRow")
        )
        self.window_fraction_row = self._compact_labeled_control(
            "Width", self.window_fraction_control, "windowFractionRow"
        )
        self.window_duration_row = self._compact_labeled_control(
            "Duration", self.window_duration_spin, "windowDurationRow"
        )
        phase_form.addWidget(self.window_fraction_row)
        phase_form.addWidget(self.window_duration_row)
        self.phase_window_section.setLayout(phase_form)
        registration_layout.addWidget(self.phase_window_section)
        self.convert_phase_button = QtWidgets.QPushButton("Convert to Phase Window")
        self.convert_phase_button.setToolTip(
            "Explicitly preserve the current Legacy acquisition windows."
        )
        self.convert_phase_button.clicked.connect(self.convertPhaseWindowRequested)
        registration_layout.addWidget(self.convert_phase_button)
        root.addWidget(registration_section)

        processing_section, processing_layout = self._inspector_section("MAP VALUES")
        self.processing_section = processing_section
        processing_form = self._form_layout()
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
        self._processing_rows: dict[str, tuple[QtWidgets.QLabel, QtWidgets.QWidget]] = {}
        self._add_processing_row(processing_form, "Value", self.transform_combo)
        self._add_processing_row(
            processing_form, "f(x)", self.custom_expression_edit, "custom_expression"
        )
        self.baseline_combo.setToolTip(
            "Applied after time-to-space reconstruction. This is not time-domain dark-current correction."
        )
        self._add_processing_row(
            processing_form, "Map offset", self.baseline_combo, "baseline_selector"
        )
        self._add_processing_row(
            processing_form, "Baseline value", self.baseline_value_spin, "baseline_value"
        )
        self._add_processing_row(
            processing_form,
            "Baseline percentile",
            self.baseline_percentile_spin,
            "baseline_percentile",
        )
        self._add_processing_row(processing_form, "Normalization", self.normalization_combo)
        self._add_processing_row(
            processing_form,
            "Normalization reference",
            self.normalization_reference_spin,
            "normalization_reference",
        )
        self._add_processing_row(processing_form, "Scale", self.scale_combo)
        self._add_processing_row(processing_form, "Color limits", self.color_range_combo)
        self.color_percentile_pair = self._compact_pair(
            "Low percentile",
            self.percentile_low_spin,
            "High percentile",
            self.percentile_high_spin,
            "colorPercentilePair",
        )
        percentile_tip = (
            "Percentile rank of the processed-data distribution; "
            "1% means the 1st percentile, not 1% of the maximum."
        )
        self.color_percentile_pair.setToolTip(percentile_tip)
        self.percentile_low_spin.setToolTip(percentile_tip)
        self.percentile_high_spin.setToolTip(percentile_tip)
        self.color_manual_pair = self._compact_pair(
            "Min", self.color_min_spin, "Max", self.color_max_spin, "colorManualPair"
        )
        self._add_processing_row(
            processing_form, "Percentile", self.color_percentile_pair, "color_percentile"
        )
        self._add_processing_row(
            processing_form, "Manual range", self.color_manual_pair, "color_manual"
        )
        processing_layout.addLayout(processing_form)
        self.processing_summary = QtWidgets.QLabel("Raw signed values - linear")
        self.processing_summary.setObjectName("processingSummary")
        self.processing_summary.setWordWrap(True)
        processing_layout.addWidget(self.processing_summary)
        reset_processing = QtWidgets.QPushButton("Reset processing")
        reset_processing.clicked.connect(self.reset_processing)
        processing_layout.addWidget(reset_processing)
        root.addWidget(processing_section)

        reconstruction_section, reconstruction_layout = self._inspector_section("RECONSTRUCTION")
        self.reconstruction_section = reconstruction_section
        self.timing_label = QtWidgets.QLabel("Timing valid: —")
        self.timing_label.setObjectName("fieldLabel")
        reconstruction_layout.addWidget(self.timing_label)
        qc_grid = QtWidgets.QGridLayout()
        qc_grid.setContentsMargins(0, 4, 0, 0)
        qc_grid.setHorizontalSpacing(14)
        qc_grid.setVerticalSpacing(5)
        self.qc_values: dict[str, QtWidgets.QLabel] = {}
        self._qc_labels: dict[str, QtWidgets.QLabel] = {}
        for row, name in enumerate(
            (
                "Row period",
                "Point period",
                "Unused / row",
                "Valid pixels",
                "0 samples",
                "1 sample",
                "Median samples/pixel",
                "P10 samples/pixel",
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
            self._qc_labels[name] = label
        reconstruction_layout.addLayout(qc_grid)
        self.qc_label = QtWidgets.QLabel("")
        self.qc_label.setObjectName("warningLabel")
        self.qc_label.setWordWrap(True)
        self.qc_label.setVisible(False)
        reconstruction_layout.addWidget(self.qc_label)
        self.export_reconstructed_button = QtWidgets.QPushButton("Export reconstructed map")
        self.export_reconstructed_button.setEnabled(False)
        self.export_reconstructed_button.clicked.connect(self.exportRawRequested)
        reconstruction_layout.addWidget(self.export_reconstructed_button)
        root.addWidget(reconstruction_section)
        root.addStretch(1)

        for geometry_widget in (
            self.rows_spin,
            self.cols_spin,
            self.scan_combo,
            self.first_row_check,
            self.aggregation_combo,
            self.rows_apart_spin,
            self.row_offset_spin,
            self.points_apart_spin,
            self.point_offset_spin,
            self.x_period_offset_spin,
            self.y_phase_spin,
            self.x_phase_spin,
            self.window_fraction_spin,
            self.window_duration_spin,
        ):
            if isinstance(geometry_widget, QtWidgets.QComboBox):
                geometry_widget.currentIndexChanged.connect(self.geometryChanged)
            elif isinstance(geometry_widget, QtWidgets.QCheckBox):
                geometry_widget.stateChanged.connect(self.geometryChanged)
            else:
                geometry_widget.valueChanged.connect(self.geometryChanged)
        self.rows_spin.valueChanged.connect(self._update_offset_ranges)
        self.cols_spin.valueChanged.connect(self._update_offset_ranges)
        self.points_apart_spin.valueChanged.connect(self._sync_point_period_from_anchors)
        self.method_combo.currentIndexChanged.connect(self._method_changed)
        self.window_mode_combo.currentIndexChanged.connect(self._phase_window_changed)
        for spin in (self.row_a_spin, self.row_b_spin, self.point_a_spin, self.point_b_spin):
            spin.valueChanged.connect(self._mark_anchors_user_edited)
            spin.editingFinished.connect(self._anchor_spin_finished)
        self.point_period_spin.editingFinished.connect(self._point_period_finished)
        for combo in (
            self.transform_combo,
            self.baseline_combo,
            self.normalization_combo,
            self.scale_combo,
        ):
            combo.currentIndexChanged.connect(self._processing_changed)
        self.color_range_combo.currentIndexChanged.connect(self._color_controls_changed)
        for processing_spin in (
            self.baseline_value_spin,
            self.baseline_percentile_spin,
            self.normalization_reference_spin,
        ):
            processing_spin.editingFinished.connect(self._processing_changed)
        for color_spin in (
            self.percentile_low_spin,
            self.percentile_high_spin,
            self.color_min_spin,
            self.color_max_spin,
        ):
            color_spin.editingFinished.connect(self._color_controls_changed)
        self.custom_expression_edit.editingFinished.connect(self._processing_changed)
        self._update_processing_fields()
        self._update_phase_window_fields()

    @staticmethod
    def _inspector_section(title: str) -> tuple[QtWidgets.QFrame, QtWidgets.QVBoxLayout]:
        section = QtWidgets.QFrame()
        section.setObjectName("inspectorSection")
        layout = QtWidgets.QVBoxLayout(section)
        layout.setContentsMargins(11, 10, 11, 10)
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
    def _form_layout() -> QtWidgets.QFormLayout:
        form = QtWidgets.QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(12)
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
        form.setRowWrapPolicy(QtWidgets.QFormLayout.RowWrapPolicy.WrapLongRows)
        return form

    @staticmethod
    def _add_form_row(
        form: QtWidgets.QFormLayout,
        label: str,
        widget: QtWidgets.QWidget,
        tooltip: str | None = None,
    ) -> None:
        label_widget = QtWidgets.QLabel(label)
        label_widget.setObjectName("fieldLabel")
        if tooltip:
            label_widget.setToolTip(tooltip)
            widget.setToolTip(tooltip)
        form.addRow(label_widget, widget)

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
            self._processing_rows[key] = (label_widget, widget)

    @staticmethod
    def _compact_labeled_control(
        label: str, control: QtWidgets.QWidget, object_name: str
    ) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        widget.setObjectName(object_name)
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        label_widget = QtWidgets.QLabel(label)
        label_widget.setObjectName("fieldLabel")
        layout.addWidget(label_widget)
        layout.addWidget(control, 1)
        return widget

    @staticmethod
    def _compact_pair(
        left_label: str,
        left: QtWidgets.QWidget,
        right_label: str,
        right: QtWidgets.QWidget,
        object_name: str,
    ) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        widget.setObjectName(object_name)
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        for label, control in ((left_label, left), (right_label, right)):
            item = QtWidgets.QLabel(label)
            item.setObjectName("fieldLabel")
            layout.addWidget(item)
            layout.addWidget(control)
        return widget

    @staticmethod
    def _int_spin(value: int, minimum: int, maximum: int) -> QtWidgets.QSpinBox:
        spin = QtWidgets.QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        spin.setFixedWidth(82)
        return spin

    @staticmethod
    def _float_spin() -> QtWidgets.QDoubleSpinBox:
        spin = QtWidgets.QDoubleSpinBox()
        spin.setDecimals(3)
        spin.setRange(-1e15, 1e15)
        spin.setSingleStep(0.01)
        spin.setSuffix(" s")
        spin.setKeyboardTracking(False)
        spin.setFixedWidth(104)
        return spin

    @staticmethod
    def _value_spin() -> QtWidgets.QDoubleSpinBox:
        spin = QtWidgets.QDoubleSpinBox()
        spin.setDecimals(12)
        spin.setRange(-1e15, 1e15)
        spin.setSingleStep(1.0)
        spin.setButtonSymbols(QtWidgets.QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        spin.setKeyboardTracking(False)
        spin.setFixedWidth(104)
        return spin

    @staticmethod
    def _percent_spin(value: float) -> QtWidgets.QDoubleSpinBox:
        spin = QtWidgets.QDoubleSpinBox()
        spin.setDecimals(1)
        spin.setRange(0.0, 100.0)
        spin.setValue(value)
        spin.setSingleStep(0.1)
        spin.setSuffix(" %")
        spin.setButtonSymbols(QtWidgets.QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        spin.setKeyboardTracking(False)
        spin.setFixedWidth(94)
        return spin

    @staticmethod
    def _phase_spin(value: float) -> QtWidgets.QDoubleSpinBox:
        """Return a compact phase editor whose visible range is ``[0, 100)``."""

        spin = ReconstructionInspector._percent_spin(value)
        spin.setMaximum(99.9)
        spin.setToolTip("Phase wraps at 100%; use the arrows for 0.1% adjustment.")
        return spin

    @staticmethod
    def _slider_spin_control(
        spin: QtWidgets.QDoubleSpinBox,
        minimum: int,
        maximum: int,
        scale: float,
        object_name: str,
    ) -> QtWidgets.QWidget:
        control = QtWidgets.QWidget()
        control.setObjectName(object_name)
        layout = QtWidgets.QHBoxLayout(control)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setMinimumWidth(80)
        slider.setValue(round(spin.value() * scale))
        spin.valueChanged.connect(lambda value: slider.setValue(round(value * scale)))
        slider.valueChanged.connect(lambda value: spin.setValue(value / scale))
        layout.addWidget(spin)
        layout.addWidget(slider, 1)
        return control

    @staticmethod
    def _enum_combo(items: tuple[tuple[str, EnumT], ...]) -> QtWidgets.QComboBox:
        combo = QtWidgets.QComboBox()
        for label, value in items:
            combo.addItem(label, value)
        return combo

    @staticmethod
    def _enum_value(combo: QtWidgets.QComboBox, _enum_type: type[EnumT]) -> EnumT:
        return combo.currentData()

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().resizeEvent(event)
        self._refresh_file_label()

    def _refresh_file_label(self) -> None:
        available = max(0, self.file_label.contentsRect().width())
        self.file_label.setText(
            self.file_label.fontMetrics().elidedText(
                getattr(self, "_file_name", "No file loaded"),
                QtCore.Qt.TextElideMode.ElideRight,
                available,
            )
        )

    def set_export_availability(
        self, raw_available: bool, processed_available: bool, source_available: bool
    ) -> None:
        self.export_button.setEnabled(raw_available or source_available)
        self.raw_export_action.setEnabled(raw_available)
        self.processed_export_action.setEnabled(processed_available)
        self.both_export_action.setEnabled(raw_available and processed_available)
        self.project_export_action.setEnabled(source_available)
        self.summary_export_action.setEnabled(source_available)
        self.pdf_export_action.setEnabled(raw_available)
        self.export_reconstructed_button.setEnabled(raw_available)

    @property
    def anchors_user_edited(self) -> bool:
        return self._anchors_user_edited

    def _mark_anchors_user_edited(self, *_args: object) -> None:
        if self._has_data and not self._syncing:
            self._anchors_user_edited = True

    def mark_anchors_user_edited(self) -> None:
        self._anchors_user_edited = True

    def set_file_name(self, filename: str | None) -> None:
        if filename is None:
            self._file_name = "No file loaded"
        else:
            self._file_name = filename
        self.file_label.setToolTip(self._file_name)
        self._refresh_file_label()

    def set_signal_names(self, names: tuple[str, ...], preferred: str | None = None) -> None:
        self.signal_combo.blockSignals(True)
        self.signal_combo.clear()
        self.signal_combo.addItems(names)
        if preferred:
            self.signal_combo.setCurrentText(preferred)
        self.signal_combo.blockSignals(False)

    def restore_project_state(self, state: ProjectState, raw_scale: float) -> None:
        """Restore semantic state without producing intermediate UI signals."""

        widgets = (
            self.signal_combo,
            self.method_combo,
            self.rows_spin,
            self.cols_spin,
            self.scan_combo,
            self.first_row_check,
            self.flip_y_check,
            self.aggregation_combo,
            self.row_a_spin,
            self.row_b_spin,
            self.rows_apart_spin,
            self.row_offset_spin,
            self.point_a_spin,
            self.point_b_spin,
            self.points_apart_spin,
            self.point_offset_spin,
            self.x_period_offset_spin,
            self.y_phase_spin,
            self.x_phase_spin,
            self.window_mode_combo,
            self.window_fraction_spin,
            self.window_duration_spin,
            self.transform_combo,
            self.baseline_combo,
            self.normalization_combo,
            self.scale_combo,
            self.color_range_combo,
            self.baseline_value_spin,
            self.baseline_percentile_spin,
            self.custom_expression_edit,
            self.normalization_reference_spin,
            self.percentile_low_spin,
            self.percentile_high_spin,
            self.color_min_spin,
            self.color_max_spin,
        )
        blockers = [QtCore.QSignalBlocker(widget) for widget in widgets]
        try:
            self.signal_combo.setCurrentText(state.signal)
            self._set_combo_value(self.method_combo, state.method)
            self.rows_spin.setValue(state.rows)
            self.cols_spin.setValue(state.columns)
            self._update_offset_ranges()
            self._set_combo_value(self.scan_combo, state.scan_pattern)
            self.first_row_check.setChecked(state.first_row_ltr)
            self.flip_y_check.setChecked(state.flip_y)
            self._set_combo_value(self.aggregation_combo, state.aggregation)
            self.row_a_spin.setValue(state.row_a_s)
            self.row_b_spin.setValue(state.row_b_s)
            self.rows_apart_spin.setValue(state.rows_apart)
            self.row_offset_spin.setValue(state.row_offset)
            self.point_a_spin.setValue(state.point_a_s)
            self.point_b_spin.setValue(state.point_b_s)
            self.points_apart_spin.setValue(state.points_apart)
            self.point_offset_spin.setValue(state.point_offset)
            self.x_period_offset_spin.setValue(state.x_period_offset)
            self.y_phase_spin.setValue(state.y_phase_fraction * 100.0)
            self.x_phase_spin.setValue(state.x_phase_fraction * 100.0)
            self._set_combo_value(self.window_mode_combo, state.window_mode)
            self.window_fraction_spin.setValue(state.window_fraction * 100.0)
            self.window_duration_spin.setValue(state.window_duration_s or 0.0)
            config = state.processing
            self._set_combo_value(self.transform_combo, config.transform)
            self._set_combo_value(self.baseline_combo, config.baseline_mode)
            self._set_combo_value(self.normalization_combo, config.normalization)
            self._set_combo_value(self.scale_combo, config.value_scale)
            self._set_combo_value(self.color_range_combo, config.color_range_mode)
            reference_scale = (
                raw_scale
                if config.transform
                in (ValueTransform.RAW, ValueTransform.ABSOLUTE, ValueTransform.NEGATE)
                else 1.0
            )
            processed_scale = (
                1.0
                if config.transform is ValueTransform.CUSTOM
                or config.normalization is not NormalizationMode.NONE
                or config.value_scale is ValueScale.LOG10
                else raw_scale
            )
            self.baseline_value_spin.setValue((config.baseline_value or 0.0) * raw_scale)
            self.baseline_percentile_spin.setValue(config.baseline_percentile)
            self.custom_expression_edit.setText(config.custom_expression)
            self.normalization_reference_spin.setValue(
                (config.normalization_reference or 0.0) * reference_scale
            )
            self.percentile_low_spin.setValue(config.percentile_low)
            self.percentile_high_spin.setValue(config.percentile_high)
            self.color_min_spin.setValue((config.color_min or 0.0) * processed_scale)
            self.color_max_spin.setValue((config.color_max or 0.0) * processed_scale)
            self._sync_point_period_from_anchors()
            self._update_processing_fields()
            self._update_phase_window_fields()
            self._anchors_user_edited = True
        finally:
            del blockers

    @staticmethod
    def _set_combo_value(combo: QtWidgets.QComboBox, value: object) -> None:
        index = combo.findData(value)
        if index < 0:
            raise ValueError(f"Project contains unsupported UI value: {value!r}")
        combo.setCurrentIndex(index)

    def set_anchor_bounds(self, data: TimeSeriesData, *, reset: bool = True) -> None:
        """Apply the loaded trace range and, for a new file, useful timing defaults."""
        self._has_data = True
        if reset:
            self._anchors_user_edited = False
        lower, upper = float(data.time_s[0]), float(data.time_s[-1])
        span = max(upper - lower, 0.0)
        spins = (self.row_a_spin, self.row_b_spin, self.point_a_spin, self.point_b_spin)
        for spin in spins:
            spin.blockSignals(True)
            spin.setRange(lower, upper)
            spin.setSingleStep(min(0.01, max(span / 1000.0, 1e-12)))

        defaults: tuple[float, float, float, float]
        if reset and span > 0.0:
            row_a = lower + 0.20 * span
            row_b = lower + 0.70 * span
            point_a = lower + 0.05 * span
            point_gap = span / max(100.0, float(self.cols_spin.value()) * 4.0)
            point_b = min(upper, point_a + point_gap)
            if point_b <= point_a:
                point_a, point_b = lower, upper
            defaults = (row_a, row_b, point_a, point_b)
        elif reset:
            defaults = (lower, lower, lower, lower)
        else:
            defaults = (
                float(min(max(spins[0].value(), lower), upper)),
                float(min(max(spins[1].value(), lower), upper)),
                float(min(max(spins[2].value(), lower), upper)),
                float(min(max(spins[3].value(), lower), upper)),
            )

        for spin, value in zip(spins, defaults):
            spin.setValue(value)
            spin.blockSignals(False)
        self._update_offset_ranges()
        self._sync_point_period_from_anchors()

    def initialize_geometry_aware_anchors(self, data: TimeSeriesData) -> bool:
        """Fit automatic timing anchors inside the trace once geometry is known."""
        if self._anchors_user_edited or self.rows_spin.value() <= 0 or self.cols_spin.value() <= 0:
            return False
        lower, upper = float(data.time_s[0]), float(data.time_s[-1])
        span = upper - lower
        if span <= 0.0:
            return False

        rows = self.rows_spin.value()
        cols = self.cols_spin.value()
        row_period = 0.90 * span / rows
        row_a = lower + 0.05 * span
        maximum_rows_apart = max(1, int((upper - row_a) // row_period))
        rows_apart = min(self.rows_apart_spin.value(), maximum_rows_apart)
        point_a = row_a + 0.05 * row_period
        points_apart = self.points_apart_spin.value()
        point_period = 0.80 * row_period / max(cols, points_apart)
        row_b = row_a + rows_apart * row_period
        point_b = min(upper, point_a + points_apart * point_period)

        widgets = (
            self.rows_apart_spin,
            self.row_a_spin,
            self.row_b_spin,
            self.point_a_spin,
            self.point_b_spin,
        )
        for widget in widgets:
            widget.blockSignals(True)
        self.rows_apart_spin.setValue(rows_apart)
        self.row_a_spin.setValue(row_a)
        self.row_b_spin.setValue(row_b)
        self.point_a_spin.setValue(point_a)
        self.point_b_spin.setValue(point_b)
        for widget in widgets:
            widget.blockSignals(False)
        self._sync_point_period_from_anchors()
        return True

    def _update_offset_ranges(self, *_args: object) -> None:
        row_max = max(0, self.rows_spin.value() - 1)
        point_max = max(0, self.cols_spin.value() - 1)
        self.row_offset_spin.setRange(0, row_max)
        self.point_offset_spin.setRange(0, point_max)
        self.x_period_offset_spin.setRange(0, 100000)

    def _method_changed(self, *_args: object) -> None:
        if (
            self.method_combo.currentData() == "dual_offset_phase_window"
            and self.x_period_offset_spin.value() == 0
            and self.x_phase_spin.value() == 0.0
        ):
            self.x_phase_spin.setValue(47.5)
        self._update_phase_window_fields()
        self.registrationChanged.emit()

    def _phase_window_changed(self, *_args: object) -> None:
        self._update_phase_window_fields()
        self.registrationChanged.emit()

    def _update_phase_window_fields(self) -> None:
        phase_window = self.method_combo.currentData() == "dual_offset_phase_window"
        self.convert_phase_button.setVisible(not phase_window)
        self.phase_window_section.setVisible(phase_window)
        y_phase_row = self.y_phase_control.parentWidget()
        if y_phase_row is not None:
            y_phase_row.setVisible(phase_window)
        self.point_offset_control.setVisible(not phase_window)
        self.x_offset_control.setVisible(phase_window)
        x_phase_row = self.x_phase_control.parentWidget()
        if x_phase_row is not None:
            x_phase_row.setVisible(phase_window)
        fixed = WindowMode(self.window_mode_combo.currentData()) is WindowMode.FIXED_DURATION
        self.window_fraction_row.setVisible(phase_window and not fixed)
        self.window_duration_row.setVisible(phase_window and fixed)

    def _sync_point_period_from_anchors(self, *_args: object) -> None:
        period = (
            self.point_b_spin.value() - self.point_a_spin.value()
        ) / self.points_apart_spin.value()
        if period <= 0:
            return
        self.point_period_spin.blockSignals(True)
        self.point_period_spin.setValue(period)
        self.point_period_spin.blockSignals(False)

    def _anchor_spin_finished(self) -> None:
        if self._syncing:
            return
        self.mark_anchors_user_edited()
        self._sync_point_period_from_anchors()
        self.registrationChanged.emit()

    def _point_period_finished(self) -> None:
        if not self._has_data or self._syncing:
            return
        self.mark_anchors_user_edited()
        point_b = (
            self.point_a_spin.value()
            + self.points_apart_spin.value() * self.point_period_spin.value()
        )
        self.pointPeriodEdited.emit(float(point_b))

    def set_point_b_value(self, value: float) -> None:
        self._syncing = True
        self.point_b_spin.setValue(value)
        self._syncing = False
        self._sync_point_period_from_anchors()

    def current_params(self) -> DualOffsetParams | PhaseWindowParams:
        if self.method_combo.currentData() == "dual_offset_phase_window":
            return PhaseWindowParams(
                rows=self.rows_spin.value(),
                cols=self.cols_spin.value(),
                row_a_s=self.row_a_spin.value(),
                row_b_s=self.row_b_spin.value(),
                rows_apart=self.rows_apart_spin.value(),
                row_offset=self.row_offset_spin.value(),
                y_phase_fraction=self.y_phase_spin.value() / 100.0,
                point_a_s=self.point_a_spin.value(),
                point_b_s=self.point_b_spin.value(),
                points_apart=self.points_apart_spin.value(),
                x_period_offset=self.x_period_offset_spin.value(),
                x_phase_fraction=self.x_phase_spin.value() / 100.0,
                window_mode=self.window_mode_combo.currentData(),
                window_fraction=self.window_fraction_spin.value() / 100.0,
                window_duration_s=self.window_duration_spin.value(),
                scan_pattern=ScanPattern(self.scan_combo.currentData()),
                first_row_ltr=self.first_row_check.isChecked(),
                aggregation=Aggregation(self.aggregation_combo.currentData()),
            )
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
            scan_pattern=ScanPattern(self.scan_combo.currentData()),
            first_row_ltr=self.first_row_check.isChecked(),
            use_median=Aggregation(self.aggregation_combo.currentData()) is Aggregation.MEDIAN,
        )

    def current_processing_config(
        self, raw_scale: float, reference_scale: float, processed_scale: float
    ) -> MapProcessingConfig:
        return MapProcessingConfig(
            baseline_mode=self._enum_value(self.baseline_combo, BaselineMode),
            baseline_value=self.baseline_value_spin.value() / raw_scale,
            baseline_percentile=self.baseline_percentile_spin.value(),
            transform=self._enum_value(self.transform_combo, ValueTransform),
            custom_expression=self.custom_expression_edit.text().strip() or "x",
            normalization=self._enum_value(self.normalization_combo, NormalizationMode),
            normalization_reference=self.normalization_reference_spin.value() / reference_scale,
            value_scale=self._enum_value(self.scale_combo, ValueScale),
            color_range_mode=self._enum_value(self.color_range_combo, ColorRangeMode),
            color_min=self.color_min_spin.value() / processed_scale,
            color_max=self.color_max_spin.value() / processed_scale,
            percentile_low=self.percentile_low_spin.value(),
            percentile_high=self.percentile_high_spin.value(),
        )

    def processing_enum(self, enum_type: type[EnumT]) -> EnumT:
        return self._enum_value(self.transform_combo, enum_type)  # type: ignore[arg-type]

    def set_processing_units(
        self,
        raw_unit: DisplayUnit,
        normalization_reference_unit: DisplayUnit,
        processed_unit: DisplayUnit,
    ) -> None:
        dimensionless = not processed_unit.unit
        labels = {
            "baseline_value": ("Baseline value", raw_unit.unit),
            "normalization_reference": (
                "Normalization reference",
                normalization_reference_unit.unit,
            ),
            "color_manual": ("Manual range", "" if dimensionless else processed_unit.unit),
        }
        for key, (label, unit) in labels.items():
            row = self._processing_rows[key]
            row[0].setText(f"{label} ({unit})" if unit else label)

    def _processing_changed(self, *_args: object) -> None:
        self._update_processing_fields()
        self.processingChanged.emit()

    def _color_controls_changed(self, *_args: object) -> None:
        self._update_processing_fields()
        self.colorLimitsChanged.emit()

    def _update_processing_fields(self) -> None:
        baseline = self._enum_value(self.baseline_combo, BaselineMode)
        transform = self._enum_value(self.transform_combo, ValueTransform)
        normalization = self._enum_value(self.normalization_combo, NormalizationMode)
        color_range = self._enum_value(self.color_range_combo, ColorRangeMode)
        self._set_processing_row_visible("baseline_value", baseline is BaselineMode.MANUAL)
        self._set_processing_row_visible("baseline_percentile", baseline is BaselineMode.PERCENTILE)
        self._set_processing_row_visible("custom_expression", transform is ValueTransform.CUSTOM)
        self._set_processing_row_visible(
            "normalization_reference", normalization is NormalizationMode.REFERENCE
        )
        self._set_processing_row_visible(
            "color_percentile", color_range is ColorRangeMode.PERCENTILE
        )
        self._set_processing_row_visible("color_manual", color_range is ColorRangeMode.MANUAL)

    def _set_processing_row_visible(self, key: str, visible: bool) -> None:
        row = self._processing_rows[key]
        row[0].setVisible(visible)
        row[1].setVisible(visible)

    def reset_processing(self) -> None:
        for combo in (
            self.transform_combo,
            self.baseline_combo,
            self.normalization_combo,
            self.scale_combo,
            self.color_range_combo,
        ):
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
        self._update_processing_fields()
        self.processingChanged.emit()

    def set_timing_solution(
        self, row_period: float, point_period: float, unused: float, *, phase_window: bool = False
    ) -> None:
        self.timing_label.setText("Timing valid: ✓")
        self.qc_values["Row period"].setText(f"{row_period:.4f} s")
        self.qc_values["Point period"].setText(f"{point_period:.4f} s")
        self._qc_labels["Unused / row"].setText(
            "Point-train slack / row" if phase_window else "Unused / row"
        )
        self.qc_values["Unused / row"].setText(f"{unused:.3f} s")

    def set_qc(
        self,
        valid_percent: float,
        median_samples: float,
        zero_percent: float,
        one_percent: float,
        p10_samples: float,
    ) -> None:
        self.qc_values["Valid pixels"].setText(f"{valid_percent:.0f} %")
        self.qc_values["0 samples"].setText(f"{zero_percent:.1f} %")
        self.qc_values["1 sample"].setText(f"{one_percent:.1f} %")
        self.qc_values["Median samples/pixel"].setText(f"{median_samples:.3g}")
        self.qc_values["P10 samples/pixel"].setText(f"{p10_samples:.3g}")

    def set_warning(self, message: str) -> None:
        self.qc_label.setText(message)
        self.qc_label.setVisible(bool(message))

    def clear_qc(self, message: str) -> None:
        self.timing_label.setText("Timing valid: no")
        for value in self.qc_values.values():
            value.setText("—")
        self.set_warning(message)

    def set_processing_summary(self, text: str) -> None:
        self.processing_summary.setText(text)
