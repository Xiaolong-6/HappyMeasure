# Codex Diary (Temporary)

This temporary diary records changes made during Codex-assisted turns so release notes can be prepared later.

## 2026-05-16

### Public package namespace migration

- Promoted runtime `PACKAGE_NAME` from the legacy `keith_ivt` namespace to the public `happymeasure` namespace.
- Added `src/happymeasure` command wrappers for `python -m happymeasure`, `python -m happymeasure.hardware_preflight`, and `python -m happymeasure.diagnostics`.
- Kept the existing `keith_ivt` implementation package and imports as a compatibility layer, so old imports and fallback launch paths continue to work.
- Updated Windows launchers, PyInstaller entry points, README/docs, and namespace tests to prefer `happymeasure` while preserving `keith_ivt` fallback behavior.

### Stop / Abort / Pause safety hardening

- Hardened `SweepRunner` so an operator stop attempts `output_off()` even when `output_off_after_run=False`.
- Preserved the existing normal-completion behavior: a successful full sweep still respects `output_off_after_run=False`.
- Added safe output-off error handling so a failed output-off command does not hide the original measurement exception.
- Applied the same output-off error-preservation pattern to the newer `MeasurementService` boundary.
- Added `tests/test_sweep_safety.py` covering operator stop, normal completion, measurement exception cleanup, and output-off failure context.
- Added/updated agent-facing handoff context for the safety contract.

### Trace/export consistency and status-light polish

- Hardened trace selection cleanup so deleting or externally removing the selected trace cannot leave `_selected_trace_id` pointing at a missing trace.
- Added regression tests for deleting the last trace, stale selected trace IDs, rename/export name preservation, and hidden-vs-visible export semantics.
- Documented that Export all includes hidden traces while Export visible filters to ticked traces.
- Fixed the status-bar connection lamp to use fixed-size color emoji rendering (`🔴`, `🟢`, `😈`) independent of the user-selected UI font family/size.

### Simulator start-state regression fix

- Fixed a Start-button regression where the worker was only allowed to start from the strict `idle` state even though the centralized AppState and button-state logic treat `stopped`, `completed`, and `aborted` as ready states.
- Added a regression check so simulator runs can be started again after a completed/stopped/aborted run without restarting the app.
