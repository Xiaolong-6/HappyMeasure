
## 2026-09-07 sweep direction and recovery release prep

- `1.1b5` changes Step and Adaptive segment step semantics to magnitude-only;
  Start and Stop are the sole direction inputs.
- `SweepControllerMixin.start_sweep()` now calls canonical `validate_config()`
  before entering Preparing/Running or creating a worker.
- Runtime sweep errors transition through visible/logged `ERROR`, clear live
  points, worker events, current-range state/actions, and the auto-opened front
  panel, then dispatch `FORCE_IDLE` so connected sessions can retry.
- Canonical model validation rejects non-finite active source, compliance,
  timing, range, and manual-output values before hardware execution.
- Existing `SweepRunner` and `MeasurementService` output-off `finally` paths are
  unchanged. Real-hardware verification for the `1.1b5` package remains a short
  post-build gate; the final `1.1b4` package previously passed that gate.
- Release validation passed with 501 tests and 1 conditional skip at 95.14%
  coverage. The Python 3.12 portable ZIP contains all required files, and the
  packaged executable passed a five-second startup/clean-close check.
- Candidate artifact: `HappyMeasure-1.1b5-windows-portable.zip`, 45,249,186
  bytes, SHA-256
  `a4e51d1fc3871ed5f567cc1d1597526d3b58cd21aec6a7667e4dc307ee15df5e`.

## 2026-09-08 no-DUT Keithley 2401 smoke validation

- Added the repository-local `tools/hardware/keithley2400_smoke.py` runner and
  `Run_Keithley2400_Smoke.bat` launcher. The runner accepts Keithley 2400/2401
  IDs and is intentionally limited to 0 V, voltage-source/current-measure,
  2-wire, disconnected-terminal checks.
- The connected Keithley 2401 (`MODEL 2401`, firmware `B02 Jan 20 2021`) passed
  Mode 1 QUICK and Mode 2 FULL on 2026-09-08. The physical confirmation beep,
  source-delay ownership, output-off, pause/resume rebase, stop/restart, and
  fixed-versus-auto range-query checks all passed. Fixed range made 0 range
  queries; auto range made 66.
- Observed RS-232/readback floors were approximately 47 ms at NPLC 0.1 and
  94–109 ms at NPLC 1. The 10–20 ms requests were correctly classified as
  hardware-limited. This is an observation, not a new software timing limit.
- Mode 3 battery idle/sleep-prevention testing was intentionally stopped before
  the AC-unplug step and remains an operator follow-up. The generated
  `hardware_smoke_results/` artifacts are local and ignored by Git.

## 2026-09-08 Map Reconstruction v1

- A dedicated `feat/map-reconstruction-v1` branch adds the standalone
  `src/map_reconstruction/` package. It does not modify HappyMeasure's
  instrument, sweep, serial, power-guard, or Tk UI paths.
- The headless core includes a CSV-aware `single-v2` importer, generic
  `TimeSeriesData`, dual-offset timing/reconstruction, same-direction and
  serpentine orientation, sample-window/nearest fallback extraction, and
  reconstruction QC warnings. The optional PySide6/PyQtGraph UI is lazy-loaded
  by `python -m map_reconstruction` and `map-reconstruction`.
- A private single-v2 CSV was opened read-only for importer validation. No
  source data, path, metadata values, or sample-specific observations were
  copied into the repository or reported.
- With `[map]` installed, the v1 UI passed a local Qt interaction smoke using a
  private read-only single-v2 import. The native file-selection dialog and
  visually observed desktop rendering remain operator follow-ups because this
  session did not expose a targetable desktop window. Combined CSVs, live
  integration, and non-dual-offset registration remain known limitations.
- The right-hand Map Reconstruction QC area now uses tabs for `Samples /
  pixel` and a read-only `Distribution` view. The distribution takes finite
  values directly from `ReconstructionResult.values`, so display-only Flip Y
  never changes its bars, summary statistics, or mean/median reference lines.
