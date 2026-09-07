
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
- Candidate artifact: `HappyMeasure-1.1b5-windows-portable.zip`, 44,701,070
  bytes, SHA-256
  `247006dd5ba05ff421fadee7e4652ea91ab5a6cd909256f48dfc489e202431ce`.

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
- `minimum_interval_seconds(nplc, line_frequency_hz=50.0, overhead_s=0.03, delay_s=0.0)`
- `estimate_point_seconds(nplc, mode="STEP", interval_s=None, delay_s=0.0)`

The estimate intentionally models the Keithley 2400-class aperture as `NPLC / line_frequency`, then adds user delay and serial/readback overhead. If hardware validation shows a consistent offset for a specific connection mode, tune `overhead_s` or add an instrument-profile-specific timing constant rather than hiding it in UI code.

Hardware command intent is covered by `drivers/command_plan.py` and `instrument/serial_2400.py`, both sending `:SOUR:DEL <delay_s>`. `SweepRunner` also sleeps `delay_s` after setting the source and before `:READ?` so debug/simulator and legacy serial behavior remain aligned.

Regression command:
`set PYTHONPATH=src && python -m pytest tests\test_delay_timing_regression.py tests\test_core_coverage_gaps.py tests\test_settings_v2.py tests\test_data_import_export_store.py tests\test_mock_visa_command_sequence.py tests\test_pre_hardware_safety.py tests\test_services_drivers_more.py -q`
