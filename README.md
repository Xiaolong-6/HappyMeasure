# HappyMeasure

HappyMeasure is a Windows-friendly Tkinter + Matplotlib measurement application for Keithley-style source-measure workflows, with an optional standalone Map Reconstruction application.

Current source candidate: **`1.1b6` (1.1 beta 6)**.

> `1.1b6` is a source/release candidate until the packaged Windows build and the final operator hardware gate are completed. Do not describe it as hardware-verified before those checks pass.

The public product/package names are **HappyMeasure** / `happymeasure`. The historical `keith_ivt` namespace remains supported as the internal/compatibility namespace.

## Start HappyMeasure

From the repository root on Windows:

```text
Run_HappyMeasure.bat
```

or:

```powershell
.\Run_HappyMeasure.ps1
python -m happymeasure
```

Legacy `python -m keith_ivt` remains available for compatibility.

## What is in 1.1b6

- Long-running Time plots use live-only display windows, Time-specific marker policy, redraw throttling, and extrema-preserving full-range display for large completed traces. The authoritative measurement data are never truncated by display settings.
- Constant-Time acquisition adds validated Standard/Fast/Custom profiles while preserving the existing output-off safety contract and deterministic next-run configuration.
- Settings and diagnostics were reorganized; UI Diagnostics remains developer-facing and Hardware Diagnostics uses a no-DUT/output-off-only safety path.
- Export filename generation no longer duplicates underscore-containing device names or Time/Adaptive tokens.
- Map Reconstruction now has staged Signal Preparation → Reconstruction → Map Analysis workflow, reproducible `.hmmap` projects, explicit source replacement behavior, processing/color controls, and a maximized standalone startup.
- Map UI tests are a dedicated Windows CI release gate with real PySide6/pyqtgraph dependencies instead of silently skipping when Qt is absent.

See `docs/RELEASE_NOTES_v1.1b6.md` for the release-candidate summary and `docs/CHANGELOG.md` for history.

## Standalone Map Reconstruction

Install the optional GUI dependencies:

```powershell
python -m pip install -e ".[map]"
python -m map_reconstruction
```

`Run_Map_Reconstruction.bat` is the Windows launcher. Map Reconstruction imports HappyMeasure `single-v2` CSV files and supports self-contained `.hmmap` projects whose embedded source remains authoritative.

## Safe validation path

Install development dependencies:

```powershell
python -m pip install -e ".[dev]"
python tests\run_full_validation.py
```

For the Map UI gate:

```powershell
python -m pip install -e ".[dev,map]"
$env:QT_QPA_PLATFORM="offscreen"
python -m pytest -q -k "map_reconstruction or phase_window"
```

Before using real hardware, read `docs/HARDWARE_VALIDATION_PROTOCOL.md`. The hardware preflight and Hardware Diagnostics must not source voltage/current or run a measurement.

## Screenshots

![HappyMeasure hardware simulator page](docs/screenshots/happymeasure-hardware.png)

![HappyMeasure completed simulator sweep](docs/screenshots/happymeasure-sweep-result.png)

![HappyMeasure Keithley-style front-panel popup](docs/screenshots/happymeasure-front-panel-popup.png)

## Documentation

Start with `docs/README.md`. Important release documents are:

- `docs/VALIDATION_STATUS.md` — current source/desktop/hardware gate status
- `docs/RELEASE_CHECKLIST.md` — release procedure
- `docs/HARDWARE_VALIDATION_PROTOCOL.md` — staged hardware verification
- `docs/TRACE_SCHEMA.md` — CSV/import/export contract
- `docs/MAP_PROJECT_FORMAT.md` — `.hmmap` project contract
- `docs/WINDOWS_PORTABLE_BUILD.md` — Windows packaging

## Windows portable build

After source validation passes:

```bat
tools\build\Build_Portable_Windows_App.bat
```

Do not publish `build/`, `dist/`, caches, logs, local helper scripts, or test artifacts. The release artifact is the versioned portable ZIP described in `docs/RELEASE_CHECKLIST.md`.

## Attribution

HappyMeasure is inspired by the MIT-licensed MATLAB project [Keith-IVt](https://github.com/Xiaolong-6/Keith-IVt). See `NOTICE.md`.