- Map Reconstruction invalidates all prior derived state on invalid timing or
  oversized geometry, so Export Map cannot emit a stale array. A timing-valid
  reconstruction with zero finite pixels retains only zero sample counts and
  an explicit empty-map explanation. `Current_A` is displayed as Current
  (µA) consistently on trace, map, and distribution; all model and export
  arrays remain SI. `qc/distribution.py` is deliberately headless, while guide
  rendering is limited to 500 row references and 500 pixel starts per family.
- Map value processing is implemented in the headless
  `src/map_reconstruction/processing/` package. `ReconstructionResult.values`
  remains raw and authoritative; `process_map()` returns immutable
  `ProcessedMap` values, and `compute_color_limits()` only computes display
  levels. Processing-only control changes reuse the existing reconstruction.
  Custom transforms are evaluated by a restricted AST allowlist. Degenerate
  max-magnitude, min-max, and reference normalizations raise a concise
  `ValueError`; they are not silently skipped. Physical log labels preserve
  their source unit, while normalized/custom results are unitless. Raw exports
  remain SI and scientific-orientation arrays; processed exports are SI
  processed arrays with a JSON configuration sidecar that records source
  physical unit separately from display unit/scale.
- The Map Reconstruction UI composition root is intentionally small. Keep
  inspector controls in `ui/inspector.py`, trace/anchor rendering in
  `ui/trace_view.py`, map/QC rendering in `ui/map_views.py`, and file dialogs
  plus metadata serialization in `ui/exporting.py`. Changes to these widgets
  must preserve the semantic signals and compatibility aliases used by the
  existing UI regression tests.
- `src/keith_ivt/assets/happymeasure.png` and
  `src/map_reconstruction/assets/map_reconstruction.png` are the source window
  icons. Matching multi-resolution ICO files support Windows packaging; keep
  the two marks distinct.

## 2026-09-09 Map Reconstruction compact timing workspace

- The Map Reconstruction main window no longer has an application action
  header. `Open CSV` and the `Export Map` Raw/Processed/Both menu live in the
  inspector Data section; keep the main window as the composition root and do
  not move file/export behavior into reconstruction code.
- Rows and Columns start at zero and display `—`. This is the deliberate
  geometry-unset state: retain the raw trace, show `Set Rows and Columns to
  reconstruct.`, and do not create an exportable reconstruction. Do not infer
  a raster geometry from timing data.
- While anchors remain automatic, a valid geometry proposes a trace-fitting
  Dual Offset setup. Once an anchor spin box, Point period control, or trace
  guide is manually changed, `anchors_user_edited` protects those values from
  later geometry-driven initialization.
- UI timing names are YA/YB/XA/XB only; internal field names remain unchanged.
  YA/YB/XA/XB use 3 displayed decimals and 0.01 s steps; Point period uses 4
  displayed decimals and 0.001 s steps. This is presentation/input resolution
  only: do not round core calculations, `ReconstructionResult`, or exports.
- Export availability is action-specific: raw needs a raw reconstruction,
  processed needs finite processed values, and Both needs both. A
  processing-only failure must retain raw export and sample-count QC.

## 2026-09-09 Map Reconstruction reproducible projects

- `.hmmap` project persistence lives in headless `project_io.py`; do not move
  ZIP/JSON/hash logic into `main_window.py` or introduce a second authoritative
  map. The only required archive members are `project.json` and
  `source/raw_timeseries.csv`; raw bytes are preserved verbatim and checked
  against SHA-256 before the embedded CSV is imported.
- `ProjectState` stores canonical `row_a_s`/`row_b_s`/`point_a_s`/`point_b_s`,
  geometry, signal, processing in internal scientific units, and Flip Y. It
  intentionally does not store derived row/point periods or machine paths.
- Project loading uses the inspector's semantic restore API with signals
  blocked, then performs one final reconstruction. Restored anchors are marked
  user-defined so automatic geometry defaults cannot overwrite them.
