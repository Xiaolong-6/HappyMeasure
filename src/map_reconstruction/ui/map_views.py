"""Map, sample-count, and distribution views for the Map Reconstruction UI."""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg  # type: ignore[import-not-found, import-untyped]
from PySide6 import QtCore, QtWidgets  # type: ignore[import-not-found]

from map_reconstruction.display_units import DisplayUnit, to_display_values
from map_reconstruction.processing import ProcessedMap
from map_reconstruction.qc.distribution import (
    HistogramBinMode,
    HistogramConfig,
    HistogramRangeMode,
    make_histogram_data,
)
from map_reconstruction.ui.style import (
    BORDER,
    GRID_MAJOR,
    PANEL,
    PRIMARY_TEXT,
    SECONDARY_TEXT,
)


class MapViews(QtWidgets.QWidget):
    """Own the right-side scientific map and QC plots."""

    distributionControlsChanged = QtCore.Signal()
    useMapLimitsRequested = QtCore.Signal()

    def __init__(
        self, parent: QtWidgets.QWidget | None = None, *, presentation: str = "reconstruction"
    ) -> None:
        super().__init__(parent)
        if presentation not in {"reconstruction", "analysis"}:
            raise ValueError(f"Unsupported map presentation: {presentation!r}")
        self.presentation = presentation
        self.setMinimumSize(0, 0)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Ignored
        )
        self._build_ui()

    def _build_ui(self) -> None:
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
        (
            self.distribution_stack,
            self.distribution_plot,
            self.distribution_bars,
            self.mean_line,
            self.median_line,
            self.distribution_stats,
        ) = self._make_distribution_panel()
        self.qc_tabs: QtWidgets.QTabWidget | None = None
        if self.presentation == "reconstruction":
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(0, 0, 0, 0)
            self.map_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
            root.addWidget(self.map_splitter)
            self.qc_tabs = QtWidgets.QTabWidget()
            self.qc_tabs.setDocumentMode(True)
            self.qc_tabs.addTab(self.count_stack, "Samples / pixel")
            self.qc_tabs.addTab(self.distribution_stack, "Distribution")
            self.map_splitter.addWidget(self.map_stack)
            self.map_splitter.addWidget(self.qc_tabs)
            self.map_splitter.setStretchFactor(0, 1)
            self.map_splitter.setStretchFactor(1, 1)
        self._set_loaded(False)

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

    def _make_empty_panel(self, title: str, message: str) -> QtWidgets.QFrame:
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
        return panel

    def _make_image_panel(
        self, title: str, empty_title: str, empty_message: str, scale_label: str
    ) -> tuple[QtWidgets.QStackedWidget, pg.PlotWidget, pg.ImageItem, pg.ColorBarItem]:
        stack = QtWidgets.QStackedWidget()
        stack.addWidget(self._make_empty_panel(empty_title, empty_message))
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

    def _make_distribution_panel(self):
        stack = QtWidgets.QStackedWidget()
        stack.addWidget(
            self._make_empty_panel(
                "Value distribution", "A histogram of finite processed values appears here."
            )
        )
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        controls = QtWidgets.QWidget()
        controls.setObjectName("distributionControls")
        controls_layout = QtWidgets.QGridLayout(controls)
        controls_layout.setContentsMargins(5, 4, 5, 0)
        controls_layout.setHorizontalSpacing(6)
        controls_layout.setVerticalSpacing(4)
        self.distribution_range_combo = QtWidgets.QComboBox()
        self.distribution_range_combo.addItem("Range: Auto", HistogramRangeMode.AUTO)
        self.distribution_range_combo.addItem("Range: Manual", HistogramRangeMode.MANUAL)
        self.distribution_bin_combo = QtWidgets.QComboBox()
        self.distribution_bin_combo.addItem("Bins: Auto", HistogramBinMode.AUTO)
        self.distribution_bin_combo.addItem("Bins: Count", HistogramBinMode.COUNT)
        self.distribution_bin_combo.addItem("Bins: Width", HistogramBinMode.WIDTH)
        self.distribution_min_spin = self._distribution_value_spin()
        self.distribution_max_spin = self._distribution_value_spin()
        self.distribution_count_spin = QtWidgets.QSpinBox()
        self.distribution_count_spin.setRange(1, 10_000)
        self.distribution_count_spin.setValue(50)
        self.distribution_width_spin = self._distribution_value_spin()
        self.distribution_width_spin.setMinimum(1e-12)
        self.distribution_width_spin.setValue(1.0)
        self.use_map_limits_button = QtWidgets.QPushButton("Use map limits")
        controls_layout.addWidget(self.distribution_range_combo, 0, 0)
        controls_layout.addWidget(self.distribution_bin_combo, 0, 1)
        controls_layout.addWidget(QtWidgets.QLabel("Min"), 1, 0)
        controls_layout.addWidget(self.distribution_min_spin, 1, 1)
        controls_layout.addWidget(QtWidgets.QLabel("Max"), 1, 2)
        controls_layout.addWidget(self.distribution_max_spin, 1, 3)
        controls_layout.addWidget(self.use_map_limits_button, 1, 4)
        controls_layout.addWidget(QtWidgets.QLabel("Count"), 2, 0)
        controls_layout.addWidget(self.distribution_count_spin, 2, 1)
        controls_layout.addWidget(QtWidgets.QLabel("Bin width"), 2, 2)
        controls_layout.addWidget(self.distribution_width_spin, 2, 3)
        layout.addWidget(controls)
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
        self._distribution_control_widgets = {
            "manual": tuple(
                controls_layout.itemAtPosition(row, column).widget()
                for row, column in ((1, 0), (1, 1), (1, 2), (1, 3), (1, 4))
            ),
            "count": (controls_layout.itemAtPosition(2, 0).widget(), self.distribution_count_spin),
            "width": (controls_layout.itemAtPosition(2, 2).widget(), self.distribution_width_spin),
        }
        self.distribution_range_combo.currentIndexChanged.connect(
            self._distribution_controls_changed
        )
        self.distribution_bin_combo.currentIndexChanged.connect(self._distribution_controls_changed)
        self.distribution_min_spin.editingFinished.connect(self.distributionControlsChanged)
        self.distribution_max_spin.editingFinished.connect(self.distributionControlsChanged)
        self.distribution_count_spin.valueChanged.connect(self.distributionControlsChanged)
        self.distribution_width_spin.editingFinished.connect(self.distributionControlsChanged)
        self.use_map_limits_button.clicked.connect(self.useMapLimitsRequested)
        self._update_distribution_control_visibility()
        return stack, plot, bars, mean_line, median_line, stats

    @staticmethod
    def _distribution_value_spin() -> QtWidgets.QDoubleSpinBox:
        spin = QtWidgets.QDoubleSpinBox()
        spin.setDecimals(6)
        spin.setRange(-1e9, 1e9)
        spin.setSingleStep(0.1)
        spin.setButtonSymbols(QtWidgets.QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        spin.setKeyboardTracking(False)
        spin.setMinimumWidth(84)
        return spin

    def _distribution_controls_changed(self) -> None:
        self._update_distribution_control_visibility()
        self.distributionControlsChanged.emit()

    def _update_distribution_control_visibility(self) -> None:
        manual = (
            HistogramRangeMode(self.distribution_range_combo.currentData())
            is HistogramRangeMode.MANUAL
        )
        bin_mode = HistogramBinMode(self.distribution_bin_combo.currentData())
        for widget in self._distribution_control_widgets["manual"]:
            widget.setVisible(manual)
        for widget in self._distribution_control_widgets["count"]:
            widget.setVisible(bin_mode is HistogramBinMode.COUNT)
        for widget in self._distribution_control_widgets["width"]:
            widget.setVisible(bin_mode is HistogramBinMode.WIDTH)

    def histogram_config(self, display_scale: float) -> HistogramConfig:
        manual = (
            HistogramRangeMode(self.distribution_range_combo.currentData())
            is HistogramRangeMode.MANUAL
        )
        return HistogramConfig(
            range_mode=self.distribution_range_combo.currentData(),
            minimum=self.distribution_min_spin.value() / display_scale if manual else None,
            maximum=self.distribution_max_spin.value() / display_scale if manual else None,
            bin_mode=self.distribution_bin_combo.currentData(),
            bin_count=self.distribution_count_spin.value(),
            bin_width=self.distribution_width_spin.value() / display_scale,
        )

    def set_manual_distribution_range(self, minimum: float, maximum: float) -> None:
        blockers = [
            QtCore.QSignalBlocker(widget)
            for widget in (
                self.distribution_range_combo,
                self.distribution_min_spin,
                self.distribution_max_spin,
            )
        ]
        try:
            self.distribution_range_combo.setCurrentIndex(1)
            self.distribution_min_spin.setValue(minimum)
            self.distribution_max_spin.setValue(maximum)
        finally:
            del blockers
        self._update_distribution_control_visibility()
        self.distributionControlsChanged.emit()

    def _set_loaded(self, loaded: bool) -> None:
        index = 1 if loaded else 0
        self.map_stack.setCurrentIndex(index)
        self.count_stack.setCurrentIndex(index)
        if not loaded:
            self.clear_distribution()

    def set_loaded(self, loaded: bool) -> None:
        """Switch all map/QC stacks between empty and loaded states."""

        self._set_loaded(loaded)

    def show_processed_map(
        self,
        values: np.ndarray,
        display_unit: DisplayUnit,
        levels: tuple[float, float] | None,
        flip_y: bool,
        label: str,
    ) -> bool:
        display = to_display_values(values, display_unit)
        if flip_y:
            display = np.flipud(display)
        if not np.isfinite(display).any():
            self.map_image.clear()
            self.show_empty_map("No finite processed values", "Adjust processing settings.")
            return False
        self.map_image.setImage(display, autoLevels=levels is None, levels=levels)
        self.map_plot.enableAutoRange()
        self.map_color_bar.setLabel("right", label, enableAutoSIPrefix=False)
        self.map_color_bar.getAxis("right").enableAutoSIPrefix(False)
        if levels is not None:
            self.map_color_bar.setLevels(levels)
        self.map_stack.setCurrentIndex(1)
        return True

    def set_palette(self, palette: str, *, inverted: bool = False) -> None:
        """Change only the map rendering palette; scientific arrays are untouched."""

        names = {
            "Viridis": "viridis",
            "Plasma": "plasma",
            "Inferno": "inferno",
            "Magma": "magma",
            "Cividis": "CET-L17",
            "Grayscale": "gray",
        }
        try:
            source_map = pg.colormap.get(names.get(palette, "viridis"))
            colors = source_map.getLookupTable(0.0, 1.0, 256)
            if inverted:
                colors = colors[::-1]
            color_map = pg.ColorMap(np.linspace(0.0, 1.0, len(colors)), colors)
        except Exception:  # pragma: no cover - backend-specific colormap registry
            return
        self.map_color_bar.setColorMap(color_map)

    def show_sample_counts(self, values: np.ndarray, flip_y: bool) -> None:
        display = np.asarray(values, dtype=float)
        if flip_y:
            display = np.flipud(display)
        finite = display[np.isfinite(display)]
        if finite.size == 0:
            self.count_image.clear()
            self.count_stack.setCurrentIndex(0)
            return
        low, high = float(np.min(finite)), float(np.max(finite))
        levels = (low - 0.5, high + 0.5) if low == high else (low, high)
        self.count_image.setImage(display, autoLevels=False, levels=levels)
        self.count_color_bar.setLevels(levels)
        ticks = np.arange(int(np.ceil(low)), int(np.floor(high)) + 1)
        if ticks.size > 10:
            ticks = np.unique(np.linspace(ticks[0], ticks[-1], 8, dtype=int))
        self.count_color_bar.getAxis("right").setTicks(
            [[(float(tick), str(int(tick))) for tick in ticks]]
        )
        self.count_color_bar.setLabel("right", "Samples / pixel", enableAutoSIPrefix=False)
        self.count_plot.enableAutoRange()
        self.count_stack.setCurrentIndex(1)

    def show_distribution(
        self, processed: ProcessedMap, display_unit: DisplayUnit, config: HistogramConfig
    ) -> None:
        histogram = make_histogram_data(processed.values, config)
        if histogram is None:
            self.clear_distribution()
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
            "Source: processed map    "
            f"Finite {histogram.finite_count} / {histogram.total_count}    "
            f"Shown {histogram.shown_count}    Below {histogram.below_count}    Above {histogram.above_count}    "
            f"Mean {histogram.mean * display_unit.scale:.6g} {display_unit.unit}    "
            f"Median {histogram.median * display_unit.scale:.6g} {display_unit.unit}"
        )
        self.distribution_plot.setLabel("bottom", display_unit.axis_label, color=SECONDARY_TEXT)
        self.distribution_stack.setCurrentIndex(1)
        self.distribution_plot.enableAutoRange()

    def show_empty_map(self, title: str, message: str) -> None:
        panel = self.map_stack.widget(0)
        if panel is None:
            return
        title_label = panel.findChild(QtWidgets.QLabel, "emptyTitle")
        message_label = panel.findChild(QtWidgets.QLabel, "emptyMessage")
        if title_label is not None:
            title_label.setText(title)
        if message_label is not None:
            message_label.setText(message)
        self.map_stack.setCurrentIndex(0)

    def clear_distribution(self) -> None:
        self.distribution_bars.setOpts(
            x0=np.array([], dtype=float),
            x1=np.array([], dtype=float),
            height=np.array([], dtype=float),
        )
        self.distribution_stats.clear()
        self.mean_line.hide()
        self.median_line.hide()
        self.distribution_stack.setCurrentIndex(0)

    def show_distribution_error(self, message: str) -> None:
        """Keep invalid QC controls local to the Distribution view."""

        self.distribution_bars.setOpts(
            x0=np.array([], dtype=float),
            x1=np.array([], dtype=float),
            height=np.array([], dtype=float),
        )
        self.mean_line.hide()
        self.median_line.hide()
        self.distribution_stats.setText(f"Histogram controls: {message}")
        self.distribution_stack.setCurrentIndex(1)

    def clear_processed_views(self, message: str = "Reconstruction unavailable") -> None:
        """Clear all derived views after reconstruction invalidation."""
        self.clear_processed_map_and_distribution(message)
        self.count_image.clear()
        self.count_stack.setCurrentIndex(0)

    def clear_processed_map_and_distribution(self, message: str = "Processing unavailable") -> None:
        """Clear only processing outputs while retaining reconstruction QC state."""
        self.map_image.clear()
        self.clear_distribution()
        self.show_empty_map(message, message)

    def reset_views(self) -> None:
        self.map_plot.enableAutoRange()
        self.count_plot.enableAutoRange()
        self.distribution_plot.enableAutoRange()
