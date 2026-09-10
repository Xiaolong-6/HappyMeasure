"""Signal Preparation page controls and diagnostic trace."""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg  # type: ignore[import-not-found, import-untyped]
from PySide6 import QtCore, QtWidgets  # type: ignore[import-not-found]

from map_reconstruction.display_units import DisplayUnit
from map_reconstruction.preparation import (
    DarkCorrectionMode,
    DarkRegion,
    ManualRegionFit,
    OutputConvention,
    PhotocurrentPolarity,
    RollingTrend,
    SignalPreparationConfig,
)


class SignalPreparationPage(QtWidgets.QWidget):
    """Stage-one controls with one authoritative, editable preparation state."""

    configurationChanged = QtCore.Signal()
    exportRequested = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("signalPreparationPage")
        self._value_scale = 1.0
        self._source_bounds: tuple[float, float] | None = None
        self._source_value_range_si: tuple[float, float] | None = None
        self._syncing = False

        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(14)

        sidebar = QtWidgets.QFrame()
        sidebar.setObjectName("stageSidebar")
        side_layout = QtWidgets.QVBoxLayout(sidebar)
        side_layout.setContentsMargins(12, 10, 12, 10)
        side_layout.setSpacing(7)

        title = QtWidgets.QLabel("Signal Preparation")
        title.setObjectName("pageTitle")
        side_layout.addWidget(title)
        description = QtWidgets.QLabel("Define the time-domain signal used by reconstruction.")
        description.setObjectName("mutedText")
        description.setWordWrap(True)
        side_layout.addWidget(description)

        self._form_rows: dict[str, tuple[QtWidgets.QLabel, QtWidgets.QWidget]] = {}
        form = QtWidgets.QFormLayout()
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(6)

        self.signal_combo = QtWidgets.QComboBox()
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItem("None", DarkCorrectionMode.NONE)
        self.mode_combo.addItem("Constant", DarkCorrectionMode.CONSTANT)
        self.mode_combo.addItem("Manual dark regions", DarkCorrectionMode.MANUAL_REGIONS)
        self.mode_combo.addItem("Rolling quantile", DarkCorrectionMode.ROLLING_QUANTILE)

        self.constant_baseline_spin = self._value_spin()
        self.fit_combo = QtWidgets.QComboBox()
        for label, fit_value in (
            ("Constant", ManualRegionFit.CONSTANT),
            ("Linear", ManualRegionFit.LINEAR),
            ("Quadratic", ManualRegionFit.QUADRATIC),
        ):
            self.fit_combo.addItem(label, fit_value)

        self.direction_combo = QtWidgets.QComboBox()
        self.direction_combo.addItem("Negative photocurrent", PhotocurrentPolarity.NEGATIVE)
        self.direction_combo.addItem("Positive photocurrent", PhotocurrentPolarity.POSITIVE)
        self.direction_combo.setToolTip(
            "Selects which side of each rolling time bin is treated as the dark-current envelope."
        )

        self.quantile_spin = QtWidgets.QDoubleSpinBox()
        self.quantile_spin.setRange(50.0, 100.0)
        self.quantile_spin.setDecimals(1)
        self.quantile_spin.setSuffix(" %")
        self.quantile_spin.setValue(90.0)
        self.quantile_spin.setKeyboardTracking(False)

        self.window_spin = QtWidgets.QDoubleSpinBox()
        self.window_spin.setRange(1e-9, 1e15)
        self.window_spin.setDecimals(6)
        self.window_spin.setSuffix(" s")
        self.window_spin.setValue(10.0)
        self.window_spin.setKeyboardTracking(False)

        self.trend_combo = QtWidgets.QComboBox()
        for label, trend_value in (
            ("Piecewise linear", RollingTrend.PIECEWISE_LINEAR),
            ("Linear", RollingTrend.LINEAR),
            ("Quadratic", RollingTrend.QUADRATIC),
        ):
            self.trend_combo.addItem(label, trend_value)

        self.output_combo = QtWidgets.QComboBox()
        self.output_combo.addItem("Measured - dark", OutputConvention.MEASURED_MINUS_DARK)
        self.output_combo.addItem("Dark - measured", OutputConvention.DARK_MINUS_MEASURED)

        self._add_form_row(form, "Signal", self.signal_combo, "signal")
        self._add_form_row(form, "Dark correction", self.mode_combo, "mode")
        self._add_form_row(form, "Constant baseline", self.constant_baseline_spin, "constant")
        self._add_form_row(form, "Manual fit", self.fit_combo, "manual_fit")
        self._add_form_row(form, "Response direction", self.direction_combo, "direction")
        self._add_form_row(form, "Quantile", self.quantile_spin, "quantile")
        self._add_form_row(form, "Time window", self.window_spin, "window")
        self._add_form_row(form, "Trend", self.trend_combo, "trend")
        self._add_form_row(form, "Output convention", self.output_combo, "output")
        side_layout.addLayout(form)

        self.value_gate_check = QtWidgets.QCheckBox("Enable value gate")
        self.gate_min_spin = self._value_spin()
        self.gate_max_spin = self._value_spin()
        self.gate_host = QtWidgets.QWidget()
        gate_layout = QtWidgets.QVBoxLayout(self.gate_host)
        gate_layout.setContentsMargins(0, 0, 0, 0)
        gate_layout.setSpacing(4)
        gate_layout.addWidget(self.value_gate_check)
        gate_form = QtWidgets.QFormLayout()
        self.gate_min_label = QtWidgets.QLabel("Min")
        self.gate_max_label = QtWidgets.QLabel("Max")
        gate_form.addRow(self.gate_min_label, self.gate_min_spin)
        gate_form.addRow(self.gate_max_label, self.gate_max_spin)
        gate_layout.addLayout(gate_form)
        side_layout.addWidget(self.gate_host)

        self.manual_host = QtWidgets.QWidget()
        manual_layout = QtWidgets.QVBoxLayout(self.manual_host)
        manual_layout.setContentsMargins(0, 0, 0, 0)
        manual_layout.setSpacing(5)
        manual_help = QtWidgets.QLabel(
            "Add a dark region, then drag the blue band or select it below and edit Start/End."
        )
        manual_help.setObjectName("mutedText")
        manual_help.setWordWrap(True)
        manual_layout.addWidget(manual_help)

        region_buttons = QtWidgets.QHBoxLayout()
        self.add_region_button = QtWidgets.QPushButton("+ Add region")
        self.remove_region_button = QtWidgets.QPushButton("Remove selected")
        self.clear_regions_button = QtWidgets.QPushButton("Clear all")
        region_buttons.addWidget(self.add_region_button)
        region_buttons.addWidget(self.remove_region_button)
        region_buttons.addWidget(self.clear_regions_button)
        manual_layout.addLayout(region_buttons)

        self.region_list = QtWidgets.QListWidget()
        self.region_list.setMaximumHeight(100)
        manual_layout.addWidget(self.region_list)

        region_editor = QtWidgets.QFormLayout()
        self.region_start_spin = self._time_spin()
        self.region_end_spin = self._time_spin()
        region_editor.addRow("Start", self.region_start_spin)
        region_editor.addRow("End", self.region_end_spin)
        manual_layout.addLayout(region_editor)
        side_layout.addWidget(self.manual_host)

        self.export_button = QtWidgets.QPushButton("Export prepared trace")
        self.export_button.clicked.connect(self.exportRequested)
        side_layout.addWidget(self.export_button)
        side_layout.addStretch(1)

        sidebar_scroll = QtWidgets.QScrollArea()
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        sidebar_scroll.setMinimumSize(300, 0)
        sidebar_scroll.setWidget(sidebar)
        root.addWidget(sidebar_scroll, 0)

        trace_host = QtWidgets.QWidget()
        trace_layout = QtWidgets.QVBoxLayout(trace_host)
        trace_layout.setContentsMargins(0, 0, 0, 0)
        self.trace_plot = pg.PlotWidget()
        self.trace_plot.setBackground("#FFFFFF")
        self.trace_plot.setTitle("Raw / prepared time trace")
        self.trace_plot.showGrid(x=True, y=True, alpha=0.2)
        self.raw_curve = self.trace_plot.plot(
            [], [], pen=pg.mkPen("#3F4854", width=1.1), name="Raw"
        )
        self.baseline_curve = self.trace_plot.plot(
            [], [], pen=pg.mkPen("#D97706", width=1.5), name="Baseline"
        )
        self.prepared_curve = self.trace_plot.plot(
            [], [], pen=pg.mkPen("#2563EB", width=1.2), name="Prepared"
        )
        trace_layout.addWidget(self.trace_plot, 1)
        self.diagnostics = QtWidgets.QLabel("No prepared signal")
        self.diagnostics.setObjectName("preparationDiagnostics")
        self.diagnostics.setWordWrap(True)
        trace_layout.addWidget(self.diagnostics)
        root.addWidget(trace_host, 1)

        self._regions: list[DarkRegion] = []
        self._region_items: list[pg.LinearRegionItem] = []

        self.mode_combo.currentIndexChanged.connect(self._mode_changed)
        for combo in (self.fit_combo, self.direction_combo, self.trend_combo, self.output_combo):
            combo.currentIndexChanged.connect(self._emit_configuration_changed)
        for spin in (
            self.constant_baseline_spin,
            self.quantile_spin,
            self.window_spin,
            self.gate_min_spin,
            self.gate_max_spin,
        ):
            spin.editingFinished.connect(self._emit_configuration_changed)
        self.value_gate_check.toggled.connect(self._emit_configuration_changed)
        self.add_region_button.clicked.connect(self._add_region)
        self.remove_region_button.clicked.connect(self._remove_selected_region)
        self.clear_regions_button.clicked.connect(self._clear_regions)
        self.region_list.currentRowChanged.connect(self._region_selection_changed)
        self.region_start_spin.editingFinished.connect(self._region_editor_finished)
        self.region_end_spin.editingFinished.connect(self._region_editor_finished)
        self._update_mode_visibility()
        self._update_region_editor_enabled()

    @staticmethod
    def _value_spin() -> QtWidgets.QDoubleSpinBox:
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(-1e15, 1e15)
        spin.setDecimals(12)
        spin.setSingleStep(0.1)
        spin.setKeyboardTracking(False)
        spin.setMinimumWidth(120)
        return spin

    @staticmethod
    def _time_spin() -> QtWidgets.QDoubleSpinBox:
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(-1e15, 1e15)
        spin.setDecimals(6)
        spin.setSingleStep(0.01)
        spin.setSuffix(" s")
        spin.setKeyboardTracking(False)
        return spin

    def _add_form_row(
        self, form: QtWidgets.QFormLayout, label: str, widget: QtWidgets.QWidget, key: str
    ) -> None:
        label_widget = QtWidgets.QLabel(label)
        form.addRow(label_widget, widget)
        self._form_rows[key] = (label_widget, widget)

    def _set_form_row_visible(self, key: str, visible: bool) -> None:
        label, widget = self._form_rows[key]
        label.setVisible(visible)
        widget.setVisible(visible)

    def _mode_changed(self, _index: int = 0) -> None:
        self._update_mode_visibility()
        self._emit_configuration_changed()

    def _update_mode_visibility(self) -> None:
        mode = self.mode_combo.currentData()
        active = mode is not DarkCorrectionMode.NONE
        manual = mode is DarkCorrectionMode.MANUAL_REGIONS
        rolling = mode is DarkCorrectionMode.ROLLING_QUANTILE
        self._set_form_row_visible("constant", mode is DarkCorrectionMode.CONSTANT)
        self._set_form_row_visible("manual_fit", manual)
        self._set_form_row_visible("direction", rolling)
        self._set_form_row_visible("quantile", rolling)
        self._set_form_row_visible("window", rolling)
        self._set_form_row_visible("trend", rolling)
        self._set_form_row_visible("output", active)
        self.manual_host.setVisible(manual)
        self.gate_host.setVisible(manual or rolling)

    def _emit_configuration_changed(self, *_args: object) -> None:
        if not self._syncing:
            self.configurationChanged.emit()

    def set_signals(self, names: tuple[str, ...], preferred: str | None = None) -> None:
        self.signal_combo.blockSignals(True)
        self.signal_combo.clear()
        self.signal_combo.addItems(names)
        if preferred:
            self.signal_combo.setCurrentText(preferred)
        self.signal_combo.blockSignals(False)

    def set_display_unit(self, display_unit: DisplayUnit) -> None:
        """Use engineering units in numeric editors while retaining SI configuration values."""

        self._value_scale = float(display_unit.scale) if display_unit.scale else 1.0
        suffix = f" {display_unit.unit}" if display_unit.unit else ""
        self.constant_baseline_spin.setSuffix(suffix)
        self.gate_min_spin.setSuffix(suffix)
        self.gate_max_spin.setSuffix(suffix)
        self.trace_plot.setLabel("left", display_unit.axis_label)
        label = f"Constant baseline ({display_unit.unit})" if display_unit.unit else "Constant baseline"
        self._form_rows["constant"][0].setText(label)
        self.gate_min_label.setText(f"Min ({display_unit.unit})" if display_unit.unit else "Min")
        self.gate_max_label.setText(f"Max ({display_unit.unit})" if display_unit.unit else "Max")

    def set_configuration(self, config: SignalPreparationConfig) -> None:
        """Restore one complete configuration without emitting intermediate states."""

        self._syncing = True
        widgets = (
            self.mode_combo,
            self.constant_baseline_spin,
            self.fit_combo,
            self.direction_combo,
            self.quantile_spin,
            self.window_spin,
            self.trend_combo,
            self.output_combo,
            self.value_gate_check,
            self.gate_min_spin,
            self.gate_max_spin,
        )
        blockers = [QtCore.QSignalBlocker(widget) for widget in widgets]
        try:
            self.mode_combo.setCurrentIndex(self.mode_combo.findData(config.dark_correction_mode))
            self.constant_baseline_spin.setValue(config.constant_baseline * self._value_scale)
            self.fit_combo.setCurrentIndex(self.fit_combo.findData(config.manual_region_fit))
            self.direction_combo.setCurrentIndex(
                self.direction_combo.findData(config.response_direction)
            )
            self.quantile_spin.setValue(config.rolling_quantile * 100.0)
            self.window_spin.setValue(config.rolling_window_s)
            self.trend_combo.setCurrentIndex(self.trend_combo.findData(config.rolling_trend))
            self.output_combo.setCurrentIndex(self.output_combo.findData(config.output_convention))
            self.value_gate_check.setChecked(config.value_gate_enabled)
            if np.isfinite(config.value_gate_min):
                gate_min = config.value_gate_min
            elif self._source_value_range_si is not None:
                gate_min = self._source_value_range_si[0]
            else:
                gate_min = 0.0
            if np.isfinite(config.value_gate_max):
                gate_max = config.value_gate_max
            elif self._source_value_range_si is not None:
                gate_max = self._source_value_range_si[1]
            else:
                gate_max = 0.0
            self.gate_min_spin.setValue(gate_min * self._value_scale)
            self.gate_max_spin.setValue(gate_max * self._value_scale)
            self.set_regions(config.manual_dark_regions)
            self._update_mode_visibility()
        finally:
            del blockers
            self._syncing = False

    def configuration(self) -> SignalPreparationConfig:
        scale = self._value_scale or 1.0
        gate_enabled = self.value_gate_check.isChecked()
        return SignalPreparationConfig(
            dark_correction_mode=self.mode_combo.currentData(),
            constant_baseline=self.constant_baseline_spin.value() / scale,
            manual_region_fit=self.fit_combo.currentData(),
            manual_dark_regions=tuple(self._regions),
            rolling_quantile=self.quantile_spin.value() / 100.0,
            rolling_window_s=self.window_spin.value(),
            rolling_trend=self.trend_combo.currentData(),
            response_direction=self.direction_combo.currentData(),
            value_gate_enabled=gate_enabled,
            value_gate_min=self.gate_min_spin.value() / scale if gate_enabled else -np.inf,
            value_gate_max=self.gate_max_spin.value() / scale if gate_enabled else np.inf,
            output_convention=self.output_combo.currentData(),
        )

    def set_diagnostics(self, text: str) -> None:
        self.diagnostics.setText(text)

    def _add_region(self) -> None:
        if self._source_bounds is None:
            self.set_diagnostics("Load a signal before adding dark regions.")
            return
        lower, upper = self._source_bounds
        span = upper - lower
        if span <= 0:
            self.set_diagnostics("The loaded signal has no selectable time span.")
            return
        width = max(span * 0.10, min(span, 1e-6))
        if self._regions:
            start = min(max(self._regions[-1].end_s, lower), max(lower, upper - width))
        else:
            start = lower
        end = min(upper, start + width)
        if end <= start:
            start = max(lower, upper - width)
            end = upper
        region = DarkRegion(start, end)
        self._regions.append(region)
        self._create_region_item(region)
        self._refresh_region_list(select_row=len(self._regions) - 1)
        self._emit_configuration_changed()

    def _create_region_item(self, region: DarkRegion) -> None:
        item = pg.LinearRegionItem(
            values=(region.start_s, region.end_s),
            movable=True,
            brush=pg.mkBrush(37, 99, 235, 35),
            pen=pg.mkPen("#2563EB", width=1),
        )
        item.sigRegionChangeFinished.connect(self._regions_drag_finished)
        self.trace_plot.addItem(item)
        self._region_items.append(item)

    def _refresh_region_list(self, select_row: int | None = None) -> None:
        previous = self.region_list.currentRow() if select_row is None else select_row
        blocker = QtCore.QSignalBlocker(self.region_list)
        self.region_list.clear()
        for index, region in enumerate(self._regions, start=1):
            self.region_list.addItem(f"Region {index}   {region.start_s:g} – {region.end_s:g} s")
        if self._regions and previous >= 0:
            self.region_list.setCurrentRow(min(previous, len(self._regions) - 1))
        del blocker
        self._region_selection_changed(self.region_list.currentRow())

    def _clamp_region(self, left: float, right: float) -> DarkRegion | None:
        if self._source_bounds is not None:
            lower, upper = self._source_bounds
            left = min(max(left, lower), upper)
            right = min(max(right, lower), upper)
        if right <= left:
            return None
        return DarkRegion(float(left), float(right))

    def _regions_drag_finished(self) -> None:
        updated: list[DarkRegion] = []
        for item in self._region_items:
            left, right = item.getRegion()
            region = self._clamp_region(float(left), float(right))
            if region is not None:
                updated.append(region)
                item.setRegion((region.start_s, region.end_s))
        self._regions = updated
        self._refresh_region_list()
        self._emit_configuration_changed()

    def _remove_region_items(self) -> None:
        for item in self._region_items:
            self.trace_plot.removeItem(item)
        self._region_items.clear()

    def _remove_selected_region(self) -> None:
        row = self.region_list.currentRow()
        if row < 0 or row >= len(self._regions):
            return
        item = self._region_items.pop(row)
        self.trace_plot.removeItem(item)
        self._regions.pop(row)
        self._refresh_region_list(select_row=min(row, len(self._regions) - 1))
        self._emit_configuration_changed()

    def _clear_regions(self) -> None:
        self._regions.clear()
        self._remove_region_items()
        self._refresh_region_list(select_row=-1)
        self._emit_configuration_changed()

    def _region_selection_changed(self, row: int) -> None:
        valid = 0 <= row < len(self._regions)
        self._update_region_editor_enabled(valid)
        if not valid:
            return
        region = self._regions[row]
        blockers = [
            QtCore.QSignalBlocker(self.region_start_spin),
            QtCore.QSignalBlocker(self.region_end_spin),
        ]
        self.region_start_spin.setValue(region.start_s)
        self.region_end_spin.setValue(region.end_s)
        del blockers

    def _update_region_editor_enabled(self, enabled: bool | None = None) -> None:
        if enabled is None:
            row = self.region_list.currentRow()
            enabled = 0 <= row < len(self._regions)
        self.region_start_spin.setEnabled(enabled)
        self.region_end_spin.setEnabled(enabled)
        self.remove_region_button.setEnabled(enabled)

    def _region_editor_finished(self) -> None:
        row = self.region_list.currentRow()
        if row < 0 or row >= len(self._regions):
            return
        region = self._clamp_region(self.region_start_spin.value(), self.region_end_spin.value())
        if region is None:
            self._region_selection_changed(row)
            self.set_diagnostics("Dark-region Start must be smaller than End.")
            return
        self._regions[row] = region
        self._region_items[row].setRegion((region.start_s, region.end_s))
        self._refresh_region_list(select_row=row)
        self._emit_configuration_changed()

    def set_regions(self, regions: tuple[DarkRegion, ...]) -> None:
        self._remove_region_items()
        self._regions = list(regions)
        for region in self._regions:
            self._create_region_item(region)
        self._refresh_region_list(select_row=0 if self._regions else -1)

    def set_source(self, time_s: np.ndarray, values: np.ndarray) -> None:
        time = np.asarray(time_s, dtype=float)
        signal = np.asarray(values, dtype=float)
        self.raw_curve.setData(time, signal * self._value_scale)
        if time.size:
            lower, upper = float(time[0]), float(time[-1])
            self._source_bounds = (lower, upper)
            for spin in (self.region_start_spin, self.region_end_spin):
                spin.setRange(lower, upper)
                spin.setSingleStep(max((upper - lower) / 1000.0, 1e-9))
        finite = signal[np.isfinite(signal)]
        self._source_value_range_si = (
            (float(np.min(finite)), float(np.max(finite))) if finite.size else None
        )

    def set_prepared(self, prepared: object | None) -> None:
        if prepared is None:
            self.prepared_curve.clear()
            self.baseline_curve.clear()
            return
        time_s = np.asarray(getattr(prepared, "time_s"), dtype=float)
        self.prepared_curve.setData(
            time_s, np.asarray(getattr(prepared, "values"), dtype=float) * self._value_scale
        )
        baseline = getattr(prepared, "baseline")
        if baseline is None:
            self.baseline_curve.clear()
        else:
            self.baseline_curve.setData(
                time_s, np.asarray(baseline, dtype=float) * self._value_scale
            )
