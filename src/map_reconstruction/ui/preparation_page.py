"""Signal Preparation page controls and diagnostic trace."""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg  # type: ignore[import-not-found, import-untyped]
from PySide6 import QtCore, QtWidgets  # type: ignore[import-not-found]

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
    """Compact stage-one controls; scientific work is delegated to the headless pipeline."""

    configurationChanged = QtCore.Signal()
    exportRequested = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("signalPreparationPage")
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
        form = QtWidgets.QFormLayout()
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(6)
        self.signal_combo = QtWidgets.QComboBox()
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItem("None", DarkCorrectionMode.NONE)
        self.mode_combo.addItem("Constant", DarkCorrectionMode.CONSTANT)
        self.mode_combo.addItem("Manual dark regions", DarkCorrectionMode.MANUAL_REGIONS)
        self.mode_combo.addItem("Rolling quantile", DarkCorrectionMode.ROLLING_QUANTILE)
        self.constant_baseline_spin = QtWidgets.QDoubleSpinBox()
        self.constant_baseline_spin.setRange(-1e15, 1e15)
        self.constant_baseline_spin.setDecimals(8)
        self.constant_baseline_spin.setSingleStep(0.1)
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
        self.quantile_spin = QtWidgets.QDoubleSpinBox()
        self.quantile_spin.setRange(0.0, 100.0)
        self.quantile_spin.setDecimals(1)
        self.quantile_spin.setSuffix(" %")
        self.quantile_spin.setValue(90.0)
        self.window_spin = QtWidgets.QDoubleSpinBox()
        self.window_spin.setRange(1e-9, 1e15)
        self.window_spin.setDecimals(3)
        self.window_spin.setSuffix(" s")
        self.window_spin.setValue(10.0)
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
        form.addRow("Signal", self.signal_combo)
        form.addRow("Dark correction", self.mode_combo)
        form.addRow("Constant baseline", self.constant_baseline_spin)
        form.addRow("Manual fit", self.fit_combo)
        form.addRow("Response direction", self.direction_combo)
        form.addRow("Quantile", self.quantile_spin)
        form.addRow("Time window", self.window_spin)
        form.addRow("Trend", self.trend_combo)
        form.addRow("Output convention", self.output_combo)
        side_layout.addLayout(form)
        self.value_gate_check = QtWidgets.QCheckBox("Enable value gate")
        self.gate_min_spin = QtWidgets.QDoubleSpinBox()
        self.gate_max_spin = QtWidgets.QDoubleSpinBox()
        for spin in (self.gate_min_spin, self.gate_max_spin):
            spin.setRange(-1e15, 1e15)
            spin.setDecimals(8)
        side_layout.addWidget(self.value_gate_check)
        gate_form = QtWidgets.QFormLayout()
        gate_form.addRow("Min", self.gate_min_spin)
        gate_form.addRow("Max", self.gate_max_spin)
        side_layout.addLayout(gate_form)
        self.add_region_button = QtWidgets.QPushButton("+ Add dark region")
        self.clear_regions_button = QtWidgets.QPushButton("Clear all regions")
        self.export_button = QtWidgets.QPushButton("Export prepared trace")
        self.export_button.clicked.connect(self.exportRequested)
        self.region_list = QtWidgets.QListWidget()
        self._regions: list[DarkRegion] = []
        self._region_items: list[pg.LinearRegionItem] = []
        self.region_list.setMaximumHeight(100)
        side_layout.addWidget(self.add_region_button)
        side_layout.addWidget(self.clear_regions_button)
        side_layout.addWidget(self.export_button)
        side_layout.addWidget(self.region_list)
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
        for widget in self.findChildren(QtWidgets.QWidget):
            if widget is not self.region_list and widget is not self.signal_combo:
                if isinstance(widget, QtWidgets.QComboBox):
                    widget.currentIndexChanged.connect(lambda _=0: self.configurationChanged.emit())
        self.mode_combo.currentIndexChanged.connect(lambda _=0: self.configurationChanged.emit())
        for spin in (
            self.constant_baseline_spin,
            self.quantile_spin,
            self.window_spin,
            self.gate_min_spin,
            self.gate_max_spin,
        ):
            spin.valueChanged.connect(lambda _=0: self.configurationChanged.emit())
        self.value_gate_check.toggled.connect(self.configurationChanged)
        self.add_region_button.clicked.connect(self._add_region)
        self.clear_regions_button.clicked.connect(self._clear_regions)

    def set_signals(self, names: tuple[str, ...], preferred: str | None = None) -> None:
        self.signal_combo.blockSignals(True)
        self.signal_combo.clear()
        self.signal_combo.addItems(names)
        if preferred:
            self.signal_combo.setCurrentText(preferred)
        self.signal_combo.blockSignals(False)

    def configuration(self) -> SignalPreparationConfig:
        return SignalPreparationConfig(
            dark_correction_mode=self.mode_combo.currentData(),
            constant_baseline=self.constant_baseline_spin.value(),
            manual_region_fit=self.fit_combo.currentData(),
            manual_dark_regions=tuple(self._regions),
            rolling_quantile=self.quantile_spin.value() / 100.0,
            rolling_window_s=self.window_spin.value(),
            rolling_trend=self.trend_combo.currentData(),
            response_direction=self.direction_combo.currentData(),
            value_gate_enabled=self.value_gate_check.isChecked(),
            value_gate_min=self.gate_min_spin.value(),
            value_gate_max=self.gate_max_spin.value(),
            output_convention=self.output_combo.currentData(),
        )

    def set_diagnostics(self, text: str) -> None:
        self.diagnostics.setText(text)

    def _add_region(self) -> None:
        """Add a conservative starter region; the trace view can refine it later."""

        start = self._regions[-1].end_s if self._regions else 0.0
        region = DarkRegion(start, start + max(self.window_spin.value(), 1.0))
        self._regions.append(region)
        self._create_region_item(region)
        self._refresh_region_list()
        self.configurationChanged.emit()

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

    def _refresh_region_list(self) -> None:
        self.region_list.clear()
        for index, region in enumerate(self._regions, start=1):
            self.region_list.addItem(f"Region {index}   {region.start_s:g} – {region.end_s:g} s")

    def _regions_drag_finished(self) -> None:
        updated: list[DarkRegion] = []
        for item in self._region_items:
            left, right = item.getRegion()
            if right > left:
                updated.append(DarkRegion(float(left), float(right)))
        self._regions = updated
        self._refresh_region_list()
        self.configurationChanged.emit()

    def _remove_region_items(self) -> None:
        for item in self._region_items:
            self.trace_plot.removeItem(item)
        self._region_items.clear()

    def _clear_regions(self) -> None:
        self._regions.clear()
        self._remove_region_items()
        self._refresh_region_list()
        self.configurationChanged.emit()

    def set_regions(self, regions: tuple[DarkRegion, ...]) -> None:
        self._remove_region_items()
        self._regions = list(regions)
        for region in self._regions:
            self._create_region_item(region)
        self._refresh_region_list()

    def set_source(self, time_s: np.ndarray, values: np.ndarray) -> None:
        self.raw_curve.setData(time_s, values)

    def set_prepared(self, prepared: object | None) -> None:
        if prepared is None:
            self.prepared_curve.clear()
            self.baseline_curve.clear()
            return
        time_s = np.asarray(getattr(prepared, "time_s"), dtype=float)
        self.prepared_curve.setData(time_s, np.asarray(getattr(prepared, "values"), dtype=float))
        baseline = getattr(prepared, "baseline")
        if baseline is None:
            self.baseline_curve.clear()
        else:
            self.baseline_curve.setData(time_s, np.asarray(baseline, dtype=float))
