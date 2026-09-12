"""Do not ship an optional Qt style plugin that the app never selects."""

from PyInstaller.utils.hooks.qt import add_qt6_dependencies


hiddenimports, _binaries, datas = add_qt6_dependencies(__file__)
binaries = []
