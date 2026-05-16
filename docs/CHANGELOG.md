# Changelog

## 0.7a1 — Pre-hardware validation and version standardization

- Hardened Windows `.bat` and `.ps1` launchers for project roots containing spaces, hyphens, and university/network-folder names. Added `tests/test_launcher_space_safe.py` to prevent path-quoting regressions.

- Standardized the branch version to PEP 440 form `0.7a1` and added automated version consistency tests across runtime metadata, `pyproject.toml`, validation scripts, and handoff docs.
- Added `drivers/command_plan.py` for side-effect-free Keithley 2400 command-plan review before hardware bring-up.
- Added mock serial command-sequence tests for voltage-source and current-source sweeps.
- Added pre-hardware safety tests for output-off behavior on exceptions and early stop paths.
- Added trace-list multi-select deletion using Delete/Backspace or the context menu while preserving multi-selection on right-click.
- Added `docs/HARDWARE_VALIDATION_PROTOCOL.md` and made coverage >=95% a validation gate for the unit-testable core/hardware subset.
- Promoted `PACKAGE_NAME` to `happymeasure` and added a public `happymeasure` command/module namespace while retaining `keith_ivt` compatibility imports and fallback launch paths.

## 0.6.0-alpha.5 — Architecture/logging consolidation

- Reduced the public `SimpleKeithIVtApp` direct inheritance chain from 18 mixins to three grouped composition layers in `ui/app_mixins.py`: app chrome, workflow, and plot/trace.
- Kept focused implementation modules intact to avoid a risky rewrite while making the composition root easier for agents to inspect.
- Routed runtime errors, uncaught exceptions, and Tk callback exceptions through the central `logging_config.setup_logging()` path.
- Kept `AppLog` as the single user-visible `logs/log.txt` writer and mirrored UI events to the developer logger without duplicating `log.txt` writes.
- Updated agent docs to lower release blockers: mixin grouping and logging unification are now addressed; full real-hardware bench validation remains a human pre-beta checklist item.

## 0.6.0-alpha.4 — Simulator current-source diode and About-scroll hotfix

- Fixed console `TclError: invalid command name ...canvas` from the About page by replacing the global mousewheel binding with guarded widget-local bindings.
- Improved the diode debug simulator in current-source mode: it now inverts the same diode I(V) model used by voltage-source mode and reports compliance-limited actual diode current when a requested current is unreachable.
- Changed Linear and Log plot views to present standard I-V data consistently for both source modes: x = voltage, y = current. This makes current-source diode sweeps visually comparable with voltage-source diode sweeps.
- Added regression tests for the About scroll binding, current-source diode compliance behavior, and current-source I-V plotting orientation.

## 0.6.0-alpha.3 — Live plot stale-cache stability and handoff cleanup

- Fixed the intermittent real-time plotting blank-screen bug: cached Matplotlib `Line2D` objects are now revalidated against the active `Axes`, so updates after `figure.clear()`, view/layout changes, sweep type/mode changes, or repeated live runs cannot silently target detached artists.
- Cleared the live renderer cache before full redraw and empty-live placeholder paths.
- Kept the `0.6.0-alpha.2` axis-limit fix: incremental live updates still call `relim()` and `autoscale_view()` so sweeps outside Matplotlib's default `0..1` range remain visible.
- Added live-plot regression coverage for autoscale, stale artist recreation, and full-redraw cache invalidation contracts.
- Added `.gitignore`, removed generated logs/caches from release packaging, updated current-version docs, and recorded architecture debt in `docs/TECH_DEBT_AGENT_NOTES.md`.

## 0.6.0-alpha.2 — Live plot autoscale and agent handoff cleanup

- Fixed real-time plotting in the incremental renderer: after updating cached `Line2D` data, touched axes call `relim()` and `autoscale_view()` so live sweeps outside the default `0..1` Matplotlib limits are visible.
- Removed transient `Waiting for data...` text when the first live data points arrive.
- Changed live plot color selection to use the active UI palette accent instead of a hard-coded blue.
- Clarified handoff structure: `README.md` is human-facing; `docs/AGENT_START_HERE.md` and `docs/AGENT_HANDOFF.md` are agent-facing; `tests/README.md` maps behavior-oriented test names.
- Renamed historical alpha-numbered tests to behavior-oriented file names and updated validation scripts.

## 0.6.0-alpha.2 — Trace/log/font/export consolidation

- Fixed log rotation when the KB threshold is lowered and applied `Log max KB` changes immediately from Settings.
- Changed the default UI font to Verdana and changed the UI font menu to read installed system fonts rather than a hard-coded list.
- Removed hex color text from the trace Color column.
- Enabled multi-select in the trace list and plot highlighting for selected traces; when traces exist, at least one trace is always selected.
- Improved preset review dialogs, trace export naming, combined CSV metadata, and visible/selected trace export wording.
- Moved preset action buttons above the preset list and redesigned the About panel for a clearer human-facing UI.
- Added Restart UI and Ctrl+MouseWheel log font zoom support.

