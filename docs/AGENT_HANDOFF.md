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

## Known limitations

- Real hardware validation is still required before external release.
- `keith_ivt` remains the implementation/legacy import namespace; `happymeasure` is the public package namespace.
- Build validation is intentionally deferred until the version-number/release-prep step.

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

Current full-test status after this sync: non-build tests pass. Two remaining full-suite failures are build/packaging contracts and should be resolved in the version-bump/release-build phase unless the user explicitly asks to address packaging earlier.

External audit quick-fix status: RunState alias clarity, redundant coverage omit cleanup, and the staged namespace migration plan have been addressed. `RunState.RUNNING` is intentionally a deprecated alias for canonical `RunState.SWEEPING`; do not split it into a new runtime state without updating AppState transitions and UI status rendering. Strict mypy settings and coverage-threshold changes remain deferred engineering-policy decisions, not next-release blockers.


## Beta UI polish note

The left navigation rail uses user-facing hover summaries for each tab; keep these concise and task-oriented. The About page must always show a non-empty update status, even before/without a successful update check. Dark-theme About labels should use About-specific card-background styles rather than native/default label backgrounds.
