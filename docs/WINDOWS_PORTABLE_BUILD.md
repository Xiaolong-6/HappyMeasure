# HappyMeasure Windows Portable Build

HappyMeasure is distributed on Windows as PyInstaller **onedir** portable folders. This document owns the common packaging contract. Python 3.14-specific exceptions/workarounds live in `WINDOWS_PYTHON314_BUILD.md`.

There are two independent deliverables sharing one version:

- `HappyMeasure-<version>-windows-portable.zip`: the acquisition application.
- `MapReconstruction-<version>-windows-portable.zip`: the standalone companion post-processing application. It needs no Python, no HappyMeasure install, and no instrument.

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

## Map Reconstruction standalone build

From the repository root, run one of:

```bat
tools\build\Build_Portable_Map_Reconstruction.bat
```

```powershell
.\tools\build\Build_Portable_Map_Reconstruction.ps1
```

This installs `.[map]` from `pyproject.toml` into `.venv-build-map`, then builds `packaging\MapReconstruction.spec` with Python 3.12 preferred. A successful build creates:

```text
dist\MapReconstruction\MapReconstruction.exe
dist\MapReconstruction\_internal\
dist\MapReconstruction-<version>-windows-portable.zip
```

## HappyMeasure deliverable

A successful HappyMeasure build creates:

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

HappyMeasure uses Tkinter, Matplotlib, serial hardware access, and optional Map Reconstruction dependencies. A folder build is preferred because it is easier to inspect/debug, avoids onefile extraction overhead, and keeps packaged resources explicit.

## Automated package audit

After both portable builds, run:

```powershell
python tools\release\audit_portable_artifacts.py --dist dist --manifest dist\release-artifacts.json
```

The audit checks:

- both versioned ZIPs and onedir folders exist;
- required EXE, `_internal` and first-run files are present;
- generated logs, caches, tests, build directories and hardware-smoke artifacts are not packaged;
- packaged text contains no known private identifiers or workstation-specific home paths;
- the Map Reconstruction package stays under the release size ceiling and does not regain excluded heavy optional dependency families; and
- SHA-256, compressed size, extracted size and file count are written to `release-artifacts.json`.

The Map release ceiling is intentionally stricter than the earlier 300 MiB escalation threshold: 180 MiB extracted and 80 MiB ZIP. The current hardened baseline is substantially below those limits, leaving room for dependency drift without accepting the old oversized package behavior.

## CI package gate

On every push to `main`, the `Windows portable package smoke (Python 3.12)` job runs after all source and Map gates pass. It performs both builds, runs the artifact audit, smoke-launches the frozen HappyMeasure and Map Reconstruction executables, and uploads the two ZIPs plus `release-artifacts.json` as a short-lived workflow artifact.

For release evidence, use the package job from the **exact final commit**. A green package job from an older commit does not validate a newer source tree.

## Package smoke boundary

The automated frozen-EXE smoke proves that both packaged applications can start and remain alive on the Windows runner. Source-level UI regression suites separately cover state flow, settings/diagnostics behavior, Time-history switching, trace/export behavior and Map workflow behavior.

Before public release, visually inspect the final packaged UI once and refresh stale README screenshots. This visual/documentation check does not require another hardware bench session.

## Hardware evidence after packaging

A package rebuild does not invalidate already-recorded real-hardware evidence when the intervening source changes do not alter serial I/O, output safety, acquisition sequencing or hardware cleanup. The current retained MODEL 2401 no-DUT evidence is defined in `VALIDATION_STATUS.md`.

If a later commit materially changes those hardware paths, rerun only the relevant staged hardware checks. Do not require a resistor/DUT session merely because the Windows artifact was rebuilt.

## Windows notes

If PowerShell execution policy blocks a `.ps1` launcher, use the matching `.bat` launcher.

For Python 3.14 temp-directory/`ensurepip` problems or the repository-local dependency-target fallback, use `WINDOWS_PYTHON314_BUILD.md` rather than duplicating a second packaging recipe here.
