"""Keep only the QtCore runtime; locale packs are not part of Map Reconstruction."""

from PyInstaller.utils.hooks.qt import add_qt6_dependencies


hiddenimports, binaries, _datas = add_qt6_dependencies(__file__)

# The application has no translated resource workflow. Qt falls back to its
# built-in English strings when these optional locale packs are absent.
datas = []
