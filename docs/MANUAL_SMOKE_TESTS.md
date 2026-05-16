# Manual Smoke Tests

Run these checks after a source-level hardening change and before release-prep build testing. They do not require real hardware unless explicitly stated.

## Simulator state flow

1. Start `Run_HappyMeasure.bat`.
2. Connect the debug simulator.
3. Start a sweep.
4. Pause if the current UI exposes pause/resume for the active sweep path.
5. Stop the sweep.
6. Start again.
7. Abort a sweep.
8. Start again.
9. Disconnect and reconnect.

Expected results:

- The status bar must not remain stuck in `Sweeping` after stop/abort/completion.
- Start must work from ready states such as stopped, completed, and aborted.
- Stop/Abort must return the UI to a state where another sweep is possible after cleanup.
- Partial data should be visible or clearly absent; the UI must not silently pretend an aborted run completed normally.

## Trace/export smoke test

1. Run a simulator trace for device A.
2. Rename the trace to `test_A`.
3. Run a second trace for device B.
4. Hide one trace.
5. Export selected.
6. Export visible.
7. Export all.
8. Clear all.
9. Import the exported CSV files.

Expected results:

- Renamed trace names are preserved in export/import.
- Export visible excludes hidden traces.
- Export all includes hidden traces.
- Clear all clears plot, trace list, selection, and save/export state.
- Import refreshes plot, trace list, and device/trace selection consistently.

## Config and preset compatibility

1. Back up `config/settings.json` and `config/presets.json`.
2. Start the app.
3. Change theme and UI font size.
4. Change a few sweep defaults and save them if the UI path supports it.
5. Close and reopen the app.
6. Load any presets created by older alpha versions.

Expected results:

- Missing or old fields fall back to defaults.
- String booleans such as `"False"` are interpreted correctly.
- Corrupt settings should fall back to defaults instead of preventing app startup.
- Invalid presets should be ignored or sanitized rather than crashing the UI.

## Update reminder

1. Start the app with network access.
2. Confirm the UI remains responsive while update metadata is checked.
3. Open About and use the release/update button.
4. Repeat with network disabled if possible.

Expected results:

- The app only reads GitHub release metadata.
- It does not download, install, or replace files.
- Offline failure does not block or crash the UI.

## Real hardware preflight

Only run this with a known safe instrument setup. Prefer disconnected outputs or a dummy load before the first real sweep.

```bat
python -m happymeasure.hardware_preflight COM3 --baud 9600
```

Expected results:

- The command prints the safety note.
- It queries identity and sends output off only.
- It does not source voltage/current or run a sweep.
- Failures print a readable `FAIL hardware preflight` message.
