# Current architecture — HappyMeasure 0.7a1

HappyMeasure remains a simulator-first alpha, but the application shell is now split enough for external review without reading a monolithic UI file.

## Runtime layers

```text
src/keith_ivt/
  models.py                    SweepConfig, SweepPoint, SweepResult
  core/sweep_runner.py          Hardware-independent sweep runner
  instrument/                   SourceMeter protocol, simulator, serial 2400 backend
  data/                         CSV import/export, autosave backup, presets, settings
  utils/thread_safe.py          Bounded thread-safe live-data buffers
  ui/app_state.py               Central AppState skeleton and run/connection enums
  ui/simple_app.py              Thin Tk application composition root (~300 lines)
  ui/ui_scaffold.py             Content header/canvas scaffold
  ui/navigation.py              Left drawer navigation and animation
  ui/status_bar.py              Bottom status bar / connection light
  ui/operator_bar.py            Bottom operator controls
  ui/panels.py                  Hardware/Sweep/Settings/Log/About panel builders
  ui/preset_restore_panel.py    Preset and Restore panel builders
  ui/sweep_config.py            UI variable binding, adaptive table, SweepConfig construction
  ui/hardware_controller.py     Capability profile, connection state, field locking
  ui/sweep_controller.py        Start/pause/stop/queue/completion/error paths
  ui/plot_panel.py              Matplotlib canvas, vertical plot/trace splitter
  ui/plot_controls.py           Plot right-click/zoom/unit/range actions
  ui/trace_panel.py             Trace table rendering and data export/import actions
  ui/trace_controls.py          Trace context menu, rename/color/delete/visibility
  ui/data_actions.py            Backup/import/restore/file-opening helpers
  ui/settings_preset_actions.py Settings review/save and preset application
  ui/theme.py                   Light/dark Nordic ttk styles
```

## Guardrails

- `simple_app.py` is the composition root only. New UI logic should go into the relevant mixin module.
- Connection state is shown only in the bottom status bar, never in the page header.
- Plot and Traces live in a vertical `ttk.PanedWindow`; the plot pane must remain present even if every view is disabled.
- During a run, the trace pane is temporarily hidden and the plot shows live data only. After completion, traces are restored.
- `AppState` is now instantiated by the UI and synchronized with run/connection transitions, but legacy fields are retained for compatibility during alpha.

## Beta-readiness gap

0.7a1 keeps the 0.6 architectural-refactoring baseline, preserves the live-plot/cache, simulator, mixin, and logging fixes, and adds pre-hardware safety/mock-command validation. Remaining beta work is real Windows/Tk smoke validation, structured bench validation, and wider hardware-integration tests.


## 0.5.0-alpha.1 patch note

Alpha.2 preserves the alpha.1 module decomposition and fixes the Start/config regression caused by missing model imports in the composition root. It also tightens the visual contract for the plot toolbar, scrollbars, status cells, and operator bar.


## 0.5.0-alpha.1 interaction/import/status/theme update

This build preserves the 0.4.0 decomposition and adds targeted UI/workflow fixes: plot context-menu fallback binding, import-overlap prompting, detected COM-port dropdown, checked-trace export, last-save status-bar cell, debug emoji indicator, High contrast theme, and interruptible simulator sleep for Stop responsiveness.


## 0.5.0-alpha.1 theme/menu note

This build fixes the trace-column gear menu import regression and changes the UI baseline: `High contrast` is now the default theme, `Light` is no longer selectable, and `Dark` uses integrated dark backgrounds with visible borders for controls. Keep plot/traces display contracts unchanged when editing theme code.


## 0.5.0-alpha.1 queue/rendering contract

Worker threads may produce points faster than the UI can redraw. The UI must process worker queue messages in bounded batches and redraw live plots once per tick, not once per point. This is required for responsive Pause/Stop in debug simulator mode.

## Historical UI/simulator refinement note

- Adaptive sweep rows are compact table rows, not tall per-segment cards.
- Sweep and Settings boolean controls are colored toggle buttons rather than native checkbox widgets.
- Source/measure range rows use `label + entry + Auto` in one row; Auto disables the entry and remains clickable only when the sweep panel is editable.
- Current-source diode debug simulation now inverts the voltage-source diode I(V) curve, so the named debug model behaves consistently across source modes.
- Mouse-wheel zoom targets only the subplot under the pointer; Ctrl still zooms X, default/Shift zooms Y.
- Log page height is refreshed when the content canvas resizes, and preset action buttons expand with the pane.


## Historical theme/adaptive polish note

- Theme names are now `Light`, `Dark`, and `Debug`. `Light` is the default clean theme; `Debug` is the renamed high-border layout-inspection theme. Existing saved `High contrast` migrates to `Debug`.
- Common sweep safety controls are intentionally above dynamic sweep controls. Do not move Compliance/NPLC/Source range/Measure range below the Adaptive table, because that hides range settings in narrow panes.
- Splitters use the same soft themed paned-window background for the main left/right pane and the plot/trace pane.


## Historical visual responsiveness note

- Navigation is now a push-side rail, not an overlay drawer. It reserves column 0 and the workspace uses column 1. It no longer auto-hides on outside clicks.
- The Light theme is the default modern card-style theme; Debug keeps strong borders for layout inspection.
- Sweep content is scrollable from child widgets at large UI scales, including Adaptive mode rows.
- Operator and status bars follow the workspace column so the side rail does not cover them.
