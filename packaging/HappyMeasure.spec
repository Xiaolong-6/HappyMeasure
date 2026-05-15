# -*- mode: python ; coding: utf-8 -*-
r"""PyInstaller spec for HappyMeasure portable Windows folder builds.

Build on Windows from the project root with:
    pyinstaller --noconfirm --clean packaging\HappyMeasure.spec

The output folder will be:
    dist\HappyMeasure\HappyMeasure.exe
"""

from PyInstaller.utils.hooks import collect_all

matplotlib_datas, matplotlib_binaries, matplotlib_hiddenimports = collect_all("matplotlib")

block_cipher = None


a = Analysis(
    ["happymeasure_entry.py"],
    pathex=["../src"],
    binaries=matplotlib_binaries,
    datas=matplotlib_datas,
    hiddenimports=matplotlib_hiddenimports
    + [
        "serial",
        "serial.tools.list_ports",
        "tkinter",
        "tkinter.ttk",
        "matplotlib.backends.backend_tkagg",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "pytest_cov", "black", "ruff", "mypy"],
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
    name="HappyMeasure",
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="HappyMeasure",
)
