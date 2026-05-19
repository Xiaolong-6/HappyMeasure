# Changelog

## 1.1b2 — Step/Adaptive hysteresis sweep beta

- Added optional forward/reverse hysteresis for finite Step and Adaptive sweeps. The default is OFF so existing presets and workflows keep their previous one-way source sequence.
- Placed the hysteresis toggle directly below `Sweep type`, replacing the stale Sweep-panel workflow note.
- Centralized finite source-sequence generation so UI point estimates and the sweep runner use the same Step/Adaptive hysteresis behavior.
- Preserved the hysteresis flag in CSV export metadata and restored it during HappyMeasure CSV import.
- Added regression coverage in `tests/test_hysteresis_sweep_values.py` and updated version consistency checks for `1.1b2`.

## 1.1b1 — Startup updater beta

- Added `Check Updates on Startup` in Settings. When enabled, HappyMeasure checks GitHub Releases shortly after launch.
- Extended the About/update-check path to prompt before installing a newer Windows portable release zip.
- Added an external PowerShell updater handoff that runs after HappyMeasure exits, downloads the latest portable zip, backs up old program files, preserves user data folders (`config`, `logs`, `exports`, `backups`, `cache`, `data`), replaces program files in the original path, and restarts the app.
- Kept update installation blocked while a sweep is running or paused.
- Updated runtime/package metadata to `1.1b1`.

## 1.0b1 — 1.0 beta candidate

- Added optional automatic Keithley-style front-panel popup behavior: Start opens the live front-panel popup by default, Stop/completion/error closes the auto-opened popup, and Settings now exposes `Auto-open Front Panel on Start` with a default of enabled.
- Fixed the plot context-menu axis-range editor on Windows/Tk packaged builds: Set X/Y range is now scheduled after the popup-menu callback returns and uses a small custom non-modal Toplevel editor instead of the built-in modal prompt. This avoids persistent ghost menus, dock auto-collapse from focus hacks, and the previous wait_visibility crash path.
- Hardened runtime console mirroring and Tk exception reporting so missing stdout/stderr streams in packaged builds cannot trigger a secondary AttributeError while logging the original exception.
- Added plot mouse interactions: left-drag pans the active plot axes, and hovering near a visible data point shows a small X/Y coordinate annotation for that point.

- Renamed the release line from pre-hardware alpha to `1.0 beta 1` / `1.0b1` while keeping the simple PEP 440 internal version.
- Kept `happymeasure` as the public package/CLI namespace and `keith_ivt` as the compatibility implementation namespace.
- Hardened state-machine behavior, Stop/Abort output-off cleanup, simulator fault injection, and non-finite readback handling.
- Improved trace workflows: latest-trace selection, visible/hidden markers, multi-select deletion, multi-select export, and factory-setting restore.
- Improved beta UI smoke behavior: compact status bar, signed V/I/Cmpl live readout, Keithley-style front-panel popup, plot screenshot export, per-view X/Y swap, top-title hover summaries, Log restoration, and duplicate title cleanup.
- Updated release, migration, trace schema, preflight, and manual smoke documentation for beta handoff.
- Full hardware bench coverage is deferred to post-release validation; simulator/source validation and manual UI smoke remain the release gate.


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
- Kept focused implementation modules intact to avoid a risky rewrite while making the composition root easier to validate and prevents the old monolithic UI file from growing back.
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


### 2026-05-18 follow-up hotfix
- Fixed Settings save feedback so `Auto-open Front Panel on Start = No` updates the live `BooleanVar` immediately, not only after restart.
- Changed factory default debug/simulator mode to disabled (`default_debug = false`) in legacy and v2 settings models plus `config/settings.json`.
- Regression: `python -m pytest tests/test_front_panel_auto_popup_regression.py -q`.

### 2026-05-18 sweep timing hotfix
- Added a common `Delay (s)` sweep control directly after `NPLC`; default is `0.0 s`.
- Added `delay_s` to `SweepConfig`, settings, export/import metadata, persistent trace storage, and driver-neutral sweep plans.
- Keithley 2400 command planning and serial configuration now include `:SOUR:DEL <delay_s>` so the configured source-delay intent is visible before hardware use.
- Sweep timing estimates now include Keithley-style NPLC aperture (`NPLC / line_frequency`), user delay, and serial/readback overhead. Constant-time estimates use the larger of the requested interval and the per-point acquisition lower bound.
- `SweepRunner` applies the user delay between source programming and readback so simulator/debug timing follows the same UI setting.
- Regression: `PYTHONPATH=src python -m pytest tests/test_delay_timing_regression.py tests/test_core_coverage_gaps.py tests/test_settings_v2.py tests/test_data_import_export_store.py tests/test_mock_visa_command_sequence.py tests/test_pre_hardware_safety.py tests/test_services_drivers_more.py -q`.

- Sweep timing estimate now includes NPLC aperture, user delay, and a baud-rate-aware serial communication overhead (source command + `:READ?` + ASCII response), so predicted time is closer to real Keithley 2400 runs.
- Adaptive sweep table no longer shows a nested internal scrollbar; the page-level scrollbar now handles the whole Sweep panel.

- Fixed Sweep/Adaptive page scrolling after removing the nested adaptive-table scrollbar: the page-level scrollregion is now refreshed after dynamic table rebuilds.
- STOP/completion/error paths now zero the live status-bar and Keithley-style front-panel readout instead of leaving stale last-point values.
