# HappyMeasure Windows Portable Build

HappyMeasure is distributed on Windows as a PyInstaller **onedir** portable folder. This document owns the common packaging contract. Python 3.14-specific exceptions/workarounds live in `WINDOWS_PYTHON314_BUILD.md`.

## Standard build

From the repository root, run one of:

```bat
tools\build\Build_Portable_Windows_App.bat
```

```powershell
.\tools\build\Build_Portable_Windows_App.ps1
```

The standard launcher uses a supported Windows Python in this order:

```text
Python 3.12
Python 3.11
Python 3.13
```

For a Python 3.14-specific build, use the dedicated `Build_Portable_Windows_App_Python314` launcher and read `WINDOWS_PYTHON314_BUILD.md`.

Source release gates must already be green before packaging. Packaging is not a substitute for CI/source validation.

## Deliverable

A successful build creates:

```text
dist\HappyMeasure\HappyMeasure.exe
dist\HappyMeasure\_internal\
dist\HappyMeasure-<version>-windows-portable.zip
```

Distribute the complete `dist\HappyMeasure\` folder or the versioned portable ZIP. Never distribute `HappyMeasure.exe` alone; the `_internal` directory is required by the onedir build.

The portable package should include the maintained first-run/support files copied by the build scripts, including:

```text
README_FIRST.txt
config\
examples\
HARDWARE_VALIDATION_PROTOCOL.md
HARDWARE_DRY_RUN_GUIDE.md
```

`build\` is PyInstaller working state, not a deliverable. Local `.build-deps`, `.pip-cache`, `.tmp-build`, `build`, and `dist` are build/runtime artifacts and must not be committed.

## Why onedir

HappyMeasure uses Tkinter, Matplotlib, serial hardware access, and optional Map Reconstruction dependencies. A folder build is preferred because it is easier to inspect/debug, avoids onefile extraction overhead, and keeps packaged resources explicit.

## Package smoke test

After building, test the actual packaged executable, not only the source checkout:

1. Launch `dist\HappyMeasure\HappyMeasure.exe` and close it cleanly.
2. Run a short debug/simulator acquisition.
3. Verify CSV export/import and log writing.
4. Verify STOP/Pause/restart paths used by the current UI.
5. Launch Map Reconstruction if it is included/supported by the package.
6. Check About/update metadata UI for import/runtime errors.

Record the final ZIP size and SHA-256 in the release notes/checklist evidence before publication.

## Hardware safety after packaging

The packaged application requires its own staged hardware check:

1. Simulator/package smoke.
2. No-DUT communication/output-off preflight.
3. Confirm physical Output OFF on the instrument front panel.
4. Dummy resistor/load test with conservative compliance.
5. Real DUT only after previous gates pass.

Follow `HARDWARE_VALIDATION_PROTOCOL.md`; a successful package build is not hardware verification.

## Windows notes

If PowerShell execution policy blocks a `.ps1` launcher, use the matching `.bat` launcher.

For Python 3.14 temp-directory/`ensurepip` problems or the repository-local dependency-target fallback, use `WINDOWS_PYTHON314_BUILD.md` rather than duplicating a second packaging recipe here.
