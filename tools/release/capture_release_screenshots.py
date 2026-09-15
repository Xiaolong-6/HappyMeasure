"""Generate the six README screenshots from the current source GUI.

This script is release-documentation automation only. It uses HappyMeasure's
debug simulator and a deterministic synthetic Map Reconstruction trace; it
never opens real hardware. When a release freeze is active, the marker must
match the runtime identity before capture proceeds.
"""

from __future__ import annotations

import csv
import json
import math
import sys
import tempfile
import time
from pathlib import Path
from tkinter import messagebox

import numpy as np
from PIL import Image, ImageGrab

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
SCREENSHOTS = ROOT / "docs" / "screenshots"
FREEZE_MARKER = ROOT / "tools" / "release" / "RELEASE_FREEZE_MARKER"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import keith_ivt.ui.sweep_controller as sweep_controller  # noqa: E402
import keith_ivt.ui.update_controller as update_controller  # noqa: E402
from keith_ivt.models import SweepKind  # noqa: E402
from keith_ivt.ui.simple_app import SimpleKeithIVtApp  # noqa: E402
from keith_ivt.version import __version__  # noqa: E402
from map_reconstruction.ui.main_window import MapReconstructionWindow  # noqa: E402


def _expected_version() -> str:
    if not FREEZE_MARKER.exists():
        return __version__
    value = FREEZE_MARKER.read_text(encoding="utf-8").strip()
    if not value:
        raise RuntimeError("Release freeze marker is empty")
    return value


def _wait_until(app: SimpleKeithIVtApp, predicate, timeout_s: float = 12.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        app.root.update()
        if predicate():
            return
        time.sleep(0.02)
    raise RuntimeError(f"Timed out while waiting for UI state; run state={app._run_state!r}")


def _capture_tk(window, path: Path) -> None:  # type: ignore[no-untyped-def]
    window.update_idletasks()
    window.update()
    time.sleep(0.25)
    x = int(window.winfo_rootx())
    y = int(window.winfo_rooty())
    width = int(window.winfo_width())
    height = int(window.winfo_height())
    if width < 400 or height < 300:
        raise RuntimeError(f"Refusing suspicious Tk capture size {width}x{height} for {path.name}")
    image = ImageGrab.grab(bbox=(x, y, x + width, y + height), all_screens=True)
    image.save(path)


def _verify_png(path: Path, *, min_width: int = 800, min_height: int = 450) -> None:
    with Image.open(path) as image:
        width, height = image.size
        extrema = image.convert("L").getextrema()
    if width < min_width or height < min_height:
        raise RuntimeError(f"{path.name} is only {width}x{height}")
    if extrema is None or extrema[0] == extrema[1]:
        raise RuntimeError(f"{path.name} appears blank")


def _capture_happymeasure(scratch: Path) -> None:
    messagebox.showinfo = lambda *_args, **_kwargs: None
    messagebox.showwarning = lambda *_args, **_kwargs: None
    messagebox.showerror = lambda *_args, **_kwargs: None
    messagebox.askyesno = lambda *_args, **_kwargs: True
    messagebox.askyesnocancel = lambda *_args, **_kwargs: False
    update_controller.check_github_release = lambda *_args, **_kwargs: {
        "status": "current",
        "message": "Release screenshot capture",
        "latest_version": _expected_version(),
        "release_url": None,
        "asset_name": None,
        "asset_download_url": None,
        "asset_sha256": None,
    }
    sweep_controller.autosave_result = lambda _result: scratch / "simulator-backup.csv"

    app = SimpleKeithIVtApp()
    try:
        # GitHub's Windows desktop is about 1024x768. Keep the entire client
        # area above the taskbar so release captures contain application UI only.
        app.root.geometry("1000x650+10+10")
        app.root.update()
        app.show_front_panel_on_start.set(False)

        app.debug.set(False)
        app.port.set("COM3")
        app.baud_rate.set(57600)
        app._show_nav("Hardware")
        app.root.update()
        _capture_tk(app.root, SCREENSHOTS / "happymeasure-hardware.png")

        app.debug.set(True)
        app.debug_model.set("Linear resistor 10 kΩ")
        app._show_nav("Hardware")
        app.connect_or_check()
        if not app._connected:
            raise RuntimeError("Debug simulator failed to connect")

        app._show_nav("Sweep")
        app.sweep_kind.set(SweepKind.STEP.value)
        app.start.set(-0.5)
        app.stop.set(0.5)
        app.step.set(0.05)
        app.nplc.set(0.01)
        app.delay_s.set(0.0)
        app.root.update()
        app.start_sweep()
        _wait_until(app, lambda: app._run_state in {"completed", "stopped", "error"})
        if app._run_state != "completed" or app._last_result is None:
            raise RuntimeError(f"Simulator sweep did not complete: {app._run_state}")
        app.root.update()
        _capture_tk(app.root, SCREENSHOTS / "happymeasure-sweep-result.png")

        app._last_source_value = 0.150
        app._last_measured_value = 15e-6
        app._refresh_live_measurement_status()
        app._open_front_panel_popup(auto_open=False)
        popup = app._front_panel_window
        if popup is None:
            raise RuntimeError("Front-panel popup was not created")
        app.root.update_idletasks()
        root_x = app.root.winfo_rootx()
        root_y = app.root.winfo_rooty()
        # Keep the full popup inside the main-window capture rectangle.
        popup.geometry(f"860x500+{root_x + 110}+{root_y + 60}")
        app.root.update()
        popup.lift()
        popup.update()
        _capture_tk(app.root, SCREENSHOTS / "happymeasure-front-panel-popup.png")
    finally:
        try:
            if getattr(app, "_connected", False):
                app.disconnect_hardware()
        finally:
            app.root.destroy()


def _synthetic_map_csv(path: Path) -> tuple[int, int]:
    rows, cols = 6, 8
    row_period = 1.0
    point_period = 0.1
    dt = 0.005
    time_s = np.arange(0.0, rows * row_period, dt)
    values = np.full(time_s.shape, -0.02e-6, dtype=float)

    for row in range(rows):
        for col in range(cols):
            gaussian = math.exp(-((row - 2.4) ** 2) / 3.0 - ((col - 3.7) ** 2) / 7.0)
            ripple = 0.13 * math.sin((row + 1) * 0.8) * math.cos((col + 1) * 0.65)
            pixel = -(0.18 + 1.65 * gaussian + ripple) * 1e-6
            start = row * row_period + 0.1 + col * point_period
            active = (time_s >= start + 0.015) & (time_s <= start + 0.080)
            values[active] = pixel

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["# HappyMeasure measurement export"])
        writer.writerow(["# schema", "single-v2"])
        writer.writerow(
            [
                "# metadata",
                json.dumps(
                    {
                        "device_name": "Synthetic release demo",
                        "operator": "",
                        "mode": "VOLT",
                    }
                ),
            ]
        )
        writer.writerow(["# section", "data"])
        writer.writerow(["Elapsed_s", "Voltage_V", "Current_A"])
        for timestamp, current in zip(time_s, values):
            writer.writerow([f"{timestamp:.6f}", "0", f"{current:.12g}"])
    return rows, cols


