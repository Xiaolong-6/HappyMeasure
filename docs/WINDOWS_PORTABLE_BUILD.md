# HappyMeasure Windows Portable Build

This project can be distributed without requiring the target PC to install
Python by building a PyInstaller **onedir** portable folder on Windows.

## Build Command

From the project root, run one of:

```bat
tools\build\Build_Portable_Windows_App.bat
```

or:

```powershell
.\tools\build\Build_Portable_Windows_App.ps1
```

The standard build path searches for Python 3.12, 3.11, then 3.13, runs the
test suite, then builds:

```text
dist\HappyMeasure\HappyMeasure.exe
```

Do not copy only `HappyMeasure.exe`; the `_internal` folder is required.

## Output To Deliver

The build artifacts are the whole folder and the generated zip:

```text
dist\HappyMeasure\
dist\HappyMeasure-<version>-windows-portable.zip
```

The zip should contain `HappyMeasure.exe`, `_internal`, `README_FIRST.txt`,
`config`, `examples`, `HARDWARE_VALIDATION_PROTOCOL.md`, and
`HARDWARE_DRY_RUN_GUIDE.md`.

The temporary `build\HappyMeasure` directory is only PyInstaller's work area.
It may contain intermediate executables, `.toc` files, and warning reports
during packaging. Do not distribute anything from `build`; successful scripts
remove the `build` directory after the portable zip is created.

## Python Version For Building

Use Python 3.12, 3.11, or 3.13 on Windows for the standard build. The current
build script searches in this order:

```text
py -3.12
py -3.11
py -3.13
python, if it is one of those versions
```

For Python 3.14, use `tools\build\Build_Portable_Windows_App_Python314.bat`
or `.\tools\build\Build_Portable_Windows_App_Python314.ps1`.

## Why Onedir, Not Onefile

The app uses Tkinter, Matplotlib, and serial hardware access. A folder build is
preferred because it starts faster, is easier to debug, is less likely to lose
GUI/backend resources, and is less likely to trigger antivirus false positives.

## Hardware Safety After Packaging

The packaged app must still be validated separately from the source run:

1. Debug/simulator sweep.
2. CSV export and log writing.
3. Real Keithley connect/disconnect without DUT.
4. Confirm Output OFF on the instrument front panel.
5. Dummy resistor load.
6. Real DUT only after all previous checks pass.

## Windows Build Notes

### PowerShell Execution Policy

If PowerShell blocks unsigned scripts, run the `.bat` launcher instead:

```bat
tools\build\Build_Portable_Windows_App.bat
```

### Python 3.14 Ensurepip Temp-Directory PermissionError

On some Windows machines, Python 3.14 can fail while creating `.venv` because
`ensurepip` cannot write or clean its temporary wheel directory. The observed
error looks like:

```text
PermissionError: [Errno 13] Permission denied: ... pip-26.1.1-py3-none-any.whl
```

If that happens before the build script can create `.venv`, use a local
dependency target instead of `.venv`:

```powershell
$root = (Resolve-Path .).Path
$env:TEMP = Join-Path $root ".tmp-build"
$env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = Join-Path $root ".pip-cache"
python -m pip install --target .build-deps matplotlib pyserial pydantic pyinstaller
$env:PYTHONPATH = (Join-Path $root ".build-deps") + ";" + (Join-Path $root "src")
Push-Location packaging
python -c "from PyInstaller.__main__ import run; run(['--noconfirm','--clean','--distpath','..\\dist','--workpath','..\\build','HappyMeasure.spec'])"
Pop-Location
```

The maintained scripts normally avoid editable install during packaging and set
`PYTHONPATH=src`, so this workaround should only be needed when `.venv`
creation itself fails.

Then copy the portable first-run files:

```powershell
New-Item -ItemType Directory -Force -Path dist\HappyMeasure\logs,dist\HappyMeasure\examples,dist\HappyMeasure\config
Copy-Item packaging\README_FIRST_PORTABLE.txt dist\HappyMeasure\README_FIRST.txt
Copy-Item docs\HARDWARE_VALIDATION_PROTOCOL.md dist\HappyMeasure\
Copy-Item docs\HARDWARE_DRY_RUN_GUIDE.md dist\HappyMeasure\
Copy-Item config\*.json dist\HappyMeasure\config\
Copy-Item examples\* dist\HappyMeasure\examples\
```

The local `.build-deps`, `.pip-cache`, `.tmp-build`, `build`, and `dist`
directories are ignored by git.