- `reporting.py` keeps the parameter summary Qt-free. PDF export is optional
  Qt-only UI reporting, not a persistence format. The report includes map,
  sample-count, and raw-trace figures when a raw reconstruction exists.

## 2026-09-08 Continuous Time timing audit

- Real Keithley 2400-series connection probes attempt a short best-effort
  `:SYST:BEEP` after successful `*IDN?`; beep errors are logged without changing
  connection success. The simulator path never emits a beep.
- `ui/sweep_controller.py` wraps the worker's complete instrument lifecycle in
  `services.power_guard.prevent_system_sleep()`. On Windows it requests only
  `ES_CONTINUOUS | ES_SYSTEM_REQUIRED`, leaves display sleep allowed, keeps the
  request active during Pause, and releases it after output-off/close on every
  completion, stop, abort, and exception path. Non-Windows and API failures are
  degraded no-ops; user-initiated lock, sleep, and lid-close actions remain
  outside the application's control.
- Constant Time `interval_s` is a target start-to-start cadence in both finite
  and continuous modes. The runner uses one monotonic deadline scheduler, skips
  extra sleep when a read overruns, and rebases after an overrun or Pause so it
  never emits a catch-up burst for missed deadlines.
- `MeasurementService.run_plan()` uses the shared deadline helper for finite
  Constant Time native plans as well; STEP and Adaptive plans retain their
  ordinary per-point execution path.
- `make_constant_time_values()` uses a small floating-point tolerance when
  counting inclusive duration endpoints, so exact ratios such as 0.3 / 0.1 do
  not lose their final sample.
- `SweepPoint.elapsed_s` is measured from acquisition start, after reset,
  configuration, output enable, and the initial constant source command. It is
  recorded after readback completes; the wall-clock `timestamp` is recorded at
  the same post-readback point.
- `minimum_allowed_interval_seconds()` is the canonical physical/configuration
  bound (NPLC aperture plus configured delay). `minimum_interval_seconds()` and
  `estimate_point_seconds()` retain serial/readback estimates for ETA and user
  information only; UI Start validation no longer applies that estimate.
- Fixed-range runtime state avoids per-point `:SENS:CURR:RANG:AUTO?` /
  `:SENS:CURR:RANG?` queries, including when an operator changes Auto to Fixed
  during a run. Explicit range actions still perform the required refresh and
  settle/discard path.
- The 2400 serial driver now sends `:SOUR:DEL:AUTO OFF` and `:SOUR:DEL 0`.
  `SweepRunner` remains the single owner of `SweepConfig.delay_s`, preventing
  the device source delay and software delay from being applied twice.
- Real Keithley throughput and instrument-side behavior remain a hardware gate;
  no specific RS-232 sample rate is promised by the simulator tests.

## 2026-09-09 Constant Time duration-row UI state

- In Constant Time mode, `constant_until_stop=True` disables both widgets in
  `duration_row`: the Duration label and its entry. The value remains stored
  and becomes editable again when Until Stop is turned off.
- The state is reapplied after dynamic sweep controls are rebuilt and after
  global sweep-field state changes (connect/disconnect or run-state changes),
  so the Until Stop semantic is not overwritten by the general editable-state
  pass. Duration validation and continuous acquisition backend semantics are
  unchanged.

## 2026-09-09 Map Reconstruction UI state remediation

- Fresh single-v2 loads now reset timing anchors to trace-relative defaults:
  Row A/B at 20%/70%, Point A at 5%, and a positive point gap based on map
  width. Existing anchors can still be clamped without reset via the optional
  inspector argument.
- Processing errors clear only the processed map and Distribution tab. The
  authoritative raw reconstruction, Samples / pixel counts, timing QC, trace
  guides, and raw export remain available; true reconstruction invalidation
  still clears all derived views.
- Processing-unit labels now distinguish the raw baseline unit, the
  normalization-reference unit, and the processed/color unit. Custom
  references are unitless while raw/absolute/negate references retain their
  physical display unit. Point period is labeled in seconds.
