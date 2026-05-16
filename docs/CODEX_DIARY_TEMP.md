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
- Replaced status-bar emoji lamps with fixed-size Canvas-rendered connection/debug indicators independent of the user-selected UI font family/size.

### Simulator start-state regression fix

- Fixed a Start-button regression where the worker was only allowed to start from the strict `idle` state even though the centralized AppState and button-state logic treat `stopped`, `completed`, and `aborted` as ready states.
- Added a regression check so simulator runs can be started again after a completed/stopped/aborted run without restarting the app.
### Trace/export, simulator start, and Canvas status icons

- Hardened trace selection/export consistency and preserved renamed trace names in export paths.
- Fixed simulator Start gating so ready states such as stopped/completed/aborted can start a new sweep.
- Replaced emoji status lamps with fixed-size Canvas indicators and a Canvas gear for simulator/debug mode to avoid Windows/Tk emoji fallback rendering.

### Fault-injection simulator and error-path hardening

- Added deterministic `SimulatorFaultProfile` hooks to the debug simulator for connect, reset/configure, output-on/off, set-source, read, NaN, and Inf fault paths used by tests.
- Hardened `SweepRunner` and `MeasurementService` to reject non-finite source/measurement readbacks before they enter datasets.
- Confirmed error paths still attempt safety `output_off()` and preserve the original measurement/readback error when output-off also fails.
- Aligned `AppState.can_start_sweep()` with UI Start gating so aborted-but-connected runs are restartable.
- Added `tests/test_fault_injection_safety.py` covering simulator connect/read/non-finite faults, driver-service non-finite faults, output-off error preservation, and aborted-state restart gating.

### Simple app composition-root size control

- Extracted the non-blocking GitHub release reminder UI wiring from `ui/simple_app.py` into `ui/update_controller.py`.
- Wired `UpdateControllerMixin` through `AppWorkflowMixin` so `SimpleKeithIVtApp` keeps the same public inheritance surface.
- Reduced `ui/simple_app.py` from 381 lines / 15 function definitions to 290 lines / 8 function definitions, satisfying the engineering baseline contract.
- Updated update-check and engineering-baseline tests to assert the new composition boundary.
