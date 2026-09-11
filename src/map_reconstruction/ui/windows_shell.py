"""Best-effort Windows 11 shell integration for the Qt workspace.

The scientific UI remains ordinary PySide6.  On Windows 11 we ask DWM for the
native rounded-corner and Mica main-window backdrop attributes; on older Windows
or non-Windows platforms the function quietly falls back to normal Qt chrome.
"""

from __future__ import annotations

import ctypes
import sys
from typing import Final

from PySide6 import QtWidgets

_DWMWA_USE_IMMERSIVE_DARK_MODE: Final = 20
_DWMWA_WINDOW_CORNER_PREFERENCE: Final = 33
_DWMWA_SYSTEMBACKDROP_TYPE: Final = 38
_DWMWCP_ROUND: Final = 2
_DWMSBT_MAINWINDOW: Final = 2
_WINDOWS_11_BUILD: Final = 22000


def _set_dwm_int(hwnd: int, attribute: int, value: int) -> bool:
    try:
        dwmapi = ctypes.windll.dwmapi  # type: ignore[attr-defined]
        data = ctypes.c_int(value)
        result = dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd),
            ctypes.c_uint(attribute),
            ctypes.byref(data),
            ctypes.sizeof(data),
        )
        return int(result) == 0
    except (AttributeError, OSError, ValueError):
        return False


def apply_windows_11_shell(window: QtWidgets.QWidget) -> bool:
    """Apply native Windows 11 shell effects without changing app behavior.

    Returns ``True`` when at least one DWM attribute was accepted.  The helper is
    deliberately decoration-only: it does not replace the native title bar,
    install custom hit testing, or alter resize/minimize/maximize semantics.
    """

    central = getattr(window, "centralWidget", lambda: None)()
    if isinstance(central, QtWidgets.QWidget):
        central.setObjectName("mapAppSurface")
        style = central.style()
        if style is not None:
            style.unpolish(central)
            style.polish(central)

    if sys.platform != "win32":
        return False
    try:
        if sys.getwindowsversion().build < _WINDOWS_11_BUILD:  # type: ignore[attr-defined]
            return False
        hwnd = int(window.winId())
    except (AttributeError, TypeError, ValueError):
        return False

    applied = False
    # The application is intentionally light-themed.  Setting this explicitly
    # lets Windows render native caption buttons consistently with the Qt shell.
    applied |= _set_dwm_int(hwnd, _DWMWA_USE_IMMERSIVE_DARK_MODE, 0)
    applied |= _set_dwm_int(hwnd, _DWMWA_WINDOW_CORNER_PREFERENCE, _DWMWCP_ROUND)
    applied |= _set_dwm_int(hwnd, _DWMWA_SYSTEMBACKDROP_TYPE, _DWMSBT_MAINWINDOW)
    return applied