- Added a read-only synthetic single-v2 `load_file()` regression and a Qt UI
  regression for processing failure/recovery, sample-count preservation, and
  custom/reference labels. No private data was used or committed.
- Validation on this head: 611 tests collected, 610 passed and 1 expected
  conditional skip; combined coverage 95.56%; compileall, Ruff, and per-file
  Black checks passed. The changed inspector module passes mypy; the existing
  repository-wide mypy run still reports unrelated test typing errors.
- Optional GUI dependencies were installed with `pip install -e ".[map]"`.
  Offscreen launch without a CSV and a synthetic read-only load probe passed;
  native desktop drag/pan/wheel/resize visuals remain operator follow-ups in
  this headless session.

## Keithley front-panel range popup visual polish note

The Keithley-style front-panel popup is in `src/keith_ivt/ui/status_bar.py`. The current-range area now intentionally uses custom `tk.Frame`/`tk.Label` card blocks instead of a native `ttk.LabelFrame`, because the native layout clipped controls under Windows scaling. Keep the mock-style hierarchy: large black instrument readout, left metadata column, right current-range card with summary cells and one aligned control row.

Regression command:
`PYTHONPATH=src python -m pytest tests/test_current_range_control.py -q`

## 2026-05-28 Keithley current range front-panel control

- Follow-up UI polish: the popup range panel should remain a compact two-column layout with Mode / Actual range / Last change summary cells. Avoid returning to long single-line labels or narrow buttons that clip at Windows default scaling.
- `src/keith_ivt/core/current_range.py` owns current-range display formatting, supported range labels, thread-safe UI-to-runner actions, and range state snapshots.
- `src/keith_ivt/ui/status_bar.py` now extends the Keithley-style popup with current autorange, actual/fixed range, lock-current, settle-delay, and discard-count controls. The bottom status readout includes `Irange Auto/...` or `Irange Fixed/...`.
- `src/keith_ivt/core/sweep_runner.py` applies queued range actions in the worker thread and discards configured readings after manual or detected actual-range changes before points enter live traces or saved results.
- `SimulatedKeithley.force_autorange_current_range_on_read(read_index, range_A)` is the deterministic simulator hook for tests; keep normal simulator autorange behavior non-random.
- Regression command: `.\.venv\Scripts\python.exe -m pytest tests\test_current_range_control.py tests\test_mock_visa_command_sequence.py tests\test_simulator_behavior.py -q -p no:cacheprovider`.

## 2026-05-18 axis-range popup hotfix

- `ui/plot_controls.py` no longer opens the axis range editor directly from the Tk popup menu command. `Set X range...` and `Set Y range...` now call `_schedule_axis_range_dialog()`, which returns immediately and opens the editor after 250 ms so the native menu can unpost naturally.
- Removed the previous focus/menu hacks (`focus_force`, root `update()`, explicit menu destroy/unpost sequences). They kept the ghost menu visible in Windows packaged builds and collapsed the hover dock.
- Replaced the built-in modal string prompt with a small custom non-modal `Toplevel` editor using `ttk.Entry`, OK, Cancel, Return, and Escape. This avoids the `wait_visibility` TclError path from `tkinter.simpledialog`.
- `diagnostics/runtime_logging.py` now tolerates `sys.stdout`/`sys.stderr` being `None` and suppresses secondary logging failures while reporting Tk callback exceptions.
- Regression command: `set PYTHONPATH=src && python -m pytest tests\test_axis_dialog_runtime_regression.py tests\test_plot_connection_regression.py -q`.

## 2026-05-17 release prep

- Prepared simple `1.0b1` / `1.0 beta 1` beta version metadata.
- Updated `src/keith_ivt/version.py`, `pyproject.toml`, README, changelog, release checklist, docs index, and current beta release notes.
- Kept build validation as the next step after this version/release-notes commit.
- Hardware bench coverage remains post-release follow-up; simulator/source validation and manual UI smoke checks are the beta release gate.

