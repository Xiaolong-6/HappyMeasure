"""Fluent-inspired visual system for the standalone Qt map workspace.

The Map Reconstruction UI intentionally remains native PySide6/Qt.  This module
provides a restrained Windows 11-like surface, spacing, typography and control
language without introducing a second widget framework or touching scientific
state.
"""

from __future__ import annotations

from PySide6 import QtGui, QtWidgets

APP_BACKGROUND = "#F3F3F3"
PANEL = "#FFFFFF"
SURFACE_ALT = "#F9F9F9"
SURFACE_HOVER = "#F6F6F6"
PRIMARY_TEXT = "#1B1B1B"
SECONDARY_TEXT = "#616161"
TERTIARY_TEXT = "#7A7A7A"
BORDER = "#E2E2E2"
BORDER_STRONG = "#C8C8C8"
GRID_MAJOR = "#D8D8D8"
GRID_MINOR = "#EEEEEE"
DEFAULT_ACCENT = "#0F6CBD"
TRACE = "#3F4854"
WARNING = "#8A5A00"
WARNING_BACKGROUND = "#FFF8E1"


def _accent_shade(accent: str, factor: int) -> str:
    color = QtGui.QColor(accent)
    if not color.isValid():
        color = QtGui.QColor(DEFAULT_ACCENT)
    adjusted = color.darker(factor) if factor >= 100 else color.lighter(200 - factor)
    return adjusted.name()


def _system_accent(application: QtWidgets.QApplication) -> str:
    """Capture the platform highlight before switching Qt to Fusion styling."""

    color = application.palette().color(QtGui.QPalette.ColorRole.Highlight)
    if not color.isValid() or color.alpha() == 0:
        return DEFAULT_ACCENT
    # Very pale highlights make selected controls illegible. Keep the native
    # hue when practical and fall back to the Windows blue otherwise.
    if color.lightness() > 225 or color.saturation() < 35:
        return DEFAULT_ACCENT
    return color.name()


