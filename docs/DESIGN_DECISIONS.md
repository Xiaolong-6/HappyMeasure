# Design decisions — HappyMeasure

## 0.4.0-alpha.7: split by runtime responsibility, not by visual page only

The application was decomposed into small mixin modules because the alpha UI still needs fast iteration without introducing a full framework. This keeps Tkinter simple while removing most logic from `simple_app.py`.

## State migration strategy

`ui/app_state.py` is the target single source of truth for run and connection state. In 0.4.0-alpha.7 it is synchronized with the existing fields (`_run_state`, `_connected`, `_stop_requested`, `_paused`) rather than replacing them outright. This avoids a high-risk one-shot migration after recent plot/traces regressions.

## Plot/traces safety contract

The Matplotlib plot pane must never be removed from the splitter. Trace pane visibility can change during live measurement, but plot must remain stable. This prevents the blue blank-pane regression seen in 0.3.0-alpha.4/alpha.5.

## Package size policy

The project remains source-only. Do not commit virtual environments, `__pycache__`, `.pytest_cache`, generated coverage HTML, large screenshots, or vendor assets.


## 0.4.0-alpha.7 interaction/import/status/theme update

This build preserves the 0.4.0 decomposition and adds targeted UI/workflow fixes: plot context-menu fallback binding, import-overlap prompting, detected COM-port dropdown, checked-trace export, last-save status-bar cell, debug emoji indicator, High contrast theme, and interruptible simulator sleep for Stop responsiveness.


## 0.4.0-alpha.7 theme/menu note

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
