"""Raw trace, timing anchors, and guide rendering for Map Reconstruction."""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg  # type: ignore[import-not-found, import-untyped]
from PySide6 import QtCore, QtWidgets  # type: ignore[import-not-found]

from map_reconstruction.display_units import DisplayUnit, to_display_values
from map_reconstruction.ui.style import GRID_MAJOR, PANEL, PRIMARY_TEXT, SECONDARY_TEXT, TRACE

MAX_GUIDES_PER_FAMILY = 500
MAX_PHASE_WINDOW_GRAPHICS = 200


class TraceView(QtWidgets.QStackedWidget):
    """Display the raw signed trace and expose semantic anchor signals."""

    anchorMoved = QtCore.Signal(str, float)
    anchorMoveFinished = QtCore.Signal(str, float)

    def __init__(self, open_callback=None, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._open_callback = open_callback
        self._syncing = False
        self.anchor_lines: dict[str, pg.InfiniteLine] = {}
        self.guide_items: list[pg.InfiniteLine] = []
        self.phase_window_items: list[pg.LinearRegionItem] = []
        self._build_ui()

    def _build_ui(self) -> None:
        self.addWidget(self._empty_panel())
        self.plot = pg.PlotWidget()
        self._configure_plot(self.plot, "Raw time trace")
        self.plot.setLabel("bottom", "Elapsed time", units="s", color=SECONDARY_TEXT)
        self.plot.setLabel("left", "Signal", color=SECONDARY_TEXT)
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.guide_key = QtWidgets.QLabel(
            "<span style='color:#e53935'>●</span> YA &nbsp; "
            "<span style='color:#00bcd4'>●</span> YB &nbsp; "
            "<span style='color:#2979ff'>●</span> XA &nbsp; "
            "<span style='color:#d500f9'>●</span> XB &nbsp; "
            "<span style='color:#888888'>⋮</span> Row refs &nbsp; "
            "<span style='color:#d4a017'>¦</span> Pixel starts"
        )
        self.guide_key.setObjectName("guideKey")
        self.guide_key.setTextFormat(QtCore.Qt.TextFormat.RichText)
        layout.addWidget(self.guide_key)
        layout.addWidget(self.plot, 1)
        self.curve = self.plot.plot([], [], pen=pg.mkPen(TRACE, width=1.15))
        self.used_samples = pg.ScatterPlotItem(
            pen=None, brush=pg.mkBrush("#F59E0B"), size=7, symbol="o"
        )
        self.plot.addItem(self.used_samples)
        # Stable aliases for callers that used the pre-component view names.
        self.raw_plot = self.plot
        self.raw_curve = self.curve
        self.raw_guide_key = self.guide_key
        self.addWidget(panel)

    def _empty_panel(self) -> QtWidgets.QFrame:
        panel = QtWidgets.QFrame()
        panel.setObjectName("emptyState")
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        title = QtWidgets.QLabel("Raw trace")
        title.setObjectName("emptyTitle")
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        message = QtWidgets.QLabel("Open a HappyMeasure time-series CSV to begin.")
        message.setObjectName("emptyMessage")
        message.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        message.setWordWrap(True)
        layout.addWidget(title)
        layout.addSpacing(4)
        layout.addWidget(message)
        if self._open_callback is not None:
            button = QtWidgets.QPushButton("Open CSV")
            button.setObjectName("primaryAction")
            button.clicked.connect(self._open_callback)
            layout.addSpacing(12)
            layout.addWidget(button, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
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

    def show_loaded(self, loaded: bool) -> None:
        self.setCurrentIndex(1 if loaded else 0)
        self.guide_key.setVisible(loaded)

    def set_signal(self, time_s: np.ndarray, values: np.ndarray, display_unit: DisplayUnit) -> None:
        self.curve.setData(time_s, to_display_values(values, display_unit))
        self.plot.setLabel("left", display_unit.axis_label, color=SECONDARY_TEXT)

    def set_anchor_bounds(self, lower: float, upper: float) -> None:
        for line in self.anchor_lines.values():
            line.setBounds((lower, upper))

    def set_anchors(self, values: dict[str, float]) -> None:
        self.clear_anchors()
        specs = (
            ("row_a_s", "#e53935", "YA"),
            ("row_b_s", "#00bcd4", "YB"),
            ("point_a_s", "#2979ff", "XA"),
            ("point_b_s", "#d500f9", "XB"),
        )
        for name, color, label in specs:
            line = pg.InfiniteLine(
                pos=values[name],
                angle=90,
                movable=True,
                pen=pg.mkPen(color, width=2),
                label=label,
                labelOpts={"color": color, "position": 0.1},
            )
            line.sigPositionChanged.connect(self._anchor_line_moved)
            line.sigPositionChangeFinished.connect(self._anchor_line_finished)
            self.plot.addItem(line)
            self.anchor_lines[name] = line

    def clear_anchors(self) -> None:
        for line in self.anchor_lines.values():
            self.plot.removeItem(line)
        self.anchor_lines = {}

    def set_anchor_value(self, name: str, value: float) -> None:
        line = self.anchor_lines.get(name)
        if line is None:
            return
        self._syncing = True
        line.setValue(value)
        self._syncing = False

    def _anchor_line_moved(self, line: pg.InfiniteLine) -> None:
        if self._syncing:
            return
        for name, current in self.anchor_lines.items():
            if current is line:
                self.anchorMoved.emit(name, float(line.value()))
                return

    def _anchor_line_finished(self, line: pg.InfiniteLine) -> None:
        for name, current in self.anchor_lines.items():
            if current is line:
                self.anchorMoveFinished.emit(name, float(line.value()))
                return

    @staticmethod
    def guide_indices(count: int) -> np.ndarray:
        if count <= MAX_GUIDES_PER_FAMILY:
            return np.arange(count)
        return np.unique(np.linspace(0, count - 1, MAX_GUIDES_PER_FAMILY, dtype=int))

    def set_guides(self, row_positions: np.ndarray, pixel_positions: np.ndarray) -> None:
        self.clear_guides()
        for position in row_positions[self.guide_indices(row_positions.size)]:
            self._add_guide(float(position), "#888888", QtCore.Qt.PenStyle.DotLine)
        for position in pixel_positions[self.guide_indices(pixel_positions.size)]:
            self._add_guide(float(position), "#d4a017", QtCore.Qt.PenStyle.DashLine)

    def _add_guide(self, position: float, color: str, style: QtCore.Qt.PenStyle) -> None:
        guide = pg.InfiniteLine(
            pos=position,
            angle=90,
            movable=False,
            pen=pg.mkPen(color, width=1, style=style),
        )
        self.plot.addItem(guide)
        self.guide_items.append(guide)

    def clear_guides(self) -> None:
        for guide in self.guide_items:
            self.plot.removeItem(guide)
        self.guide_items = []
        for band in self.phase_window_items:
            self.plot.removeItem(band)
        self.phase_window_items = []
        self.used_samples.setData([], [])

    def set_phase_window_guides(
        self,
        row_positions: np.ndarray,
        bounds: np.ndarray,
        time_s: np.ndarray,
        values: np.ndarray,
        display_unit: DisplayUnit,
        inclusive_right: bool = False,
    ) -> None:
        """Render decimated core bounds and exactly their selected samples."""

        self.clear_guides()
        for position in row_positions[self.guide_indices(row_positions.size)]:
            self._add_guide(float(position), "#888888", QtCore.Qt.PenStyle.DotLine)
        flat_bounds = np.asarray(bounds, dtype=float).reshape(-1, 2)
        indices = self.guide_indices(min(flat_bounds.shape[0], MAX_PHASE_WINDOW_GRAPHICS))
        if flat_bounds.shape[0] > MAX_PHASE_WINDOW_GRAPHICS:
            indices = np.unique(
                np.linspace(0, flat_bounds.shape[0] - 1, MAX_PHASE_WINDOW_GRAPHICS, dtype=int)
            )
        selected_times: list[np.ndarray] = []
        selected_values: list[np.ndarray] = []
        for index in indices:
            left, right = flat_bounds[index]
            band = pg.LinearRegionItem(
                values=(float(left), float(right)),
                movable=False,
                brush=pg.mkBrush(245, 158, 11, 38),
                pen=pg.mkPen("#D97706", width=0.8),
            )
            band.setZValue(-5)
            self.plot.addItem(band)
            self.phase_window_items.append(band)
            first = int(np.searchsorted(time_s, left, side="left"))
            last = int(np.searchsorted(time_s, right, side="right" if inclusive_right else "left"))
            selected_times.append(time_s[first:last])
            selected_values.append(values[first:last])
        if selected_times:
            self.used_samples.setData(
                np.concatenate(selected_times),
                to_display_values(np.concatenate(selected_values), display_unit),
            )

    def clear(self) -> None:
        self.curve.clear()
        self.clear_anchors()
        self.clear_guides()
        self.show_loaded(False)

    def reset_view(self) -> None:
        self.plot.enableAutoRange()
