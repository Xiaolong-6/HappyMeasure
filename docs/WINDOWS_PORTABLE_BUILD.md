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

The current build path targets Python 3.14, runs an import smoke check, then
builds:

```text
dist\HappyMeasure\HappyMeasure.exe
```

Do not copy only `HappyMeasure.exe`; the `_internal` folder is required.

## Output To Deliver

The build artifact is the whole folder:

```text
dist\HappyMeasure\
```

For handoff, zip that folder:

```powershell
Compress-Archive -Path dist\HappyMeasure -DestinationPath dist\HappyMeasure-0.7a1-windows-portable.zip -CompressionLevel Optimal
```

The zip should contain `HappyMeasure.exe`, `_internal`, `README_FIRST.txt`,
`HARDWARE_VALIDATION_PROTOCOL.md`, and `HARDWARE_DRY_RUN_GUIDE.md`.

## Python Version For Building

Use Python 3.14 on Windows. The current build script searches in this order:

```text
py -3.14
python
```

Run source validation separately before packaging. The Python 3.14 build path
skips full pytest during packaging because Windows/Python 3.14 can keep
temporary files locked during cleanup.

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

If that happens, use a local dependency target instead of `.venv`:

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

Then copy the portable first-run files:

```powershell
New-Item -ItemType Directory -Force -Path dist\HappyMeasure\logs,dist\HappyMeasure\examples
Copy-Item packaging\README_FIRST_PORTABLE.txt dist\HappyMeasure\README_FIRST.txt
Copy-Item docs\HARDWARE_VALIDATION_PROTOCOL.md dist\HappyMeasure\
Copy-Item docs\HARDWARE_DRY_RUN_GUIDE.md dist\HappyMeasure\
```

The local `.build-deps`, `.pip-cache`, `.tmp-build`, `build`, and `dist`
directories are ignored by git.