## 0.5.0-alpha.5 — Navigation responsiveness and label-background polish

- Replaced laggy navigation drawer width animation with a single layout commit.
- Cleaned Light-theme label backgrounds by aligning ordinary and muted labels with the dominant card background.
- Preserved large-font/high-DPI Sweep usability while keeping plot-wheel zoom local to plot axes.
- Added regression tests for instant push navigation and label-background cleanup.

## 0.5.0-alpha.1 — Hardware-readiness alpha and naming cleanup

- Fixed the Adaptive table crash by importing the shared tooltip helper in `ui/sweep_config.py`.
- Added `services/serial_safety.py` with `SerialRetryPolicy` and `OutputOffGuard` for real serial bring-up.
- Added hardware preflight entry points for safe IDN + output-off preflight before the first hardware sweep.
- Moved legacy `_run_state`, `_connected`, `_running`, `_paused`, and `_stop_requested` UI access behind AppState-backed compatibility properties.
- Removed duplicate persistent UI log writes by making `AppLog` the single `logs/log.txt` writer.
- Cleaned user-facing legacy names: HappyMeasure is the product name; `keith_ivt` is documented as an internal package namespace only.

## 0.4.0-alpha.7 — Pause/Stop responsiveness and adaptive-table hotfix

- Fixed Pause/Stop responsiveness for debug/worker sweeps by creating instruments from immutable `SweepConfig` values instead of reading Tk variables in the measurement thread.
- Added explicit `_pause_event` and `_stop_event` controls so Pause/Resume/Stop state is independent of Tk variable access and AppState migration timing.
- Bounded UI queue draining in `_process_queue` and redrew at most once per Tk tick so Pause and STOP button events are not starved by rapid simulator points.
- Made `_make_config()` tolerant of both internal enum values (`TIME`) and UI/display labels (`Time`) for sweep type selection.
- Added responsive compact segment rows for the adaptive table.
- Added regression coverage for display-label config parsing and worker-safe instrument creation.

## 0.4.0-alpha.5 — Trace menu and default theme correction

- Restored trace-column gear/context-menu helper imports.
- Tightened dark/debug theme palettes and visible control borders.
- Improved simulator Stop responsiveness by replacing long interval sleeps with interruptible sleeps.

## 0.4.0-alpha.4 — Plot context-menu and connection-button hotfix

- Restored plot right-click actions with a Tk-level fallback binding.
- Added import-overlap detection for CSV imports.
- Added visible-trace export from the trace-list context menu.
- Changed Hardware COM selection from free text to a detected-port dropdown.

## 0.3.0-alpha.6 — Plot/trace regression fix and beta-hardening foundations

- Stabilized early plot/trace behavior and continued migration from the monolithic MATLAB-era workflow toward a modular Python alpha.

### Packaging update

Added Windows portable-app packaging support: `packaging/happymeasure_entry.py`, `packaging/HappyMeasure.spec`, `tools/build/Build_Portable_Windows_App.bat`, `tools/build/Build_Portable_Windows_App.ps1`, and `docs/WINDOWS_PORTABLE_BUILD.md`. Build output should be `dist\HappyMeasure\HappyMeasure.exe` plus its `_internal` resources folder.



### Windows build note: Python 3.14 / temp log PermissionError

The portable-app build scripts now reject stale or unsupported `.venv` environments and rebuild with Python 3.11-3.13. This avoids Windows `PermissionError: [WinError 32]` failures seen when Python 3.14 keeps temporary log files open during validation. If the build still fails, delete `.venv`, close any running HappyMeasure/Python windows, and rerun `tools\build\Build_Portable_Windows_App.bat`.


### Build launcher Python detection fix

The Windows portable build launcher now verifies actual interpreter availability before selecting `py -3.13` / `py -3.12` / `py -3.11`. If only Python 3.14+ is installed, the launcher attempts a fallback build and prints a warning; Python 3.12 remains the recommended release-build interpreter.

### Build script hotfix: Python launcher loop fix

- Rebuilt `tools/build/Build_Portable_Windows_App.bat` from scratch after a bad merge duplicated the Python detection block.
- Batch build now uses a single `:pick_python` routine and prefers Python 3.12, then 3.11, then 3.13, with PATH `python` as fallback.
- PowerShell build script now uses valid version checks and the same selection order.
- Added `tests/test_windows_build_script_integrity.py` to catch duplicated/corrupted build script blocks.
