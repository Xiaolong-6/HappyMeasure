from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

try:
    import pyqtgraph as pg  # type: ignore[import-not-found]
    from PySide6 import QtCore, QtWidgets  # type: ignore[import-not-found]
except ImportError as exc:  # pragma: no cover - optional GUI dependency
    raise ImportError("PySide6 and pyqtgraph are required for the Map Reconstruction UI") from exc

from map_reconstruction.importers.happymeasure import import_happymeasure_csv
from map_reconstruction.methods.dual_offset import reconstruct_map
from map_reconstruction.models import (
    DualOffsetParams,
    ReconstructionResult,
    ScanPattern,
    TimeSeriesData,
)


class MapReconstructionWindow(QtWidgets.QMainWindow):
    """Resizable timing, trace, and map workspace for v1 reconstruction."""

    def __init__(self, initial_path: Path | None = None) -> None:
        super().__init__()
        pg.setConfigOption("imageAxisOrder", "row-major")
        self.data: TimeSeriesData | None = None
        self.result: ReconstructionResult | None = None
        self.params: DualOffsetParams | None = None
        self.anchor_lines: dict[str, pg.InfiniteLine] = {}
        self.guide_items: list[pg.InfiniteLine] = []
        self._syncing = False
        self.setWindowTitle("Map Reconstruction")
        self.resize(1280, 820)
        self._build_ui()
        if initial_path is not None:
            self.load_file(initial_path)

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        root_layout = QtWidgets.QVBoxLayout(central)
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        root_layout.addWidget(splitter)
        self.setCentralWidget(central)

        controls = QtWidgets.QWidget()
        controls_layout = QtWidgets.QVBoxLayout(controls)
        self.open_button = QtWidgets.QPushButton("Open HappyMeasure CSV")
        self.open_button.clicked.connect(self._choose_file)
        controls_layout.addWidget(self.open_button)
        self.file_label = QtWidgets.QLabel("No file loaded")
        self.file_label.setWordWrap(True)
        controls_layout.addWidget(self.file_label)

        form = QtWidgets.QFormLayout()
        self.signal_combo = QtWidgets.QComboBox()
        self.signal_combo.currentTextChanged.connect(self._reconstruct)
        form.addRow("Signal", self.signal_combo)
        self.rows_spin = self._int_spin(36, 1, 10000)
        self.cols_spin = self._int_spin(36, 1, 10000)
        form.addRow("Rows", self.rows_spin)
        form.addRow("Columns", self.cols_spin)
        self.scan_combo = QtWidgets.QComboBox()
        self.scan_combo.addItem("Same direction", ScanPattern.SAME_DIRECTION)
        self.scan_combo.addItem("Serpentine", ScanPattern.SERPENTINE)
        form.addRow("Scan pattern", self.scan_combo)
        self.first_row_check = QtWidgets.QCheckBox("First row L → R")
        self.first_row_check.setChecked(True)
        form.addRow("Orientation", self.first_row_check)
        self.flip_y_check = QtWidgets.QCheckBox("Flip Y display")
        form.addRow("Display", self.flip_y_check)
        self.median_check = QtWidgets.QCheckBox("Median / pixel")
        self.median_check.setChecked(True)
        form.addRow("Aggregation", self.median_check)
        controls_layout.addLayout(form)

        timing_group = QtWidgets.QGroupBox("Timing anchors")
        timing_form = QtWidgets.QFormLayout(timing_group)
        self.row_a_spin = self._float_spin()
        self.row_b_spin = self._float_spin()
        self.point_a_spin = self._float_spin()
        self.point_b_spin = self._float_spin()
        self.rows_apart_spin = self._int_spin(10, 1, 100000)
        self.row_offset_spin = self._int_spin(0, 0, 100000)
        self.points_apart_spin = self._int_spin(10, 1, 100000)
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
        for label, widget in (
            ("Row A (s)", self.row_a_spin),
            ("Row B (s)", self.row_b_spin),
            ("Rows apart", self.rows_apart_spin),
            ("Row offset", row_offset_control),
            ("Point A (s)", self.point_a_spin),
            ("Point B (s)", self.point_b_spin),
            ("Points apart", self.points_apart_spin),
            ("Point offset", point_offset_control),
        ):
            timing_form.addRow(label, widget)
        controls_layout.addWidget(timing_group)

        self.timing_label = QtWidgets.QLabel("Timing: —")
        self.timing_label.setWordWrap(True)
        self.qc_label = QtWidgets.QLabel("QC: —")
        self.qc_label.setWordWrap(True)
        controls_layout.addWidget(self.timing_label)
        controls_layout.addWidget(self.qc_label)
        button_row = QtWidgets.QHBoxLayout()
        self.reset_button = QtWidgets.QPushButton("Reset trace view")
        self.reset_button.clicked.connect(self._reset_views)
        self.export_button = QtWidgets.QPushButton("Export map CSV")
        self.export_button.clicked.connect(self._export_map)
        button_row.addWidget(self.reset_button)
        button_row.addWidget(self.export_button)
        controls_layout.addLayout(button_row)
        controls_layout.addStretch(1)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(controls)
        scroll.setMinimumWidth(280)
        splitter.addWidget(scroll)

        right_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        map_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.map_plot, self.map_image = self._make_image_plot("Reconstructed map")
        self.count_plot, self.count_image = self._make_image_plot("Samples / pixel")
        map_splitter.addWidget(self.map_plot)
        map_splitter.addWidget(self.count_plot)
        right_splitter.addWidget(map_splitter)

        self.raw_plot = pg.PlotWidget()
        self.raw_plot.setTitle("Raw time trace")
        self.raw_plot.setLabel("bottom", "Elapsed time", units="s")
        self.raw_plot.showGrid(x=True, y=True, alpha=0.25)
        self.raw_curve = self.raw_plot.plot([], [], pen=pg.mkPen("#555555", width=1))
        right_splitter.addWidget(self.raw_plot)
        right_splitter.setStretchFactor(0, 2)
        right_splitter.setStretchFactor(1, 1)
        splitter.addWidget(right_splitter)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

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
        for spin in (self.row_a_spin, self.row_b_spin, self.point_a_spin, self.point_b_spin):
            spin.editingFinished.connect(self._anchor_spin_finished)

    @staticmethod
    def _int_spin(value: int, minimum: int, maximum: int) -> QtWidgets.QSpinBox:
        spin = QtWidgets.QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        return spin

    @staticmethod
    def _float_spin() -> QtWidgets.QDoubleSpinBox:
        spin = QtWidgets.QDoubleSpinBox()
        spin.setDecimals(6)
        spin.setRange(-1e15, 1e15)
        spin.setSingleStep(0.1)
        return spin

    @staticmethod
    def _offset_slider() -> QtWidgets.QSlider:
        slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        slider.setRange(0, 0)
        return slider

    @staticmethod
    def _make_image_plot(title: str) -> tuple[pg.PlotWidget, pg.ImageItem]:
        plot = pg.PlotWidget()
        plot.setTitle(title)
        plot.setAspectLocked(True)
        plot.showGrid(x=True, y=True, alpha=0.2)
        image = pg.ImageItem()
        plot.addItem(image)
        return plot, image

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
        self.file_label.setText(str(path))
        self.signal_combo.blockSignals(True)
        self.signal_combo.clear()
        self.signal_combo.addItems(data.signal_names)
        preferred = "Current_A" if "Current_A" in data.signals else data.signal_names[-1]
        self.signal_combo.setCurrentText(preferred)
        self.signal_combo.blockSignals(False)
        self._set_anchor_bounds(data)
        self.raw_curve.setData(data.time_s, data.signals[preferred])
        self._create_anchor_lines()
        self._reconstruct()
        self.statusBar().showMessage(f"Loaded {data.sample_count} samples from {path.name}")

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

    def _update_offset_ranges(self) -> None:
        row_max = max(0, self.rows_spin.value() - 1)
        point_max = max(0, self.cols_spin.value() - 1)
        self.row_offset_spin.setRange(0, row_max)
        self.point_offset_spin.setRange(0, point_max)
        self.row_offset_slider.setRange(0, row_max)
        self.point_offset_slider.setRange(0, point_max)

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
            self.statusBar().showMessage(str(exc))
            self.timing_label.setText("Timing: —")
            return
        self.params = params
        self.result = result
        timing = result.timing
        self.timing_label.setText(
            "Timing: "
            f"row={timing.row_period_s:.6g}s, point={timing.point_period_s:.6g}s, "
            f"row ref0={timing.row_ref0_s:.6g}s, pixel 1 phase={timing.pixel1_phase_s:.6g}s"
        )
        finite = np.isfinite(result.values)
        valid_percent = 100.0 * float(np.mean(finite))
        median_samples = float(np.median(result.sample_counts[finite])) if np.any(finite) else 0.0
        first_pixel = timing.row_ref0_s + timing.pixel1_phase_s
        last_pixel = (
            timing.row_ref0_s
            + (params.rows - 1) * timing.row_period_s
            + timing.pixel1_phase_s
            + (params.cols - 1) * timing.point_period_s
        )
        warning_text = " | ".join(result.warnings) if result.warnings else "none"
        self.qc_label.setText(
            "QC: "
            f"valid={valid_percent:.1f}%, median samples={median_samples:.3g}, "
            f"first={first_pixel:.6g}s, last={last_pixel:.6g}s, warnings={warning_text}"
        )
        self._set_image(self.map_plot, self.map_image, result.values)
        self._set_image(self.count_plot, self.count_image, result.sample_counts)
        self._update_guides(result)
        self.statusBar().showMessage("Map reconstructed.")

    def _set_image(self, plot: pg.PlotWidget, image: pg.ImageItem, values: np.ndarray) -> None:
        display = np.asarray(values, dtype=float)
        if self.flip_y_check.isChecked():
            display = np.flipud(display)
        if not np.isfinite(display).any():
            display = np.zeros_like(display)
        image.setImage(display, autoLevels=True)
        plot.enableAutoRange()

    def _update_guides(self, result: ReconstructionResult) -> None:
        for guide in self.guide_items:
            self.raw_plot.removeItem(guide)
        self.guide_items = []
        if self.data is None or self.params is None:
            return
        t_min, t_max = float(self.data.time_s[0]), float(self.data.time_s[-1])
        timing = result.timing
        for row in range(self.params.rows):
            position = timing.row_ref0_s + row * timing.row_period_s
            if t_min <= position <= t_max:
                self._add_guide(position, "#888888", QtCore.Qt.PenStyle.DotLine)
        row_index = int(np.floor((self.params.point_a_s - timing.row_ref0_s) / timing.row_period_s))
        row_base = timing.row_ref0_s + row_index * timing.row_period_s
        for column in range(self.params.cols):
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

    def _export_map(self) -> None:
        if self.result is None or self.data is None:
            QtWidgets.QMessageBox.information(
                self, "No map", "Load a CSV and reconstruct a map first."
            )
            return
        default = f"{self.data.source_path.stem if self.data.source_path else 'map'}_map.csv"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export reconstructed map", default, "CSV files (*.csv);;All files (*.*)"
        )
        if not path:
            return
        try:
            np.savetxt(path, self.result.values, delimiter=",", fmt="%.12g")
        except OSError as exc:
            QtWidgets.QMessageBox.critical(self, "Export failed", str(exc))
            return
        self.statusBar().showMessage(f"Exported map to {path}")


def run_app(path: Path | None = None) -> int:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    window = MapReconstructionWindow(path)
    window.show()
    return app.exec()
