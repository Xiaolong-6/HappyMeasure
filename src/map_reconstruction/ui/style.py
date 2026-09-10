"""Small, dependency-free visual system for the optional Qt map workspace."""

from __future__ import annotations

from PySide6 import QtGui, QtWidgets

APP_BACKGROUND = "#F5F7FA"
PANEL = "#FFFFFF"
PRIMARY_TEXT = "#1F2937"
SECONDARY_TEXT = "#667085"
BORDER = "#D8DEE8"
GRID_MAJOR = "#D9DEE7"
GRID_MINOR = "#EEF1F5"
ACCENT = "#2563EB"
TRACE = "#3F4854"
WARNING = "#9A6700"
WARNING_BACKGROUND = "#FFF6D8"


APP_STYLESHEET = f"""
QMainWindow {{
    background: {APP_BACKGROUND};
    color: {PRIMARY_TEXT};
}}
QLabel#sectionHeader, QLabel#fieldLabel, QLabel#fileLabel {{
    color: {SECONDARY_TEXT};
}}
QLabel#appTitle, QLabel#pageTitle {{
    color: {PRIMARY_TEXT};
    font-weight: 600;
}}
QLabel#appTitle {{ font-size: 15px; }}
QLabel#pageTitle {{ font-size: 13px; }}
QLabel#mutedText, QLabel#workflowFile, QLabel#workflowStatus {{
    color: {SECONDARY_TEXT};
}}
QFrame#stageSidebar {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 7px;
    min-width: 300px;
    max-width: 340px;
}}
QLabel#analysisControls, QLabel#preparationDiagnostics {{ color: {SECONDARY_TEXT}; }}
QLabel#sectionHeader {{
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.8px;
}}
QFrame#inspectorSection {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 9px;
}}
QFrame#emptyState {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 9px;
}}
QLabel#emptyTitle {{
    color: {PRIMARY_TEXT};
    font-size: 15px;
    font-weight: 600;
}}
QLabel#emptyMessage {{
    color: {SECONDARY_TEXT};
}}
QLabel#methodValue {{
    color: {ACCENT};
    font-weight: 600;
}}
QLabel#subsectionHeader {{
    color: {SECONDARY_TEXT};
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.7px;
}}
QLabel#qcValue {{
    color: {PRIMARY_TEXT};
    font-weight: 600;
}}
QLabel#warningLabel {{
    color: {WARNING};
    background: {WARNING_BACKGROUND};
    border: 1px solid #F1D58A;
    border-radius: 4px;
    padding: 5px 7px;
}}
QLabel#distributionStats {{
    color: {SECONDARY_TEXT};
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px 7px;
}}
QLabel#guideKey {{
    color: {SECONDARY_TEXT};
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 3px 6px;
    font-size: 9px;
}}
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 9px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #C7CFDB;
    border-radius: 4px;
    min-height: 24px;
}}
QComboBox, QSpinBox, QDoubleSpinBox {{
    background: {PANEL};
    color: {PRIMARY_TEXT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    min-height: 26px;
    padding: 1px 7px;
}}
QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: #AEB9C8;
}}
QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {ACCENT};
}}
QCheckBox {{
    color: {PRIMARY_TEXT};
    spacing: 7px;
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: #DCE3EC;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 13px;
    margin: -5px 0;
    background: {ACCENT};
    border-radius: 6px;
}}
QPushButton {{
    color: {PRIMARY_TEXT};
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 4px;
    min-height: 28px;
    padding: 2px 10px;
}}
QPushButton:hover {{
    background: #F8FAFC;
    border-color: #AEB9C8;
}}
QPushButton#primaryAction {{
    color: white;
    background: {ACCENT};
    border-color: {ACCENT};
    font-weight: 600;
}}
QPushButton#primaryAction:hover {{
    background: #1D4ED8;
}}
QPushButton:disabled {{
    color: #98A2B3;
    background: #F1F3F6;
    border-color: #E3E7ED;
}}
QStatusBar {{
    color: {SECONDARY_TEXT};
    background: transparent;
}}
QSplitter::handle {{
    background: transparent;
}}
QSplitter::handle:hover {{
    background: #DCE6F8;
}}
QTabWidget::pane {{
    border: 1px solid {BORDER};
    background: {PANEL};
}}
QTabBar::tab {{
    color: {SECONDARY_TEXT};
    background: #EEF2F7;
    border: 1px solid {BORDER};
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    min-height: 25px;
    padding: 2px 10px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    color: {PRIMARY_TEXT};
    background: {PANEL};
    font-weight: 600;
}}
"""


def apply_light_theme(application: QtWidgets.QApplication) -> None:
    """Apply the restrained shared QSS once per process."""

    if application.property("map_reconstruction_light_theme"):
        return
    application.setStyle("Fusion")
    font = QtGui.QFont(application.font())
    if "Segoe UI" in QtGui.QFontDatabase.families():
        font.setFamily("Segoe UI")
    font.setPointSize(10)
    application.setFont(font)
    application.setStyleSheet(APP_STYLESHEET)
    application.setProperty("map_reconstruction_light_theme", True)
