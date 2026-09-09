# Changelog

## Unreleased — Continuous Time timing and RS-232 throughput

- Map Reconstruction now initializes fresh-file timing anchors from the loaded
  trace span, keeps Samples / pixel and raw exports visible when only map
  processing fails, and restores processed views after the setting is fixed.
  Processing controls now distinguish raw, normalization-reference, and
  processed units; Point period is explicitly shown in seconds. Removed a
  duplicate map splitter attachment and added synthetic single-v2 load and
  UI-state regression coverage.
- Refined the optional Map Reconstruction Qt workspace with a light scientific
  theme, compact action header, sectioned inspector, empty states, QC summary
  rows, light PyQtGraph plots, and map/sample-count color scales. The importer,
  dual-offset reconstruction, orientation, and raw exported array semantics
  are unchanged.
- Added an explicit Qt-free Map Values processing pipeline. Raw signed values
  are the default; baseline subtraction, absolute/negate/custom transforms,
  normalization, log10, and auto/percentile/manual color levels are explicit
  choices. Color clipping and display-unit scaling never alter scientific map
  arrays. Custom expressions use a restricted AST evaluator with no Python
  execution or attribute access.
- Map export now offers Raw, Processed, or Both. Processed exports remain in
  scientific units and include a JSON sidecar with processing metadata; the
  raw export remains the unmodified `ReconstructionResult.values` array.
- Added distinct HappyMeasure and Map Reconstruction application icons. The
  supplied blue HappyMeasure mark and green Map Reconstruction mark are used
  by their respective windows; the HappyMeasure mark is also embedded in the
  Windows portable executable.
- Hardened Map Reconstruction processing semantics: degenerate normalization
  now fails explicitly, physical log10 labels retain source units, and custom
  expression/reference processing remains unitless without changing raw
  scientific values. Processed-export metadata now separates source physical
  unit from display unit and scale.
- Split the optional Map Reconstruction UI into inspector, trace, map/QC, and
  exporting components while keeping `main_window.py` as the lifecycle
  composition root. Raw/Processed/Both export actions now share the focused
  export workflow, with Both using one base-name dialog.
- Hardened Map Reconstruction against stale or misleading output: invalid
  timing clears derived views and disables export, while a timing solution with
  zero valid pixels reports an empty map rather than displaying fabricated
  zeros. Signal selection now updates raw trace, map, and QC together.
- Added editable Point period registration, a compact raw-trace guide key,
  decimated guide rendering, a one-million-pixel reconstruction guard, and
  display-only Current (µA) / Voltage (V) scaling shared by raw, map, and
  distribution views. Scientific arrays and exported CSV values remain SI.
- Added a complete synthetic MATLAB Dual Offset parity regression and moved
  histogram QC calculations out of the optional UI package for headless
  coverage.
- Added a read-only Map Reconstruction Distribution QC tab beside Samples /
  pixel. It histograms only finite scientific map values with mean and median
  references; display orientation, sample counts, and exported values remain
  unchanged.
- Added the standalone optional `map_reconstruction` package and
  `map-reconstruction` console entry point. It imports HappyMeasure `single-v2`
  CSV files with CSV-aware metadata parsing and reconstructs 2-D maps using the
  dual-offset timing method without coupling to HappyMeasure's instrument/UI
  runtime. Install GUI dependencies with `pip install -e ".[map]"`.
- Successful real Keithley 2400-series detection now attempts one short
  instrument-side confirmation beep; beep failure is logged as degraded UX and
  does not invalidate an otherwise successful connection. Debug simulator
  connections remain silent.
- Active measurement workers now best-effort request Windows
  `ES_SYSTEM_REQUIRED` through `SetThreadExecutionState`. The display may still
  turn off, the request lasts only for the worker lifecycle (including Pause),
  and completion, Stop, Abort, or error releases it. Non-Windows platforms are
  safe no-ops, and user-initiated lock/sleep/lid-close actions are not blocked.
- Constant Time `Interval (s)` now uses one start-to-start deadline scheduler in
  both finite and continuous modes. Acquisition elapsed time starts after reset,
  configuration, output enable, and the initial source command complete.
