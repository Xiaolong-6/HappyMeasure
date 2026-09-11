# State Machine Contract

HappyMeasure uses `AppState` as the authoritative run/connection state model. Controllers dispatch `AppAction` values; UI labels render from state and worker threads report back through queue/callback boundaries instead of mutating Tk widgets directly.

## Run states

```text
IDLE
PREPARING
SWEEPING
PAUSED
STOPPING
STOPPED
COMPLETED
ERROR
ABORTED
```

`SWEEPING` is the canonical active-measurement state. `RunState.RUNNING` remains only as a deprecated compatibility alias with the same enum value; legacy text `running` is normalized to `SWEEPING`.

Ready-to-start states are `IDLE`, `STOPPED`, `COMPLETED`, and `ABORTED`, provided the connection is `CONNECTED` or `SIMULATED` and no stop request is pending.

Typical run transitions:

```text
IDLE -> PREPARING -> SWEEPING -> COMPLETED
IDLE -> PREPARING -> SWEEPING -> PAUSED -> SWEEPING
SWEEPING/PAUSED -> STOPPING -> STOPPED
SWEEPING/PAUSED/STOPPING -> ERROR
SWEEPING/PAUSED/STOPPING/PREPARING -> ABORTED
ERROR -> IDLE
STOPPED/COMPLETED/ABORTED -> next PREPARING/allowed ready transition
```

Stop/pause request flags are transient operator state. Completion/stop/abort/force-idle paths clear them so a later run does not inherit stale control state.

## Connection states

```text
DISCONNECTED
SIMULATED
CONNECTING
CONNECTED
ERROR
```

Typical connection transitions:

```text
DISCONNECTED -> CONNECTING -> CONNECTED
DISCONNECTED -> CONNECTING -> SIMULATED
CONNECTING/CONNECTED/SIMULATED -> ERROR
CONNECTED/SIMULATED/ERROR -> DISCONNECTED
```

Successful connected/simulated states own the detected device identity/model. Disconnection clears active device identity; connection errors retain a readable connection error for the UI.

## State discipline

- `AppState.dispatch(...)` is the normal transition gate.
- `can_start_sweep()`, `can_pause_sweep()`, `can_resume_sweep()`, and `can_stop_sweep()` define operator-action eligibility.
- Worker paths must not infer state by status-label text.
- `_run_state` / `_connected`-style compatibility accessors may remain in older UI mixins, but new logic must use the authoritative state/actions rather than adding another parallel state source.
- Error handling must preserve the distinction between `STOPPED`, `COMPLETED`, `ABORTED`, and `ERROR`.

State-graph behavior is covered by tests; this document should describe the accepted contract, not a migration roadmap.
