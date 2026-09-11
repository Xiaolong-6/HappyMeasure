from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from PySide6 import QtWidgets

from map_reconstruction.models import TimeSeriesData
from map_reconstruction.ui.main_window import MapReconstructionWindow


@pytest.fixture(scope="module")
def application():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _window_with_valid_reconstruction(application) -> MapReconstructionWindow:
    window = MapReconstructionWindow()
    time = np.linspace(0.0, 10.0, 10_001)
    current = 1e-6 * np.sin(time)
    voltage = np.cos(time)
    window.data = TimeSeriesData(time_s=time, signals={"Current_A": current, "Voltage_V": voltage})
    window.signal_combo.blockSignals(True)
    window.signal_combo.addItems(window.data.signal_names)
    window.signal_combo.setCurrentText("Current_A")
    window.signal_combo.blockSignals(False)
    window._set_anchor_bounds(window.data)
    window.rows_spin.setValue(2)
    window.cols_spin.setValue(2)
    window.rows_apart_spin.setValue(1)
    window.row_offset_spin.setValue(0)
    window.points_apart_spin.setValue(1)
    window.point_offset_spin.setValue(0)
    window.row_a_spin.setValue(0.0)
    window.row_b_spin.setValue(4.0)
    window.point_a_spin.setValue(0.5)
    window.point_b_spin.setValue(1.5)
    window._sync_point_period_from_anchors()
    window._set_raw_signal("Current_A")
    window._create_anchor_lines()
    window._set_loaded_view(True)
    window._reconstruct()
    assert window.result is not None
    return window


def _write_minimal_csv(path: Path, scale: float = 1.0) -> None:
    path.write_bytes(
        b"# schema,single-v2\n"
        b"# section,data\n"
        b"Elapsed_s,Current_A\n"
        + f"0,{scale * 1e-6:.12g}\n0.1,{scale * 2e-6:.12g}\n".encode()
    )


def test_new_csv_replaces_old_workspace_and_returns_to_preparation(
    application, tmp_path: Path, monkeypatch
) -> None:
    window = _window_with_valid_reconstruction(application)
    candidate = tmp_path / "candidate.csv"
    _write_minimal_csv(candidate, scale=4.0)
    old_data = window.data
    monkeypatch.setattr(window, "_replacement_choice", lambda: "discard")
    try:
        window._select_stage(2)
        window.load_file(candidate)
        assert window.data is not old_data
        assert window._loaded_filename == "candidate.csv"
        assert window.result is None
        assert window.params is None
        assert window.processed is None
        assert window._active_color_limits is None
        assert window.workflow_stack.currentIndex() == 0
        assert window.workflow_header.stage_buttons[0].isChecked()
        assert all(value.text() == "—" for value in window.qc_values.values())
    finally:
        window.close()


def test_invalid_csv_preserves_existing_workspace(application, tmp_path: Path, monkeypatch) -> None:
    window = _window_with_valid_reconstruction(application)
    old_data = window.data
    old_values = window.result.values.copy() if window.result is not None else None
    invalid = tmp_path / "invalid.csv"
    invalid.write_text("not a HappyMeasure CSV\n", encoding="utf-8")
    monkeypatch.setattr(QtWidgets.QMessageBox, "critical", staticmethod(lambda *_args: None))
    try:
        window.load_file(invalid)
        assert window.data is old_data
        assert window.result is not None
        assert old_values is not None
        np.testing.assert_allclose(window.result.values, old_values, equal_nan=True)
    finally:
        window.close()


def test_csv_replacement_cancel_preserves_existing_workspace(
    application, tmp_path: Path, monkeypatch
) -> None:
    window = _window_with_valid_reconstruction(application)
    candidate = tmp_path / "candidate.csv"
    _write_minimal_csv(candidate, scale=5.0)
    old_data = window.data
    monkeypatch.setattr(window, "_replacement_choice", lambda: "cancel")
    try:
        window.load_file(candidate)
        assert window.data is old_data
        assert window.result is not None
    finally:
        window.close()