## 2026-05-17 export-selected and settings factory restore
- Fixed trace context-menu `Export selected...` so a multi-row Treeview selection exports all selected traces into one metadata-preserving combined CSV; single selection still exports one normal CSV.
- Added a `Restore factory settings` button to the Default Settings dialog. The button resets dialog fields to built-in `AppSettings()` defaults and checks those fields; values are not persisted until `Save Selected` is clicked.
- Added source-contract tests for multi-selected trace export and the factory-settings restore button.

## 2026-05-17 duplicate title/log/About cleanup
- Removed duplicate in-panel tab titles; the fixed top-bar title is now the only visible page title.
- Added/kept tab hover summaries on the fixed top-bar title instead of duplicate panel headings.
- Removed the `Named presets` LabelFrame title and the Preset/Restore inline info rows/buttons.
- Moved the About release-stage text into the body copy instead of showing a separate status line.
- Restored Log panel layout by avoiding mixed pack/grid title widgets inside grid-based pages.
- Added regression coverage for duplicate-title and inline-info cleanup.

## 2026-05-17 follow-up UI/status/plot patch
- Removed preset/restore inline info rows and pushed the explanation back into hover tips via the page title + in-panel section title hover.
- Moved points/estimate into the Controls heading (`Controls (xx pts, yy sec)` / continuous variant).
- Added compact live status readout (`Vsrc/Isrc`, `Imeas/Vmeas`, `Cmpl`) with signed engineering-format values and a double-clickable Keithley-style front-panel popup.
- Added fullscreen plot `Save screenshot...` button.
- Tight-layout warning path replaced with constrained-layout/safe fallback.
- Plot X/Y swap now targets only the current plot view from the context menu.
- Current-source default linear/log IV plots now use current on the X axis.
- Range Auto buttons stay editable in idle/stopped/completed states (not only literal `idle`).
- Trace visibility column now shows ☑/☐ and completed sweeps auto-select the newest trace.
- Added source-text + logic contract tests for controls header, front-panel hooks, current-source X-axis default, and plot swap/fullscreen save hooks.

# Agent Handoff

## 2026-09-10 Map three-stage workflow

The standalone Map Reconstruction app now has explicit Preparation,
Reconstruction, and Analysis navigation pages. Keep the scientific dependency
graph one-way: imported `TimeSeriesData` is immutable in practice, the
Qt-free `map_reconstruction.preparation` pipeline returns read-only
`PreparedSignal` arrays, reconstruction consumes an adapter trace, and
post-map processing/display remain separate. Active preparation configuration
is serialized in project schema v3; v1/v2 projects intentionally restore
identity preparation for parity. Do not move dark correction into the map
processing stage or change the reconstruction formulas when extending this
workflow.

This file is the machine-facing handoff note for future coding agents. Keep `README.md` human-facing and put implementation-specific context here.

## Current architecture anchors

- `src/keith_ivt/ui/simple_app.py` is the composition root and should stay small; keep feature logic in focused mixins/modules.
- `src/keith_ivt/ui/update_controller.py` owns non-blocking GitHub release metadata checks and manual-upgrade status messages.
- `src/keith_ivt/ui/hardware_controller.py` owns connection/disconnection and instrument profile rendering.
- `src/keith_ivt/ui/sweep_controller.py` owns Start/Pause/Stop worker orchestration and queue draining.
- `src/keith_ivt/ui/app_state.py` is the authoritative run/connection state gate.
- `src/keith_ivt/core/sweep_runner.py` is the legacy sweep execution boundary used by the Tk UI.
- `src/keith_ivt/services/measurement_service.py` is the newer driver-level execution service for future hardware backends.

## Recent safety hardening

Pause/Stop responsiveness depends on the bounded UI queue in `ui/sweep_controller.py`; do not restore unbounded queue draining or per-point redraws in the point branch.

Stop/Abort safety now has explicit sweep-runner tests: an operator stop must attempt `output_off()` even when `output_off_after_run=False`. Normal completion still respects `output_off_after_run=False`, while measurement exceptions preserve the original error if the safety output-off command also fails.

## Trace/export consistency contract