- A read overrun rebases the next deadline immediately, preserving fast recovery
  without a transient catch-up burst; Pause/Resume also rebases instead of
  replaying missed deadlines.
- Finite Constant Time point generation now keeps an exact duration endpoint
  when binary floating-point division lands just below an integer ratio.
- Native `MeasurementService.run_plan()` now uses the same deadline/rebase
  cadence for finite Constant Time plans as the current UI runner.
- Constant Time validation now uses only the NPLC aperture and configured delay;
  serial transfer estimates remain ETA/throughput information rather than a
  hard rejection of short requested intervals.
- Fixed current measurement ranges skip redundant per-point `RANG:AUTO?` and
  `RANG?` queries, including after a runtime Auto → Fixed action, while explicit
  range actions still refresh state and preserve settle/discard handling.
- Constant Time's `Duration (s)` row now disables both its label and entry when
  `Constant until Stop` is enabled, preserves the previous finite value, and
  reapplies the state after dynamic sweep-field rebuilds.
- The Keithley 2400 driver disables automatic/programmed source delay so the
  runner's configured delay is applied exactly once for simulator and serial
  runs.
- Added `tools/hardware/keithley2400_smoke.py` and its Windows launcher for
  disconnected, 0 V, voltage-source/current-measure, 2-wire Keithley
  2400/2401 smoke testing. The runner records timing statistics, range-query
  behavior, pause/resume rebase, stop/restart, output-off, and optional power
  guard observations without requiring a DUT.
- The 2026-09-08 no-DUT bench run on a Keithley 2401 passed Mode 1 QUICK and
  Mode 2 FULL, including fixed-range `0` queries versus auto-range `66`
  queries. The optional battery sleep-prevention Mode 3 remains a separate
  operator-run check and was not completed in that session.

## 1.1b5 — Sweep direction and recovery hardening

- Changed Step and Adaptive segment step semantics to magnitude-only; Start and
  Stop determine ascending or descending direction while either step sign
  remains accepted.
- Added canonical UI-thread preflight validation before worker creation so
  invalid configurations do not enter Preparing/Running or touch instrument
  output.
- Added explicit rejection of NaN and infinite active sweep values across Step,
  finite Time, manual output, compliance, NPLC, delays, and fixed ranges.
- Made runtime sweep errors transient: HappyMeasure records and displays the
  error, clears live sweep/range state, closes the auto-opened front panel, and
  returns through `AppAction.FORCE_IDLE` so a connected operator can retry.
- Preserved existing runner/service `output_off()` safety paths and added
  focused direction, hysteresis, preflight, retry, recovery, and fault tests.
- Added root `AGENTS.md` as the stable machine-facing development entry point.

## 1.1b4 — Adaptive editor and exact presets

- Replaced the fixed Adaptive row table with a multiline `start, stop, step` editor.
- Added explicit ascending and descending syntax guidance plus line-numbered validation.
- Added an option to preserve repeated scan values or remove them globally while keeping order.
- Preserved editable segment text and the duplicate option in settings, presets, CSV metadata, and persistent storage.
- Legacy Adaptive logic is no longer expanded into dozens of segment rows; when
  no new-format segment text exists, the editor starts empty.
- Removed the nested Adaptive editor scrollbar and made its height follow the
  number of entered segment lines.
- Empty, non-numeric, or non-finite numeric fields now restore their current
  defaults on focus loss and again before a sweep configuration is created.
- Presets now use a versioned Hardware + visible Sweep snapshot, restore both
  range Auto states independently, preserve raw Adaptive text, and leave
  settings from every other page untouched.
- Update-check workers now return through the thread-safe UI event queue, so
  closing the app immediately after opening About cannot call a destroyed Tk
  interpreter.
- Added a reusable desktop user-flow smoke script covering navigation,
  responsive themes, simulator sweeps, Pause/Resume/STOP, validation errors,
  CSV/PNG output, and Preset round trips.
