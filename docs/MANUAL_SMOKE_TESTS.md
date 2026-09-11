# Manual Smoke Tests

Run these checks after the automated source gates and before release packaging/hardware verification. Real hardware is required only where explicitly stated.

## Simulator state flow

1. Start `Run_HappyMeasure.bat`.
2. Connect the debug simulator.
3. Start a sweep.
4. Pause/Resume on a supported active sweep.
5. Stop the sweep.
6. Start again.
7. Abort/error a run using a safe simulator path if available.
8. Start again.
9. Disconnect and reconnect.

Expected:

- status does not remain stuck in an active state after Stop/Abort/completion;
- Start works again from documented ready states;
- stop/pause flags do not leak into the next run;
- partial/aborted data are not presented as a normal completed run.

## Constant-Time / Time plot

1. Select Constant Time with Standard acquisition and run a short trace.
2. Open Advanced Acquisition and verify Standard/Fast/Custom enable/disable behavior.
3. In Time plot settings, exercise marker `Auto`, `On`, and `Off`.
4. Select `Last N` with a small N and run long enough to exceed it.
5. Confirm the live view follows the latest points without obvious axis/canvas flashing.
6. Finish/Stop the run and switch to the completed trace.

Expected:

- Last-N affects live display only; authoritative data are not truncated;
- the completed trace can show the full elapsed-time range;
- large completed traces do not re-enable a dense marker cloud under Auto;
- acquisition remains responsive when render refresh is slower than sample arrival.

## Trace/export smoke test

1. Run a simulator trace for device A.
2. Rename the trace to a name containing underscores.
3. Run a second trace for device B.
4. Hide one trace.
5. Export selected, visible, and all traces.
6. Clear all.
7. Import the exported CSV files.

Expected:

- renamed trace metadata are preserved;
- export-visible excludes hidden traces and export-all includes them;
- Time/Adaptive/underscore-containing names do not duplicate filename tokens;
- Clear All resets the workspace save/export state coherently;
- imported traces restore plot/list metadata without modifying source data.

## Settings and diagnostics

1. Back up `config/settings.json` and `config/presets.json`.
2. Disable **Check Updates on Startup** and save/review settings.
3. Reopen the settings review and confirm the preference remains disabled.
4. Enable developer tools and run **UI Diagnostics** in a short/low-height window.
5. Confirm UI Diagnostics returns to a usable Settings page and all diagnostics actions remain reachable by scrolling.
6. Restart the UI once with no unsaved work and confirm the replacement process launches cleanly.

Expected:

- missing/old settings fields fall back safely;
- string booleans such as `"False"` are interpreted correctly;
- corrupt settings do not prevent startup;
- review/save does not silently reset unrelated preferences;
- diagnostics do not invoke hardware actions.

## Map Reconstruction

With `.[dev,map]` installed:

1. Launch Map Reconstruction and confirm it starts maximized.
2. Open CSV A, prepare, reconstruct, and enter Map Analysis.
3. Open CSV B and exercise Save/Discard/Cancel replacement behavior.
4. Confirm accepted CSV B returns the workflow to Signal Preparation and no CSV A result/QC/processed map remains active.
5. Reconstruct CSV B.
6. Save and reopen an `.hmmap` project.
7. Confirm manual min/max, percentile wording, palette and **Flip color** controls are visible and responsive.

## Update flow

Use a disposable portable/source test environment; never test updater replacement against the only copy of user data.

Expected:

- update metadata checking is asynchronous/non-blocking;
- a release with a valid portable asset plus SHA-256 digest may offer **Download and install** only after explicit user confirmation;
- a release without a usable digest falls back to opening/manual download rather than installing unverified bytes;
- cancelling the prompt does not replace files;
- offline/rate-limit/error paths remain non-blocking and readable.

## Real hardware preflight

Only after source/desktop gates pass, and with a known safe setup, run:

```bat
python -m happymeasure.hardware_preflight COM3 --baud 9600
```

Expected:

- it queries identity and sends output off only;
- it does not source voltage/current or run a sweep;
- failures produce a readable preflight failure;
- the instrument front panel is physically confirmed OFF before proceeding to the staged hardware protocol.