def build_stylesheet(accent: str = DEFAULT_ACCENT) -> str:
    """Return the shared light-theme stylesheet for the scientific workspace."""

    color = QtGui.QColor(accent)
    accent = color.name() if color.isValid() else DEFAULT_ACCENT
    accent_hover = _accent_shade(accent, 115)
    accent_pressed = _accent_shade(accent, 130)
    # Qt style sheets do not consistently honor alpha hex colors across all
    # widgets, so derive a light opaque selection surface instead.
    soft_selection = QtGui.QColor(accent).lighter(188).name()

    return f"""
QMainWindow {{
    background: {APP_BACKGROUND};
    color: {PRIMARY_TEXT};
}}
QWidget#mapAppSurface {{
    background: {APP_BACKGROUND};
    color: {PRIMARY_TEXT};
}}
QLabel {{
    color: {PRIMARY_TEXT};
}}
QLabel#sectionHeader, QLabel#fieldLabel, QLabel#fileLabel {{
    color: {SECONDARY_TEXT};
}}
QLabel#appTitle, QLabel#pageTitle {{
    color: {PRIMARY_TEXT};
    font-weight: 600;
}}
QLabel#appTitle {{
    font-size: 17px;
}}
QLabel#pageTitle {{
    font-size: 14px;
}}
QLabel#mutedText, QLabel#workflowFile, QLabel#workflowStatus {{
    color: {SECONDARY_TEXT};
}}
QLabel#workflowFile {{
    font-size: 9pt;
}}
QFrame#stageSidebar {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 8px;
    min-width: 300px;
    max-width: 340px;
}}
QLabel#analysisControls, QLabel#preparationDiagnostics {{
    color: {SECONDARY_TEXT};
}}
QLabel#sectionHeader {{
    font-size: 9pt;
    font-weight: 600;
}}
QFrame#inspectorSection {{
    background: {PANEL};
    border: none;
    border-bottom: 1px solid {BORDER};
    border-radius: 0;
}}
QFrame#emptyState {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}
QLabel#emptyTitle {{
    color: {PRIMARY_TEXT};
    font-size: 14px;
    font-weight: 600;
}}
QLabel#emptyMessage {{
    color: {SECONDARY_TEXT};
}}
QLabel#methodValue {{
    color: {accent};
    font-weight: 600;
}}
QLabel#subsectionHeader {{
    color: {SECONDARY_TEXT};
    font-size: 9pt;
    font-weight: 600;
}}
QLabel#qcValue {{
    color: {PRIMARY_TEXT};
    font-weight: 600;
}}
QLabel#warningLabel {{
    color: {WARNING};
    background: {WARNING_BACKGROUND};
    border: 1px solid #F0D58C;
    border-radius: 6px;
    padding: 7px 9px;
}}
QLabel#distributionStats {{
    color: {SECONDARY_TEXT};
    background: {SURFACE_ALT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 9px;
}}
QLabel#guideKey {{
    color: {SECONDARY_TEXT};
    background: {SURFACE_ALT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px 7px;
    font-size: 9pt;
}}
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 12px;
    margin: 3px 2px;
}}
QScrollBar::handle:vertical {{
    background: #C6C6C6;
    border-radius: 4px;
    min-height: 30px;
    margin: 1px 2px;
}}
QScrollBar::handle:vertical:hover {{
    background: #AFAFAF;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
    border: none;
    height: 0px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 12px;
    margin: 2px 3px;
}}
QScrollBar::handle:horizontal {{
    background: #C6C6C6;
    border-radius: 4px;
    min-width: 30px;
    margin: 2px 1px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #AFAFAF;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
    border: none;
    width: 0px;
}}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background: {PANEL};
    color: {PRIMARY_TEXT};
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
    min-height: 30px;
    padding: 1px 9px;
    selection-background-color: {accent};
    selection-color: white;
}}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
    background: {SURFACE_ALT};
    border-color: #A7A7A7;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {accent};
    border-bottom: 2px solid {accent};
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
    color: {TERTIARY_TEXT};
    background: #F1F1F1;
    border-color: {BORDER};
}}
QComboBox::drop-down {{
    border: none;
    width: 26px;
}}
QComboBox QAbstractItemView {{
    color: {PRIMARY_TEXT};
    background: {PANEL};
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
    padding: 4px;
    outline: 0;
    selection-background-color: {soft_selection};
    selection-color: {PRIMARY_TEXT};
}}
QCheckBox {{
    color: {PRIMARY_TEXT};
    spacing: 8px;
    min-height: 24px;
}}
QRadioButton {{
    color: {PRIMARY_TEXT};
    spacing: 8px;
    min-height: 24px;
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: #D6D6D6;
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {accent};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 14px;
    height: 14px;
    margin: -5px 0;
    background: {accent};
    border: 2px solid {PANEL};
    border-radius: 7px;
}}
QPushButton {{
    color: {PRIMARY_TEXT};
    background: {PANEL};
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
    min-height: 30px;
    padding: 2px 12px;
}}
QPushButton:hover {{
    background: {SURFACE_HOVER};
    border-color: #A7A7A7;
}}
QPushButton:pressed {{
    background: #ECECEC;
    border-color: #B7B7B7;
}}
QPushButton:focus {{
    border-color: {accent};
}}
QPushButton#primaryAction {{
    color: white;
    background: {accent};
    border-color: {accent};
    font-weight: 600;
}}
QPushButton#primaryAction:hover {{
    background: {accent_hover};
    border-color: {accent_hover};
}}
QPushButton#primaryAction:pressed {{
    background: {accent_pressed};
    border-color: {accent_pressed};
}}
QPushButton:disabled {{
    color: #989898;
    background: #F0F0F0;
    border-color: {BORDER};
}}
QFrame#workflowNavigation {{
    background: #E9E9E9;
    border: 1px solid {BORDER};
    border-radius: 8px;
}}
QFrame#workflowNavigation QPushButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    color: {SECONDARY_TEXT};
    font-weight: 500;
    min-height: 34px;
    padding: 1px 14px;
}}
QFrame#workflowNavigation QPushButton:checked {{
    background: {PANEL};
    border-color: #D4D4D4;
    color: {PRIMARY_TEXT};
    font-weight: 600;
}}
QFrame#workflowNavigation QPushButton:hover:!checked {{
    background: #DEDEDE;
    color: {PRIMARY_TEXT};
}}
QStatusBar {{
    color: {SECONDARY_TEXT};
    background: transparent;
    min-height: 24px;
}}
QStatusBar::item {{
    border: none;
}}
QSplitter::handle {{
    background: transparent;
}}
QSplitter::handle:horizontal {{
    width: 5px;
}}
QSplitter::handle:vertical {{
    height: 5px;
}}
QSplitter::handle:hover {{
    background: #D8EAF8;
    border-radius: 2px;
}}
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    background: {PANEL};
    top: -1px;
}}
QTabBar::tab {{
    color: {SECONDARY_TEXT};
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    min-height: 30px;
    padding: 4px 12px;
    margin-right: 2px;
}}
QTabBar::tab:hover {{
    color: {PRIMARY_TEXT};
    background: {SURFACE_HOVER};
}}
QTabBar::tab:selected {{
    color: {PRIMARY_TEXT};
    border-bottom: 2px solid {accent};
    font-weight: 600;
}}
QToolTip {{
    color: {PRIMARY_TEXT};
    background: {PANEL};
    border: 1px solid {BORDER_STRONG};
    border-radius: 4px;
    padding: 5px 7px;
}}
QMenu {{
    color: {PRIMARY_TEXT};
    background: {PANEL};
    border: 1px solid {BORDER_STRONG};
    padding: 5px;
}}
QMenu::item {{
    border-radius: 4px;
    padding: 6px 22px 6px 10px;
}}
QMenu::item:selected {{
    background: {soft_selection};
}}
QMessageBox {{
    background: {APP_BACKGROUND};
}}
"""


def apply_light_theme(application: QtWidgets.QApplication) -> None:
    """Apply the Fluent-inspired light theme once per process."""

    if application.property("map_reconstruction_fluent_theme"):
        return

    accent = _system_accent(application)
    application.setStyle("Fusion")

    families = set(QtGui.QFontDatabase.families())
    font = QtGui.QFont(application.font())
    if "Segoe UI Variable" in families:
        font.setFamily("Segoe UI Variable")
    elif "Segoe UI" in families:
        font.setFamily("Segoe UI")
    font.setPointSizeF(9.5)
    application.setFont(font)
    application.setStyleSheet(build_stylesheet(accent))
    application.setProperty("map_reconstruction_accent", accent)
    application.setProperty("map_reconstruction_fluent_theme", True)
    # Preserve the old marker for callers/tests that still key off it.
    application.setProperty("map_reconstruction_light_theme", True)
