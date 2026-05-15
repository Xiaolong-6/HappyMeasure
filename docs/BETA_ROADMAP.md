# Beta hardening roadmap — HappyMeasure

This roadmap converts the external alpha review into a staged implementation plan for moving HappyMeasure from simulator-first alpha to beta quality.

## Current 0.3.x scope

0.3.x remains an offline-alpha line. Its goal is not production hardware control; it is to stabilise UI layout, simulator behaviour, test coverage, and module boundaries before the hardware-integration branch.

## Accepted recommendations

The 0.3.0-alpha.6 iteration accepted the following low-risk recommendations immediately:

- Add a tested `ui/app_state.py` foundation with explicit `RunState` and `ConnectionState` enums.
- Add bounded thread-safe buffer primitives in `utils/thread_safe.py` for later queue/live-plot migration.
- Add unit tests for the state model and buffer primitives.
- Keep the current UI state variables in place for this release to avoid a high-risk wholesale migration.


## 0.5.0-alpha.1 implementation status

Implemented from the external review:

- `simple_app.py` reduced from roughly 1440 lines to roughly 300 lines and converted into a composition root.
- Remaining responsibilities split into hardware controller, sweep controller, sweep config, data actions, settings/preset actions, scaffold, preset/restore panel builder, and widget helper modules.
- Run/connection transitions synchronized into `AppState` without risky full removal of legacy fields.
- Live measurement path now also populates a bounded thread-safe XY buffer.
- Architecture, design decision, handoff, and new-thread docs updated for external review.

Still deferred:

- Real serial retry/backoff policy.
- Full AppState-only migration.
- Real Windows GUI smoke and real Keithley dry-run validation.
- Formal CI coverage gate above 80% for full production/hardware scope. Current alpha-supported scope reaches about 80% with the configured coverage omit list.

## Deferred recommendations

The following recommendations are valid but intentionally deferred:

- Full migration from `_running`, `_paused`, `_stop_requested`, `_run_state`, and `_connected` into `AppState`.
- Structured logging and serial retry policy.
- CI coverage target above 80%.
- Hardware retry/recovery around real serial devices.

These require a dedicated refactor window and real Windows/Tk validation.

## Proposed staged plan

### 0.3.x alpha stabilisation

- Fix UI regressions immediately.
- Keep package source-only and small.
- Grow tests around core logic, simulator behaviour, export/import naming, and UI contracts.
- Continue module extraction from `simple_app.py` without changing runtime behaviour.

### 0.4.x alpha/beta hardware integration

- Migrate run/connection state into `AppState`.
- Add structured runtime logging and serial retry/backoff.
- Add Keithley 2400/2450 real-hardware dry-run checklist.
- Add compliance/range/terminal failure-path tests where simulator coverage is possible.

### Beta gate

HappyMeasure can be called beta only after:

- GUI smoke test passes on Windows desktop.
- Simulator workflows pass step/time/adaptive/current-source/voltage-source tests.
- Stop/Abort and output-off paths are verified.
- Data import/export/restore paths have unit tests.
- Known hardware limitations are documented in handoff notes.


## 0.5.0-alpha.1 interaction/import/status/theme update

This build preserves the 0.4.0 decomposition and adds targeted UI/workflow fixes: plot context-menu fallback binding, import-overlap prompting, detected COM-port dropdown, checked-trace export, last-save status-bar cell, debug emoji indicator, High contrast theme, and interruptible simulator sleep for Stop responsiveness.


## 0.5.0-alpha.1 theme/menu note

This build fixes the trace-column gear menu import regression and changes the UI baseline: `High contrast` is now the default theme, `Light` is no longer selectable, and `Dark` uses integrated dark backgrounds with visible borders for controls. Keep plot/traces display contracts unchanged when editing theme code.

## 0.5.0-alpha.4 UI/simulator refinement note

- Adaptive sweep rows are compact table rows, not tall per-segment cards.
- Sweep and Settings boolean controls are colored toggle buttons rather than native checkbox widgets.
- Source/measure range rows use `label + entry + Auto` in one row; Auto disables the entry and remains clickable only when the sweep panel is editable.
- Current-source diode debug simulation now inverts the voltage-source diode I(V) curve, so the named debug model behaves consistently across source modes.
- Mouse-wheel zoom targets only the subplot under the pointer; Ctrl still zooms X, default/Shift zooms Y.
- Log page height is refreshed when the content canvas resizes, and preset action buttons expand with the pane.


## 0.5.0-alpha.4 theme/adaptive polish note

- Theme names are now `Light`, `Dark`, and `Debug`. `Light` is the default clean theme; `Debug` is the renamed high-border layout-inspection theme. Existing saved `High contrast` migrates to `Debug`.
- Common sweep safety controls are intentionally above dynamic sweep controls. Do not move Compliance/NPLC/Source range/Measure range below the Adaptive table, because that hides range settings in narrow panes.
- Splitters use the same soft themed paned-window background for the main left/right pane and the plot/trace pane.


## 0.5.0-alpha.4 visual responsiveness note

- Navigation is now a push-side rail, not an overlay drawer. It reserves column 0 and the workspace uses column 1. It no longer auto-hides on outside clicks.
- The Light theme is the default modern card-style theme; Debug keeps strong borders for layout inspection.
- Sweep content is scrollable from child widgets at large UI scales, including Adaptive mode rows.
- Operator and status bars follow the workspace column so the side rail does not cover them.
