# Error Recovery Contract

This document describes current recovery behavior. Historical implementation milestones belong in Git history and release notes.

## Core rules

- Measurement errors must never bypass best-effort `output_off()` cleanup.
- A recoverable sweep error must leave the desktop UI reusable after cleanup instead of requiring an application restart.
- Worker exceptions are reported back to the UI thread; worker code must not mutate Tk widgets directly.
- Serial retry is bounded. Repeated communication failure must surface as an error rather than retry forever.
- Recovery must not fabricate measurement values or silently mark an incomplete/aborted sweep as normally completed.
- If output-off cannot be confirmed in software, the operator must verify the physical instrument state before reconnecting a DUT.

## Serial and shutdown protection

`SerialRetryPolicy` provides bounded retry/backoff for selected serial operations. `OutputOffGuard` and instrument/context cleanup provide best-effort output-off protection without masking the original exception.

Hardware preflight and built-in Hardware Diagnostics are deliberately narrower than a sweep: they establish communication/output-off safety and do not enable source output or run a measurement.

## UI recovery states

Normal completion, Stop and Abort/Error are distinct outcomes. After cleanup, the application must permit another run from the documented ready states without stale stop/pause flags.

See `STATE_MACHINE.md` for run/connection state semantics and `HARDWARE_VALIDATION_PROTOCOL.md` for the release hardware gate.

## Operator recovery after a real-hardware error

1. Confirm the instrument output is physically OFF.
2. Save `logs/error.log`, `logs/console_last_run.log`, and any relevant CSV/diagnostic archive.
3. Disconnect the DUT if the fault could involve compliance, wiring, range, or communication state.
4. Run the output-off hardware preflight again.
5. Reproduce first with the simulator or a safe dummy load and conservative compliance.
6. Return to a real DUT only after the failure mode is understood and the output-off path has been rechecked.

## Known boundary

HappyMeasure does not claim a firmware-specific recovery matrix for every Keithley model/firmware combination. Automated tests verify software contracts; staged real-hardware checks remain required for release claims.
