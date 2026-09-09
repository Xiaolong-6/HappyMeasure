"""Map, sample-count, and distribution views for the Map Reconstruction UI."""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg  # type: ignore[import-not-found, import-untyped]
from PySide6 import QtCore, QtWidgets  # type: ignore[import-not-found]

from map_reconstruction.display_units import DisplayUnit, to_display_values
from map_reconstruction.processing import ProcessedMap
from map_reconstruction.qc.distribution import make_histogram_data
from map_reconstruction.ui.style import (
    BORDER,
    GRID_MAJOR,
    PANEL,
    PRIMARY_TEXT,
    SECONDARY_TEXT,
)


class MapViews(QtWidgets.QWidget):
    """Own the right-side scientific map and QC plots."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        map_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        root.addWidget(map_splitter)
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
        map_splitter.setStretchFactor(0, 1)
        map_splitter.setStretchFactor(1, 1)
        root.addWidget(map_splitter)
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

    def show_sample_counts(self, values: np.ndarray, flip_y: bool) -> None:
        display = np.asarray(values, dtype=float)
        if flip_y:
            display = np.flipud(display)
        self.count_image.setImage(display, autoLevels=True)
        self.count_plot.enableAutoRange()
        self.count_stack.setCurrentIndex(1)

    def show_distribution(self, processed: ProcessedMap, display_unit: DisplayUnit) -> None:
        histogram = make_histogram_data(processed.values)
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
            f"Finite pixels {histogram.finite_count} / {histogram.total_count}    "
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

    def clear_processed_views(self, message: str = "Reconstruction unavailable") -> None:
        self.map_image.clear()
        self.count_image.clear()
        self.clear_distribution()
        self.show_empty_map(message, message)
        self.count_stack.setCurrentIndex(0)

    def reset_views(self) -> None:
        self.map_plot.enableAutoRange()
        self.count_plot.enableAutoRange()
        self.distribution_plot.enableAutoRange()
