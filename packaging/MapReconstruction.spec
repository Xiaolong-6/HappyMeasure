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

from PyInstaller.utils.hooks import collect_all
from pathlib import Path

pyside6_datas, pyside6_binaries, pyside6_hiddenimports = collect_all("PySide6")
pyqtgraph_datas, pyqtgraph_binaries, pyqtgraph_hiddenimports = collect_all("pyqtgraph")
numpy_datas, numpy_binaries, numpy_hiddenimports = collect_all("numpy")
PROJECT_ROOT = Path(SPECPATH).parent
MAP_ICON = PROJECT_ROOT / "src" / "map_reconstruction" / "assets" / "map_reconstruction.ico"

block_cipher = None


a = Analysis(
    ["map_reconstruction_entry.py"],
    pathex=["src"],
    binaries=pyside6_binaries + pyqtgraph_binaries + numpy_binaries,
    datas=pyside6_datas
    + pyqtgraph_datas
    + numpy_datas
    + [(str(MAP_ICON.with_suffix(".png")), "map_reconstruction/assets")],
    hiddenimports=pyside6_hiddenimports
    + pyqtgraph_hiddenimports
    + numpy_hiddenimports
    + [
        "map_reconstruction",
        "map_reconstruction.models",
        "map_reconstruction.preparation",
        "map_reconstruction.processing",
        "map_reconstruction.project_io",
        "map_reconstruction.reporting",
        "map_reconstruction.display_units",
        "map_reconstruction.importers",
        "map_reconstruction.ui",
        "keith_ivt.version",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "pytest_cov", "black", "ruff", "mypy", "matplotlib", "tkinter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MapReconstruction",
)