def _set_map_geometry(window: MapReconstructionWindow, rows: int, cols: int) -> None:
    widgets = (
        window.rows_spin,
        window.cols_spin,
        window.rows_apart_spin,
        window.row_a_spin,
        window.row_b_spin,
        window.row_offset_spin,
        window.points_apart_spin,
        window.point_a_spin,
        window.point_b_spin,
        window.point_offset_spin,
    )
    for widget in widgets:
        widget.blockSignals(True)
    try:
        window.rows_spin.setValue(rows)
        window.cols_spin.setValue(cols)
        window.rows_apart_spin.setValue(4)
        window.row_a_spin.setValue(0.0)
        window.row_b_spin.setValue(4.0)
        window.row_offset_spin.setValue(0)
        window.points_apart_spin.setValue(6)
        window.point_a_spin.setValue(0.1)
        window.point_b_spin.setValue(0.7)
        window.point_offset_spin.setValue(0)
    finally:
        for widget in widgets:
            widget.blockSignals(False)
    window.inspector.mark_anchors_user_edited()
    window._sync_point_period_from_anchors()
    window._create_anchor_lines()
    window._reconstruct()
    if window.result is None or window.processed is None:
        raise RuntimeError("Synthetic map reconstruction did not produce a processed map")


def _capture_qt(window: MapReconstructionWindow, path: Path) -> None:
    from PySide6 import QtWidgets

    app = QtWidgets.QApplication.instance()
    if app is None:
        raise RuntimeError("QApplication is unavailable")
    for _ in range(3):
        app.processEvents()
        time.sleep(0.05)
    pixmap = window.grab()
    if pixmap.isNull() or not pixmap.save(str(path), "PNG"):
        raise RuntimeError(f"Could not save Qt screenshot {path}")


def _capture_map_reconstruction(scratch: Path) -> None:
    from PySide6 import QtWidgets

    qt_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    source = scratch / "synthetic-release-map.csv"
    rows, cols = _synthetic_map_csv(source)
    window = MapReconstructionWindow()
    try:
        window.resize(1440, 900)
        window.show()
        qt_app.processEvents()
        window.load_file(source)
        _set_map_geometry(window, rows, cols)

        window._select_stage(0)
        _capture_qt(window, SCREENSHOTS / "map-reconstruction-preparation.png")
        window._select_stage(1)
        _capture_qt(window, SCREENSHOTS / "map-reconstruction-reconstruction.png")
        window._select_stage(2)
        _capture_qt(window, SCREENSHOTS / "map-reconstruction-analysis.png")
    finally:
        window.close()
        qt_app.processEvents()


def main() -> int:
    expected_version = _expected_version()
    if __version__ != expected_version:
        raise RuntimeError(
            f"Screenshot capture expects {expected_version} from the active release identity, "
            f"source reports {__version__}."
        )
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="happymeasure-release-screenshots-") as temp_dir:
        scratch = Path(temp_dir)
        _capture_happymeasure(scratch)
        _capture_map_reconstruction(scratch)

    for filename in (
        "happymeasure-hardware.png",
        "happymeasure-sweep-result.png",
        "happymeasure-front-panel-popup.png",
        "map-reconstruction-preparation.png",
        "map-reconstruction-reconstruction.png",
        "map-reconstruction-analysis.png",
    ):
        path = SCREENSHOTS / filename
        _verify_png(path)
        print(f"captured {path.relative_to(ROOT)} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
