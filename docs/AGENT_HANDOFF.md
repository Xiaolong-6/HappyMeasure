# Agent Handoff

This file is the machine-facing handoff note for future coding agents. Keep `README.md` human-facing and put implementation-specific context here.

## Current architecture anchors

- `src/keith_ivt/ui/simple_app.py` is the composition root and should stay small.
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

Status-bar connection lamps are Canvas-rendered fixed-size indicators, not emoji labels. The simulator/debug state is a Canvas gear. Do not reintroduce emoji glyphs for these indicators because Windows/Tk can render them through monochrome fallback fonts.

Start gating in `ui/sweep_controller.py` must stay aligned with `AppState.can_start_sweep()`: ready states are `idle`, `stopped`, `completed`, and `aborted`. Do not regress to an `idle`-only guard, or repeated simulator starts will appear unresponsive.


## Fault-injection and error-path tests

`keith_ivt.instrument.simulator.SimulatorFaultProfile` is for deterministic test faults only. Keep normal debug-simulator behavior inert by default. Current fault coverage intentionally exercises connect failures, read failures, non-finite readbacks, and output-off failures without real hardware. `SweepRunner` and `MeasurementService` must reject NaN/Inf readbacks before data reaches `DatasetStore` or CSV export paths.

## Known limitations

- Real hardware validation is still required before external release.
- `keith_ivt` remains the implementation/legacy import namespace; `happymeasure` is the public package namespace.
- Build validation is intentionally deferred until the version-number/release-prep step.

## Current UI/data hardening note

Status-bar connection indicators are Canvas-rendered, not emoji labels. The simulator/debug state is shown as a small Canvas gear. Do not reintroduce red/green/devil emoji for these indicators because Windows/Tk can render them through monochrome fallback fonts.

