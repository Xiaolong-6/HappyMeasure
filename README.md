# HappyMeasure

HappyMeasure is a lightweight Windows-friendly Tkinter + Matplotlib measurement UI for Keithley 2400/2450-style IV workflows.

Current version: `0.7a1` pre-hardware validation alpha.

This Python project is inspired by the MIT-licensed MATLAB project
[Keith-IVt](https://github.com/Xiaolong-6/Keith-IVt). See `NOTICE.md`.

The product name and public Python package namespace are **HappyMeasure** / `happymeasure`. The historical `keith_ivt` namespace remains available as a compatibility layer, so existing imports and older local launch commands keep working during the alpha migration.

## Start the app

Double-click:

```text
Run_HappyMeasure.bat
```

PowerShell alternative:

```text
.\Run_HappyMeasure.ps1
```

CLI launchers also support the public package namespace:

```text
python -m happymeasure
python -m happymeasure.hardware_preflight COM3 --baud 9600
```

The legacy `python -m keith_ivt` and `python -m keith_ivt.hardware_preflight` commands remain supported for compatibility.

## What changed in 0.7a1

- Standardized the public version style to PEP 440 alpha form: `0.7a1`.
- Added version consistency tests so `src/keith_ivt/version.py`, `pyproject.toml`, validation scripts, and handoff docs cannot silently drift again.
- Added pre-hardware safety validation around output-off behavior, mock Keithley command sequencing, and a side-effect-free command-plan helper.
- Added trace-list multi-select deletion: select several traces with Ctrl/Cmd or Shift, then use Delete/Backspace or right-click deletion. Right-clicking an already selected row preserves the multi-selection.
- Added a coverage gate for the unit-testable core/hardware subset. Tk widgets and real hardware entrypoints remain covered by smoke/bench procedures instead of fake unit coverage.
- Preserved the 0.6 live-plot, simulator diode, scroll, mixin, and logging fixes.
- Hardened Windows launchers for project paths containing spaces, hyphens, and university/network-folder names; added launcher path-safety regression tests.
- Promoted `happymeasure` to the public package/CLI namespace while retaining `keith_ivt` as a legacy compatibility namespace.

## Safe validation path

Install developer test tools first:

```text
python -m pip install -r requirements-dev.txt
```

Run simulator/unit validation first:

```text
python tests\run_full_validation.py
python -m pytest -q
python -m pytest --cov=keith_ivt -q
```

Run the update reminder tests:

```text
python -m pytest tests/test_update_check.py -q
```

Run release-hardening compatibility checks:

```text
python -m pytest tests/test_config_compatibility.py tests/test_trace_schema_contract.py tests/test_hardware_preflight_cli.py -q
```

Manual smoke checks are listed in `docs/MANUAL_SMOKE_TESTS.md`. Trace/export behavior is documented in `docs/TRACE_SCHEMA.md`; hardware preflight behavior is documented in `docs/HARDWARE_PREFLIGHT.md`.


Optional desktop-only Tk smoke test:

```powershell
$env:HAPPYMEASURE_RUN_TK_SMOKE="1"
python -m pytest tests\test_ui_smoke.py -q
```

## Real hardware preflight

Before real hardware, read:

```text
docs\HARDWARE_VALIDATION_PROTOCOL.md
```

Then run only the preflight:

```text
tools\hardware\Real_Hardware_Preflight.bat
```

The preflight opens the serial port, queries `*IDN?`, sends `:OUTP OFF`, and closes the port. It must not source voltage or current.

## Human developer handoff

This README is the human-facing handoff. Public documentation is in `docs/`.

## Current human-facing status

- Simulator workflows are the supported validation path.
- Real Keithley operation is preflight-ready, but full bench validation is still pending.
- The UI default is the clean `Light` theme; `Dark` is available; `Debug` is for layout inspection.
- Verdana is the preferred default UI font when installed. The font selector reads system-installed fonts.
- During an active measurement, the plot shows live data only; stored traces return after completion.
- Trace export/import/rename/delete actions live in the trace-list context menu. Plot right-click is for plot view/range/image actions.
- Trace visibility is display-only. **Export all traces** includes hidden traces; **Export visible** filters to ticked/visible traces only. Renamed traces are exported with their edited names.
- The bottom status-bar connection/debug indicators are fixed-size Canvas drawings, so they do not depend on Windows emoji fallback or scale with the app UI font setting.
- Start is valid from `idle`, `stopped`, `completed`, and `aborted` ready states; repeated simulator runs should not require restarting the app.

## Developer architecture note

`src/keith_ivt/ui/simple_app.py` is intentionally kept as a compact composition root. Feature behavior should live in focused UI mixins/modules such as `update_controller.py`, `sweep_controller.py`, `hardware_controller.py`, and `trace_panel.py`. This keeps the Tkinter shell easier to validate and prevents the old monolithic UI file from growing back.

## Manual update checks

App only checks GitHub release metadata. It does not auto-download, auto-install, or replace files. Users must upgrade manually from the Release page.

## Where to look next

Human developer: start here, then use these files only as needed:

```text
CONTRIBUTING.md
docs\HARDWARE_VALIDATION_PROTOCOL.md
docs\HARDWARE_DRY_RUN_GUIDE.md
docs\WINDOWS_PORTABLE_BUILD.md
docs\RELEASE_CHECKLIST.md
docs\CHANGELOG.md
tests\README.md
```

## Windows portable app build

To build a version that runs on a Windows PC without requiring Python on the target machine, run from the project root:

```bat
tools\build\Build_Portable_Windows_App.bat
```

or:

```powershell
.\tools\build\Build_Portable_Windows_App.ps1
```

The output is `dist\HappyMeasure\HappyMeasure.exe`. Distribute the entire `dist\HappyMeasure` folder as a zip; do not copy only the exe. See `docs/WINDOWS_PORTABLE_BUILD.md`.



### Windows build note: Python 3.14 / temp log PermissionError

The portable-app build scripts now reject stale or unsupported `.venv` environments and rebuild with Python 3.11-3.13. This avoids Windows `PermissionError: [WinError 32]` failures seen when Python 3.14 keeps temporary log files open during validation. If the build still fails, delete `.venv`, close any running HappyMeasure/Python windows, and rerun `tools\build\Build_Portable_Windows_App.bat`.

## Windows portable build with Python 3.14

To build a Python-free portable Windows folder app using your installed Python 3.14, double-click:

```text
tools\build\Build_Portable_Windows_App.bat
```

The output is `dist\HappyMeasure\HappyMeasure.exe`. Distribute the whole `dist\HappyMeasure` folder, not only the exe. See `docs/WINDOWS_PYTHON314_BUILD.md`.

### Measurement safety note

Operator Stop/Abort is treated as a safety path. If a sweep is interrupted by the operator, HappyMeasure attempts to turn the SMU output off even when the normal-completion option would leave output enabled. A completed sweep still respects the configured `output_off_after_run` behavior.


### Simulator fault-injection safety tests

The debug simulator includes deterministic fault-injection hooks used by tests only. These hooks cover connect failures, read failures, non-finite readbacks, and output-off failures so the safety/error paths can be validated before real hardware testing. Normal UI simulator behavior is unchanged unless a test explicitly passes a `SimulatorFaultProfile`.

### Status icon rendering

The bottom status bar uses fixed-size Canvas icons for connection/debug indicators instead of emoji glyphs. This avoids Windows/Tk emoji fallback problems where red/green lamps can render as monochrome or striped symbols. Status text still follows the selected UI font, but the lamp and simulator gear icons keep fixed dimensions.

