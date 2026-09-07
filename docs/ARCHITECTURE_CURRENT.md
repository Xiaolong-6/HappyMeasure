# Current architecture — HappyMeasure 1.1b5

HappyMeasure is a simulator-first beta, with the application shell split into focused UI modules for external review.

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
- `AppState` is now instantiated by the UI and synchronized with run/connection transitions.

## Design decisions

- **Split by runtime responsibility**: The application was decomposed into small mixin modules because the UI needs fast iteration without introducing a full framework. This keeps Tkinter simple while removing most logic from `simple_app.py`.
- **State migration strategy**: `ui/app_state.py` is the target single source of truth for run and connection state. It is synchronized with legacy fields rather than replacing them outright to avoid high-risk one-shot migration.
- **Plot/traces safety contract**: The Matplotlib plot pane must never be removed from the splitter. Trace pane visibility can change during live measurement, but plot must remain stable.
- **Package size policy**: The project remains source-only. Do not commit virtual environments, `__pycache__`, `.pytest_cache`, generated coverage HTML, large screenshots, or vendor assets.

## Queue/rendering contract

Worker threads may produce points faster than the UI can redraw. The UI must process worker queue messages in bounded batches and redraw live plots once per tick, not once per point. This is required for responsive Pause/Stop in debug simulator mode.

## Historical UI/simulator refinement note

- Adaptive sweeps use one multiline editor with a `start, stop, step` segment
  on each line. The core parser, not Tk widgets, owns validation and value generation.
- Sweep and Settings boolean controls are colored toggle buttons rather than native checkbox widgets.
- Source/measure range rows use `label + entry + Auto` in one row; Auto disables the entry and remains clickable only when the sweep panel is editable.
- Current-source diode debug simulation now inverts the voltage-source diode I(V) curve, so the named debug model behaves consistently across source modes.
- Mouse-wheel zoom targets only the subplot under the pointer; Ctrl still zooms X, default/Shift zooms Y.
- Log page height is refreshed when the content canvas resizes, and preset action buttons expand with the pane.


## Historical theme/adaptive polish note

- Theme names are now `Light`, `Dark`, and `Debug`. `Light` is the default clean theme; `Debug` is the renamed high-border layout-inspection theme. Existing saved `High contrast` migrates to `Debug`.
- Common sweep safety controls are intentionally above dynamic sweep controls. Do not move Compliance/NPLC/Source range/Measure range below the Adaptive editor, because that hides range settings in narrow panes.
- Splitters use the same soft themed paned-window background for the main left/right pane and the plot/trace pane.


## Historical visual responsiveness note

- Navigation is now a push-side rail, not an overlay drawer. It reserves column 0 and the workspace uses column 1. It no longer auto-hides on outside clicks.
- The Light theme is the default modern card-style theme; Debug keeps strong borders for layout inspection.
- Sweep content is scrollable from child widgets at large UI scales, including Adaptive mode rows.
- Operator and status bars follow the workspace column so the side rail does not cover them.
