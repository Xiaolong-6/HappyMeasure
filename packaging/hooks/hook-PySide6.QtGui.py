"""Collect only the Windows platform plugin needed by the Map UI."""

from PyInstaller.utils.hooks.qt import add_qt6_dependencies


hiddenimports, _binaries, datas = add_qt6_dependencies(__file__)

# QtGui's default hook collects every platform, image-format, input-context,
# icon-engine, and style plugin. Map Reconstruction uses a PNG application
# icon and QImage/QPainter, both handled by QtGui itself; it does not load
# runtime image files or use touch, SVG, PDF, QML, or virtual-keyboard UI.
# Keep the normal Windows desktop platform plugin only.
binaries = [
    item
    for item in _binaries
    if item[1].replace("\\", "/") == "PySide6/plugins/platforms"
    and item[0].replace("\\", "/").lower().endswith("/qwindows.dll")
]