- Fixed PowerShell portable-build Python discovery and virtual-environment
  creation by avoiding the reserved automatic `$Args` variable.

## 1.1b3 — Keithley front-panel current range control

- Polished the front-panel current-range popup layout so labels/buttons no longer clip, range state is shown as compact Mode / Actual range / Last change summary cells, and range controls are grouped into one readable row.
- Expanded the Keithley-style front-panel popup with current autorange state, actual current range, fixed-range selection, `Lock current range`, last range-change age, settle delay, and discard-count controls.
- Added current-range SCPI accessors for Keithley 2400/2401 style drivers and deterministic simulator support for autorange actual-range changes.
- Added sweep-runner filtering so readings immediately after manual or automatic current-range changes are settled/discarded before they enter live traces, saved results, or CSV export.
- Fixed range-change filtering so discarded transient readbacks are retried at the same source setpoint instead of silently removing requested voltages from the sweep result.
- Added regression coverage in `tests/test_current_range_control.py` plus current-range SCPI assertions in `tests/test_mock_visa_command_sequence.py`.
- Fixed NPLC validation for constant-time sweeps so the interval check no longer includes serial overhead.
- Fixed CSV import/export metadata round-trip so device_name, operator, mode, and autorange are preserved correctly.

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
- Added `.gitignore`, removed generated logs/caches from release packaging, updated current-version docs, and recorded architecture debt in agent handoff notes.

## 0.6.0-alpha.2 — Live plot autoscale and agent handoff cleanup

- Fixed real-time plotting in the incremental renderer: after updating cached `Line2D` data, touched axes call `relim()` and `autoscale_view()` so live sweeps outside the default `0..1` Matplotlib limits are visible.
- Removed transient `Waiting for data...` text when the first live data points arrive.
- Changed live plot color selection to use the active UI palette accent instead of a hard-coded blue.
- Clarified handoff structure: `README.md` is human-facing; `docs/AGENT_HANDOFF.md` is agent-facing; `tests/README.md` maps behavior-oriented test names.
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

The standard portable-app build scripts now reject stale or unsupported `.venv`
environments and rebuild with Python 3.12, 3.11, or 3.13. Python 3.14 now has
dedicated `.bat` and `.ps1` launchers that skip full pytest during packaging and
avoid editable-install temp-directory permission failures by installing explicit
dependencies with `PYTHONPATH=src`.


### Build launcher Python detection fix

The Windows portable build launcher now verifies actual interpreter
availability before selecting `py -3.12` / `py -3.11` / `py -3.13`. If only
Python 3.14 is installed, use the dedicated Python 3.14 launcher.

### Build script hotfix: Python launcher loop fix

- Rebuilt `tools/build/Build_Portable_Windows_App.bat` from scratch after a bad merge duplicated the Python detection block.
- Batch build now uses a single `:pick_python` routine and prefers Python 3.12, then 3.11, then 3.13, with PATH `python` as fallback.
- PowerShell build script now uses valid version checks and the same selection order.
- Added `tests/test_windows_build_script_integrity.py` to catch duplicated/corrupted build script blocks.

### Build script hotfix: portable zip contents

- Build scripts now run PyInstaller from the project root and write directly to
  `dist\HappyMeasure`, avoiding the previous `packaging\dist` mismatch.
- Build scripts now copy `config`, `examples`, first-run README, and hardware
  validation docs into the portable folder.
- Build scripts now create `dist\HappyMeasure-<version>-windows-portable.zip`
  automatically and fail fast on dependency, smoke-check, test, or PyInstaller
  errors.


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

### 2026-05-28 Keithley front-panel range UI visual polish
- Reworked the Keithley-style front-panel current-range popup toward the mock layout: larger black readout, separate output/measure indicators, white card body, compact range summary cells, and aligned controls.
- Replaced the cramped native LabelFrame/table layout that clipped labels and buttons at normal Windows scaling.
- Kept the existing current-range behavior and tests intact; this is a visual/layout polish on top of the range-control feature.
- Regression: `PYTHONPATH=src python -m pytest tests/test_current_range_control.py -q`.
