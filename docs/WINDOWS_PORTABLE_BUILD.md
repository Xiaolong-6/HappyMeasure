# HappyMeasure Windows Portable Build

HappyMeasure is distributed on Windows as a PyInstaller **onedir** portable folder. Python 3.14-specific exceptions/workarounds live in `WINDOWS_PYTHON314_BUILD.md`.

The current deliverable is:

- `HappyMeasure-<version>-windows-portable.zip`

The former desktop Map Reconstruction portable application was retired from this repository. Browser Map Reconstruction is maintained separately in `Xiaolong-6/HM-Map-Reconstruction`.

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

Source release gates must already be green before packaging. Packaging is not a substitute for CI/source validation. Build scripts use dedicated `.venv-build*` environments and never touch the developer `.venv`.

## HappyMeasure deliverable

A successful build creates:

```text
dist\HappyMeasure\HappyMeasure.exe
dist\HappyMeasure\_internal\
dist\HappyMeasure-<version>-windows-portable.zip
```

Distribute the complete `dist\HappyMeasure\` folder or the versioned portable ZIP. Never distribute `HappyMeasure.exe` alone; the `_internal` directory is required by the onedir build.

The portable package includes maintained first-run/support files copied by the build scripts, including:

```text
README_FIRST.txt
config\
examples\
HARDWARE_VALIDATION_PROTOCOL.md
HARDWARE_DRY_RUN_GUIDE.md
```

`build\` is PyInstaller working state, not a deliverable. Local `.build-deps`, `.pip-cache`, `.tmp-build`, `build`, and `dist` are build/runtime artifacts and must not be committed.

## Why onedir

HappyMeasure uses Tkinter, Matplotlib and serial hardware access. A folder build is preferred because it is easier to inspect/debug, avoids onefile extraction overhead, and keeps packaged resources explicit.

## Automated package audit

After the portable build, run:

```powershell
python tools\release\audit_portable_artifacts.py --dist dist --manifest dist\release-artifacts.json
```

The audit checks:

- the versioned ZIP and onedir folder exist;
- required EXE, `_internal` and first-run files are present;
- generated logs, caches, tests, build directories and hardware-smoke artifacts are not packaged;
- packaged text contains no known private identifiers or workstation-specific home paths; and
- SHA-256, compressed size, extracted size and file count are written to `release-artifacts.json`.

## CI package gate

On every push to `main`, the `Windows portable package smoke (Python 3.12)` job runs after the source gates pass. It builds HappyMeasure, runs the artifact audit, smoke-launches the frozen executable, and uploads the ZIP plus `release-artifacts.json` as a short-lived workflow artifact.

For release evidence, use the package job from the **exact final commit**. A green package job from an older commit does not validate a newer source tree.

## Package smoke boundary

The automated frozen-EXE smoke proves that the packaged HappyMeasure application can start and remain alive on the Windows runner. Source-level UI regression suites separately cover state flow, settings/diagnostics behavior, Time-history switching and trace/export behavior.

Before public release, visually inspect the final packaged UI once and refresh stale README screenshots. This visual/documentation check does not require another hardware bench session.

## Hardware evidence after packaging

A package rebuild does not invalidate already-recorded real-hardware evidence when the intervening source changes do not alter serial I/O, output safety, acquisition sequencing or hardware cleanup. The current retained MODEL 2401 no-DUT evidence is defined in `VALIDATION_STATUS.md`.

If a later commit materially changes those hardware paths, rerun only the relevant staged hardware checks. Do not require a resistor/DUT session merely because the Windows artifact was rebuilt.

## Windows notes

If PowerShell execution policy blocks a `.ps1` launcher, use the matching `.bat` launcher.

For Python 3.14 temp-directory/`ensurepip` problems or the repository-local dependency-target fallback, use `WINDOWS_PYTHON314_BUILD.md` rather than duplicating a second packaging recipe here.
