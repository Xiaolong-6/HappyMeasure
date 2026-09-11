from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from PySide6 import QtWidgets

from map_reconstruction.ui.main_window import MapReconstructionWindow


@pytest.fixture(scope="module")
def application():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_map_analysis_flip_color_control_is_visible_when_analysis_stage_is_shown(application) -> None:
    window = MapReconstructionWindow()
    try:
        window.show()
        window._select_stage(2)
        application.processEvents()
        assert window.analysis_page.invert_palette_check.text() == "Flip color"
        assert window.analysis_page.invert_palette_check.isVisible()
    finally:
        window.close()


def test_map_window_has_sensible_normal_geometry_before_maximized_start(application) -> None:
    window = MapReconstructionWindow()
    try:
        assert window.width() >= 1000
        assert window.height() >= 700
    finally:
        window.close()