`DatasetStore` remains the trace registry; `TracePanelMixin._refresh_trace_list()` is responsible for cleaning stale tree selections. If traces are deleted/import-replaced/cleared, `_selected_trace_id` must either point at an existing trace or be `None` for the empty state.

Export semantics are intentional: **Export all traces** includes hidden traces; **Export visible** filters by the trace `visible` flag. Trace rename must be applied to exported `SweepResult.config.device_name` via `_result_with_trace_name()`.

Status-bar connection lamps are Canvas-rendered UI-scale-aware indicators, not emoji labels. The simulator/debug state is a Canvas gear. Do not reintroduce emoji glyphs for these indicators because Windows/Tk can render them through monochrome fallback fonts.

Start gating in `ui/sweep_controller.py` must stay aligned with `AppState.can_start_sweep()`: ready states are `idle`, `stopped`, `completed`, and `aborted`. Do not regress to an `idle`-only guard, or repeated simulator starts will appear unresponsive.


## Fault-injection and error-path tests

`keith_ivt.instrument.simulator.SimulatorFaultProfile` is for deterministic test faults only. Keep normal debug-simulator behavior inert by default. Current fault coverage intentionally exercises connect failures, read failures, non-finite readbacks, and output-off failures without real hardware. `SweepRunner` and `MeasurementService` must reject NaN/Inf readbacks before data reaches `DatasetStore` or CSV export paths.


## Plot interaction note

Main plot interactivity lives in `src/keith_ivt/ui/plot_panel.py` and `src/keith_ivt/ui/plot_controls.py`. The primary canvas uses Matplotlib event hooks for `button_press_event`, `button_release_event`, and `motion_notify_event`. Left-button drag pans the axis under the pointer, while motion without an active drag performs nearest-visible-point hit testing and shows an X/Y annotation when the pointer is close enough to a plotted point. Keep this path non-modal and avoid forcing Tk focus; the context-menu axis-range editor intentionally stays scheduled after the popup command returns to avoid Windows/Tk ghost menus and hover-dock collapse.

## Known limitations

- The operator confirmed successful real-device measurement and the short
  hardware release gate with the final packaged `1.1b4` executable.
- `keith_ivt` remains the implementation/legacy import namespace; `happymeasure` is the public package namespace.
- The `1.1b4` Python 3.12 portable build passed; package contents and packaged
  window startup/shutdown were verified.

## Current UI/data hardening note

Status-bar connection indicators are Canvas-rendered, not emoji labels. The simulator/debug state is shown as a small Canvas gear. These icons follow UI scale but not the selected font family. Do not reintroduce red/green/devil emoji for these indicators because Windows/Tk can render them through monochrome fallback fonts.


## P1 release-hardening contracts

Configuration compatibility is now part of the release contract. `data/settings.py` intentionally sanitizes the legacy flat settings JSON instead of failing hard: corrupt/non-dict files fall back to defaults, string booleans are parsed explicitly, invalid numbers are clamped/defaulted, old theme names are migrated, and unknown fields are ignored. Keep this path tolerant until a formal config schema migration replaces it.

Sweep presets use the same sanitizer through `data/presets.py`. Do not let partial or legacy presets crash startup; missing fields should fall back to defaults and unknown fields should be ignored.

Trace metadata is documented in `docs/TRACE_SCHEMA.md`; if exporter/importer fields change, update that document and `tests/test_trace_schema_contract.py` together.

Manual release validation is documented in `docs/MANUAL_SMOKE_TESTS.md`. Hardware preflight behavior is documented in `docs/HARDWARE_PREFLIGHT.md`. The CLI should produce readable PASS/FAIL output for ordinary serial/resource failures.

## Documentation ownership note

`docs/README.md` is now the documentation index. `docs/RELEASE_CHECKLIST.md` is the release-prep owner document and should be updated whenever the release workflow, validation sequence, build steps, asset naming, or post-release verification changes. `docs/DOCS_AUDIT.md` records the latest documentation audit and future cleanup candidates.

