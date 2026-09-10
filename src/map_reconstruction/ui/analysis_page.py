"""Stage-three map analysis controls and scientific display workspace."""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets  # type: ignore[import-not-found]

from map_reconstruction.display_units import DisplayUnit
from map_reconstruction.processing import (
    BaselineMode,
    ColorRangeMode,
    MapProcessingConfig,
    NormalizationMode,
    ValueScale,
    ValueTransform,
)


class MapAnalysisPage(QtWidgets.QWidget):
    """Own post-reconstruction processing and display-only figure controls."""

    displayChanged = QtCore.Signal()
    processingChanged = QtCore.Signal()
    colorLimitsChanged = QtCore.Signal()
    exportProcessedRequested = QtCore.Signal()
    exportSummaryRequested = QtCore.Signal()
    exportPdfRequested = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("mapAnalysisPage")
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(14)
        sidebar = QtWidgets.QFrame()
        sidebar.setObjectName("stageSidebar")
        layout = QtWidgets.QVBoxLayout(sidebar)
        self.sidebar_layout = layout
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(7)
        self._rows: dict[str, tuple[QtWidgets.QLabel, QtWidgets.QWidget]] = {}

        layout.addWidget(self._header("VALUE PROCESSING"))
        form = QtWidgets.QFormLayout()
        form.setVerticalSpacing(6)
        self.transform_combo = self._combo(
            (
                ("Raw signed", ValueTransform.RAW),
                ("Absolute value", ValueTransform.ABSOLUTE),
                ("Negate", ValueTransform.NEGATE),
                ("Custom expression", ValueTransform.CUSTOM),
            )
        )
        self.baseline_combo = self._combo(
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
        self.normalization_combo = self._combo(
            (
                ("None", NormalizationMode.NONE),
                ("Max magnitude", NormalizationMode.MAX_MAGNITUDE),
                ("Min-max", NormalizationMode.MIN_MAX),
                ("Reference", NormalizationMode.REFERENCE),
            )
        )
        self.scale_combo = self._combo((("Linear", ValueScale.LINEAR), ("Log10", ValueScale.LOG10)))
        self.custom_expression_edit = QtWidgets.QLineEdit("x")
        self.custom_expression_edit.setPlaceholderText("e.g. abs(x) * 2")
        self.baseline_value_spin = self._value_spin()
        self.baseline_percentile_spin = self._percent_spin(50.0)
        self.normalization_reference_spin = self._value_spin()
        self._add_row(form, "Value transform", self.transform_combo, "transform")
        self._add_row(form, "Expression", self.custom_expression_edit, "custom")
        self._add_row(form, "Map offset", self.baseline_combo, "offset")
        self._add_row(form, "Manual offset", self.baseline_value_spin, "offset_value")
        self._add_row(form, "Percentile", self.baseline_percentile_spin, "offset_percentile")
        self._add_row(form, "Normalization", self.normalization_combo, "normalization")
        self._add_row(form, "Reference", self.normalization_reference_spin, "reference")
        self._add_row(form, "Scale", self.scale_combo, "scale")
        layout.addLayout(form)

        layout.addSpacing(8)
        layout.addWidget(self._header("FIGURE"))
        figure = QtWidgets.QFormLayout()
        self.palette_combo = QtWidgets.QComboBox()
        self.palette_combo.addItems(
            ("Viridis", "Plasma", "Inferno", "Magma", "Cividis", "Grayscale")
        )
        self.color_range_combo = self._combo(
            (
                ("Auto", ColorRangeMode.AUTO),
                ("Percentile", ColorRangeMode.PERCENTILE),
                ("Manual", ColorRangeMode.MANUAL),
            )
        )
        self.percentile_low_spin = self._percent_spin(1.0)
        self.percentile_high_spin = self._percent_spin(99.0)
        self.color_min_spin = self._value_spin()
        self.color_max_spin = self._value_spin()
        self.color_percentile_pair = self._pair(
            "Low", self.percentile_low_spin, "High", self.percentile_high_spin
        )
        self.color_manual_pair = self._pair("Min", self.color_min_spin, "Max", self.color_max_spin)
        self._add_row(figure, "Palette", self.palette_combo, "palette")
        self._add_row(figure, "Color limits", self.color_range_combo, "color_range")
        self._add_row(figure, "Percentile", self.color_percentile_pair, "color_percentile")
        self._add_row(figure, "Manual range", self.color_manual_pair, "color_manual")
        layout.addLayout(figure)
        self.flip_y_check = QtWidgets.QCheckBox("Flip Y")
        layout.addWidget(self.flip_y_check)
        layout.addSpacing(8)
        layout.addWidget(self._header("EXPORT"))
        self.export_processed_button = QtWidgets.QPushButton("Export processed map")
        self.export_figure_button = QtWidgets.QPushButton("Export parameter summary")
        self.export_report_button = QtWidgets.QPushButton("Export report")
        layout.addWidget(self.export_processed_button)
        layout.addWidget(self.export_figure_button)
        layout.addWidget(self.export_report_button)
        layout.addStretch(1)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll.setMinimumWidth(300)
        scroll.setWidget(sidebar)
        root.addWidget(scroll, 0)
        self.views_host = QtWidgets.QWidget()
        self.views_layout = QtWidgets.QVBoxLayout(self.views_host)
        self.views_layout.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.views_host, 1)

        for processing_combo in (
            self.transform_combo,
            self.baseline_combo,
            self.normalization_combo,
            self.scale_combo,
        ):
            processing_combo.currentIndexChanged.connect(self._processing_changed)
        self.custom_expression_edit.editingFinished.connect(self._processing_changed)
        for processing_spin in (
            self.baseline_value_spin,
            self.baseline_percentile_spin,
            self.normalization_reference_spin,
        ):
            processing_spin.editingFinished.connect(self.processingChanged)
        self.palette_combo.currentIndexChanged.connect(self.displayChanged)
        self.flip_y_check.stateChanged.connect(self.displayChanged)
        self.color_range_combo.currentIndexChanged.connect(self._color_changed)
        for color_spin in (
            self.percentile_low_spin,
            self.percentile_high_spin,
            self.color_min_spin,
            self.color_max_spin,
        ):
            color_spin.editingFinished.connect(self.colorLimitsChanged)
        self.export_processed_button.clicked.connect(self.exportProcessedRequested)
        self.export_figure_button.clicked.connect(self.exportSummaryRequested)
        self.export_report_button.clicked.connect(self.exportPdfRequested)
        self._update_visibility()

    @staticmethod
    def _header(text: str) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text)
        label.setObjectName("sectionHeader")
        return label

    @staticmethod
    def _combo(items: tuple[tuple[str, object], ...]) -> QtWidgets.QComboBox:
        combo = QtWidgets.QComboBox()
        for label, value in items:
            combo.addItem(label, value)
        return combo

    @staticmethod
    def _value_spin() -> QtWidgets.QDoubleSpinBox:
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(-1e15, 1e15)
        spin.setDecimals(12)
        spin.setKeyboardTracking(False)
        return spin

    @staticmethod
    def _percent_spin(value: float) -> QtWidgets.QDoubleSpinBox:
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(0.0, 100.0)
        spin.setDecimals(2)
        spin.setSuffix(" %")
        spin.setValue(value)
        spin.setKeyboardTracking(False)
        return spin

    @staticmethod
    def _pair(
        left: str, first: QtWidgets.QWidget, right: str, second: QtWidgets.QWidget
    ) -> QtWidgets.QWidget:
        host = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(QtWidgets.QLabel(left))
        layout.addWidget(first, 1)
        layout.addWidget(QtWidgets.QLabel(right))
        layout.addWidget(second, 1)
        return host

    def _add_row(
        self, form: QtWidgets.QFormLayout, label: str, widget: QtWidgets.QWidget, key: str
    ) -> None:
        label_widget = QtWidgets.QLabel(label)
        form.addRow(label_widget, widget)
        self._rows[key] = (label_widget, widget)

    def _set_visible(self, key: str, visible: bool) -> None:
        label, widget = self._rows[key]
        label.setVisible(visible)
        widget.setVisible(visible)

    def _processing_changed(self) -> None:
        self._update_visibility()
        self.processingChanged.emit()

    def _color_changed(self) -> None:
        self._update_visibility()
        self.colorLimitsChanged.emit()

    def _update_visibility(self) -> None:
        self._set_visible(
            "custom", ValueTransform(self.transform_combo.currentData()) == ValueTransform.CUSTOM
        )
        offset = BaselineMode(self.baseline_combo.currentData())
        self._set_visible("offset_value", offset == BaselineMode.MANUAL)
        self._set_visible("offset_percentile", offset == BaselineMode.PERCENTILE)
        self._set_visible(
            "reference",
            NormalizationMode(self.normalization_combo.currentData())
            == NormalizationMode.REFERENCE,
        )
        color = ColorRangeMode(self.color_range_combo.currentData())
        self._set_visible("color_percentile", color == ColorRangeMode.PERCENTILE)
        self._set_visible("color_manual", color == ColorRangeMode.MANUAL)

    def current_processing_config(
        self, raw_scale: float, reference_scale: float, display_scale: float
    ) -> MapProcessingConfig:
        return MapProcessingConfig(
            transform=ValueTransform(self.transform_combo.currentData()),
            custom_expression=self.custom_expression_edit.text(),
            baseline_mode=BaselineMode(self.baseline_combo.currentData()),
            baseline_value=self.baseline_value_spin.value() / raw_scale,
            baseline_percentile=self.baseline_percentile_spin.value(),
            normalization=NormalizationMode(self.normalization_combo.currentData()),
            normalization_reference=self.normalization_reference_spin.value() / reference_scale,
            value_scale=ValueScale(self.scale_combo.currentData()),
            color_range_mode=ColorRangeMode(self.color_range_combo.currentData()),
            percentile_low=self.percentile_low_spin.value(),
            percentile_high=self.percentile_high_spin.value(),
            color_min=self.color_min_spin.value() / display_scale,
            color_max=self.color_max_spin.value() / display_scale,
        )

    def set_processing_units(
        self, raw: DisplayUnit, reference: DisplayUnit, display: DisplayUnit
    ) -> None:
        self.baseline_value_spin.setSuffix(f" {raw.unit}" if raw.unit else "")
        self.normalization_reference_spin.setSuffix(f" {reference.unit}" if reference.unit else "")
        for spin in (self.color_min_spin, self.color_max_spin):
            spin.setSuffix(f" {display.unit}" if display.unit else "")

    def set_processing_config(self, config: MapProcessingConfig, raw_scale: float) -> None:
        """Restore persisted map-processing state into the stage-three owner."""
        widgets = (
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
            for combo, value in (
                (self.transform_combo, config.transform),
                (self.baseline_combo, config.baseline_mode),
                (self.normalization_combo, config.normalization),
                (self.scale_combo, config.value_scale),
                (self.color_range_combo, config.color_range_mode),
            ):
                combo.setCurrentIndex(combo.findData(value))
            reference_scale = (
                raw_scale
                if config.transform
                in (ValueTransform.RAW, ValueTransform.ABSOLUTE, ValueTransform.NEGATE)
                else 1.0
            )
            display_scale = (
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
            self.color_min_spin.setValue((config.color_min or 0.0) * display_scale)
            self.color_max_spin.setValue((config.color_max or 0.0) * display_scale)
            self._update_visibility()
        finally:
            del blockers
