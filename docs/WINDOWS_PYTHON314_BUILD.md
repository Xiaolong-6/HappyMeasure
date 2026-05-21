# Windows Portable Build With Python 3.14

This package intentionally includes a Python 3.14-targeted portable-app build
path.

## One-Click Build

From Windows, double-click:

```text
tools\build\Build_Portable_Windows_App_Python314.bat
```

or:

```text
.\tools\build\Build_Portable_Windows_App_Python314.ps1
```

The script only uses Python 3.14. It does not search for Python 3.13/3.12/3.11.

## Output

A successful build creates:

```text
dist\HappyMeasure\HappyMeasure.exe
dist\HappyMeasure-<version>-windows-portable.zip
```

Distribute the whole folder:

```text
dist\HappyMeasure\
```

Do not distribute only `HappyMeasure.exe`, because PyInstaller onedir builds
need the bundled internal files.

Ignore `build\HappyMeasure` if you see it during packaging. It is PyInstaller's
temporary work area, not a deliverable app. Successful scripts remove it after
the portable zip is created.

## Validation Policy For This Build Path

The Python 3.14 build script runs an import smoke check and then packages with
PyInstaller. It intentionally skips the full pytest validation because
Windows/Python 3.14 can keep temporary log files locked during pytest cleanup.
It installs explicit runtime/dev dependencies and sets `PYTHONPATH=src` instead
of using editable install, which avoids temp-directory permission failures seen
on some Python 3.14 Windows setups.

After packaging, validate manually in this order:

1. Launch `dist\HappyMeasure\HappyMeasure.exe`.
2. Run the debug simulator with diode/resistor/open/short.
3. Confirm CSV export works.
4. Confirm logs are written.
5. Confirm STOP returns the UI to a safe state.
6. Run hardware preflight before connecting any real DUT.

## Known Windows 3.14 Packaging Workaround

If `py -3.14 -m venv .venv` fails inside `ensurepip` with a temp-directory
`PermissionError`, the source code does not need to change. Build with a local
dependency target:

```powershell
$root = (Resolve-Path .).Path
$env:TEMP = Join-Path $root ".tmp-build"
$env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = Join-Path $root ".pip-cache"
python -m pip install --target .build-deps matplotlib pyserial pydantic pyinstaller
$env:PYTHONPATH = (Join-Path $root ".build-deps") + ";" + (Join-Path $root "src")
python -c "from PyInstaller.__main__ import run; run(['--noconfirm','--clean','--distpath','dist','--workpath','build','packaging\\HappyMeasure.spec'])"
```

After PyInstaller finishes, add the same first-run files that the build script
normally copies:

```powershell
New-Item -ItemType Directory -Force -Path dist\HappyMeasure\logs,dist\HappyMeasure\examples,dist\HappyMeasure\config
Copy-Item packaging\README_FIRST_PORTABLE.txt dist\HappyMeasure\README_FIRST.txt
Copy-Item docs\HARDWARE_VALIDATION_PROTOCOL.md dist\HappyMeasure\
Copy-Item docs\HARDWARE_DRY_RUN_GUIDE.md dist\HappyMeasure\
Copy-Item config\*.json dist\HappyMeasure\config\
Copy-Item examples\* dist\HappyMeasure\examples\
```

This workaround was used successfully on Windows 11 with Python 3.14.5,
PyInstaller 6.20.0, and Matplotlib 3.10.9. A brief packaged-app smoke test
should launch `dist\HappyMeasure\HappyMeasure.exe`, wait until the process stays
alive, then close it before hardware testing.

## If Python 3.14 Is Not Detected

Run:

```bat
py -3.14 --version
python --version
```

At least one command must report Python 3.14.
