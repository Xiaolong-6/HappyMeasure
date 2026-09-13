# Error Recovery Contract

This document describes current recovery behavior. Historical implementation milestones belong in Git history and release notes.

## Core rules

- Measurement errors must never bypass output-off cleanup.
- A recoverable sweep error must leave the desktop UI reusable after cleanup instead of requiring an application restart.
- Worker exceptions are reported back to the UI thread; worker code must not mutate Tk widgets directly.
- Serial retry is bounded. Measurement `READ?` is not automatically replayed after a timeout because a replay could duplicate an acquisition and extend STOP latency.
- Recovery must not fabricate measurement values or silently mark an incomplete/aborted sweep as normally completed.
- If output-off cannot be confirmed in software, the operator must verify the physical instrument state before reconnecting a DUT.

## Serial and shutdown protection

The real Keithley serial driver treats `output_off()` as a safety-critical command: a failed write propagates as an error instead of being reported as success.

`SerialRetryPolicy` remains available for selected idempotent serial operations. `OutputOffGuard` is a secondary best-effort cleanup helper used where masking the original exception would be worse; it is **not** a substitute for verified hardware state.

The repository hardware preflight is stronger than a best-effort cleanup path: it sends `OUTPUT OFF`, queries `:OUTP?`, and requires the instrument to report an off state before returning a pass.

Hardware Diagnostics is similarly narrow: it is for communication/output-off verification and does not enable source output or run a measurement.

## STOP and application close

The desktop STOP control is cooperative. It sets the stop request and the runner exits at the next safe software point, then performs output-off cleanup. A serial transaction already in progress cannot be interrupted by that button.

If immediate physical output-off is required, use the instrument front-panel control.

Closing the main window during an active run does not immediately destroy the UI. HappyMeasure requests Stop and waits for the measurement/cleanup path to finish. If that path reports an error, the application remains open so the operator can verify physical `OUTPUT OFF` before closing.

## Partial-data rescue

If a measurement fails after one or more points have already been acquired, HappyMeasure attempts to preserve those points as an explicitly partial `SweepResult`, register a partial trace, and write an automatic backup. The partial result carries a warning identifying the measurement error and is not treated as a normally completed run.

A failure to register or back up the partial dataset is logged separately and must not hide the original measurement/cleanup error.

## UI recovery states

Normal completion, STOP and Abort/Error are distinct outcomes. After cleanup, the application must permit another run from the documented ready states without stale stop/pause flags.

See `STATE_MACHINE.md` for run/connection state semantics and `HARDWARE_VALIDATION_PROTOCOL.md` for the release hardware gate.

## Operator recovery after a real-hardware error

1. Confirm the instrument output is physically OFF.
2. Save `logs/error.log`, `logs/console_last_run.log`, any partial-data backup, and the relevant diagnostic archive.
3. Disconnect the DUT if the fault could involve compliance, wiring, range, or communication state.
4. Run the output-off hardware preflight again.
5. Reproduce first with the simulator or a safe dummy load and conservative compliance.
6. Return to a real DUT only after the failure mode is understood and the output-off path has been rechecked.

## Known boundary

HappyMeasure does not claim a firmware-specific recovery matrix for every Keithley model/firmware combination. Automated tests verify software contracts; staged real-hardware checks remain required for release claims.