Avoid duplicating long procedures across docs. Update the owner document and link to it from README, handoff, or release notes as needed.

## Legacy test-contract synchronization note

Legacy source-contract tests have been updated to match the current Canvas status-icon design, `_normalize_theme()` settings sanitizer, and `_should_stop` interruptible-sleep wrapper. Do not reintroduce assertions for `ConnGreen.TLabel`, `ConnRed.TLabel`, or the old devil emoji status indicator; those are intentionally obsolete.

Current full-test status after the `1.1b4` release-prep sync: 467 tests pass
with 1 expected skip. The earlier build/packaging contract failures are
resolved.

External audit quick-fix status: RunState alias clarity, redundant coverage omit cleanup, and the staged namespace migration plan have been addressed. `RunState.RUNNING` is intentionally a deprecated alias for canonical `RunState.SWEEPING`; do not split it into a new runtime state without updating AppState transitions and UI status rendering. Strict mypy settings and coverage-threshold changes remain deferred engineering-policy decisions, not next-release blockers.


## Beta UI polish note

The left navigation rail uses user-facing hover summaries for each tab; keep these concise and task-oriented. The About page must always show a non-empty update status, even before/without a successful update check. Dark-theme About labels should use About-specific card-background styles rather than native/default label backgrounds.

## Front-panel popup automation note

The Keithley-style front-panel popup is implemented in `src/keith_ivt/ui/status_bar.py`. The user can still open it manually by double-clicking the status readout, but `show_front_panel_on_start` now controls automatic behavior. `ui/sweep_controller.py` opens it when a sweep enters `running` and closes only the auto-opened popup on Stop, completion, or error. Keep the `_front_panel_auto_opened` flag so a future manual-only popup path is not accidentally closed by unrelated state refreshes.

Regression command: `set PYTHONPATH=src && python -m pytest tests\test_front_panel_auto_popup_regression.py -q`.


### 2026-05-18 follow-up hotfix
- Fixed Settings save feedback so `Auto-open Front Panel on Start = No` updates the live `BooleanVar` immediately, not only after restart.
- Changed factory default debug/simulator mode to disabled (`default_debug = false`) in legacy and v2 settings models plus `config/settings.json`.
- Regression: `python -m pytest tests/test_front_panel_auto_popup_regression.py -q`.

## Sweep delay / timing-estimate note

The Sweep panel now has a common `Delay (s)` field immediately after `NPLC`. It is stored as `SweepConfig.delay_s` and persisted as `default_delay_s`. Default is `0.0` so existing workflows do not slow down unless the user explicitly sets a delay.

Timing estimate owner functions are in `src/keith_ivt/models.py`:
- `minimum_allowed_interval_seconds(nplc, line_frequency_hz=50.0, delay_s=0.0)`
- `minimum_interval_seconds(nplc, line_frequency_hz=50.0, overhead_s=None, delay_s=0.0, baud_rate=9600)`
- `estimate_point_seconds(nplc, mode="STEP", interval_s=None, delay_s=0.0)`

The estimate intentionally models the Keithley 2400-class aperture as `NPLC / line_frequency`, then adds user delay and serial/readback overhead for ETA/user information. Validation uses `minimum_allowed_interval_seconds()` instead and never rejects a cadence solely because of estimated PC/serial transfer time.

Hardware command intent is covered by `drivers/command_plan.py` and `instrument/serial_2400.py`. Both disable the 2400 automatic/programmed source delay (`:SOUR:DEL:AUTO OFF`, `:SOUR:DEL 0`); `SweepRunner` sleeps `delay_s` after setting the source and before `:READ?` so debug/simulator and serial behavior apply the configured delay once.

Regression command:
`set PYTHONPATH=src && python -m pytest tests\test_delay_timing_regression.py tests\test_core_coverage_gaps.py tests\test_settings_v2.py tests\test_data_import_export_store.py tests\test_mock_visa_command_sequence.py tests\test_pre_hardware_safety.py tests\test_services_drivers_more.py -q`
