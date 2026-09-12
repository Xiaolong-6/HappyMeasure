# -*- mode: python ; coding: utf-8 -*-
r"""PyInstaller spec for the standalone Map Reconstruction portable build.

Build on Windows from the project root with:
    pyinstaller --noconfirm --clean packaging\MapReconstruction.spec

The output folder will be:
    dist\MapReconstruction\MapReconstruction.exe

This is a companion post-processing tool to HappyMeasure. It bundles its own
Qt/plotting stack plus the shared HappyMeasure file-format, schema and version
helpers it needs for CSV/.hmmap import; it does not bundle the HappyMeasure
Tk acquisition app, serial drivers or simulator.
"""

from pathlib import Path

PROJECT_ROOT = Path(SPECPATH).parent
MAP_ICON = PROJECT_ROOT / "src" / "map_reconstruction" / "assets" / "map_reconstruction.ico"

block_cipher = None

# The application imports only these PySide6 bindings.  PyInstaller's Qt
# hooks add the platform plugin and the transitive QtGui/QtWidgets runtime
# files; collecting all of PySide6 would also ship WebEngine, Quick/QML, 3D,
# Designer, multimedia, and every translation/resource pack.
required_hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
]


a = Analysis(
    ["map_reconstruction_entry.py"],
    pathex=["src"],
    binaries=[],
    datas=[(str(MAP_ICON.with_suffix(".png")), "map_reconstruction/assets")],
    hiddenimports=required_hiddenimports,
    hookspath=[str(PROJECT_ROOT / "packaging" / "hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Never pull optional Qt modules through a broad hook or a future
        # dependency.  None is imported by the Map UI.
        "PySide6.Qt3DAnimation",
        "PySide6.Qt3DCore",
        "PySide6.Qt3DExtras",
        "PySide6.Qt3DInput",
        "PySide6.Qt3DLogic",
        "PySide6.Qt3DRender",
        "PySide6.QtBluetooth",
        "PySide6.QtCharts",
        "PySide6.QtConcurrent",
        "PySide6.QtDataVisualization",
        "PySide6.QtDesigner",
        "PySide6.QtGraphs",
        "PySide6.QtGraphsWidgets",
        "PySide6.QtHelp",
        "PySide6.QtHttpServer",
        "PySide6.QtLocation",
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
        "PySide6.QtNetwork",
        "PySide6.QtNetworkAuth",
        "PySide6.QtNfc",
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
        "PySide6.QtPositioning",
        "PySide6.QtPrintSupport",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtQuick3D",
        "PySide6.QtQuickControls2",
        "PySide6.QtQuickWidgets",
        "PySide6.QtRemoteObjects",
        "PySide6.QtScxml",
        "PySide6.QtSensors",
        "PySide6.QtSerialBus",
        "PySide6.QtSerialPort",
        "PySide6.QtSpatialAudio",
        "PySide6.QtSql",
        "PySide6.QtStateMachine",
        "PySide6.QtSvg",
        "PySide6.QtSvgWidgets",
        "PySide6.QtTest",
        "PySide6.QtTextToSpeech",
        "PySide6.QtUiTools",
        "PySide6.QtWebChannel",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineQuick",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebSockets",
        "PySide6.QtXml",
        "pytest",
        "pytest_cov",
        "black",
        "ruff",
        "mypy",
        "matplotlib",
        "tkinter",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# PyInstaller may resolve Qt6Core's generic `icuuc.dll` import to an
# unrelated host package (for example Poppler) and bundle an incompatible
# ICU implementation.  Windows supplies the ICU API used by this Qt wheel;
# keeping the host-resolved copy makes the frozen QtCore fail with
# ERROR_PROC_NOT_FOUND.  Filter only these host-side ICU names; numpy, Qt,
# and Python runtime binaries remain unchanged.
runtime_binaries = [
    item
    for item in a.binaries
    if Path(str(item[0])).name.lower() not in {"icuuc.dll", "icudt78.dll", "icuin78.dll"}
]

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MapReconstruction",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(MAP_ICON),
)
coll = COLLECT(
    exe,
    runtime_binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MapReconstruction",
)
