# State Machine Notes

HappyMeasure keeps one authoritative application state source: `AppState`.
UI code and worker callbacks must not infer or directly mutate run/connection
labels. State changes go through `AppState.dispatch(action, **context)` and UI
labels render from that state.

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

## Connection states

```text
DISCONNECTED
SIMULATED
CONNECTING
CONNECTED
ERROR
```

## State discipline

- `AppState` is the single authority for run and connection state.
- Controllers dispatch actions such as `START_SWEEP`, `PAUSE_SWEEP`,
  `CONNECT_SUCCESS`, and `SWEEP_COMPLETED`.
- Worker threads communicate with the Tk thread by queue messages; they do not
  directly mutate Tk widgets.
- The status bar renders from `AppState.get_status_string()` and
  `AppState.get_connection_status_string()`.
- Legacy compatibility names such as `_run_state` and `_connected` remain as
  properties during migration, but their setters dispatch state actions.

## Typical transitions

```text
IDLE -> PREPARING -> SWEEPING -> COMPLETED
IDLE -> PREPARING -> SWEEPING -> PAUSED -> SWEEPING
SWEEPING/PAUSED -> STOPPING -> STOPPED
SWEEPING/PAUSED/STOPPING -> ERROR -> IDLE
DISCONNECTED -> CONNECTING -> CONNECTED
DISCONNECTED -> CONNECTING -> SIMULATED
CONNECTING/CONNECTED/SIMULATED -> ERROR -> DISCONNECTED
CONNECTED/SIMULATED -> DISCONNECTED
```

## Remaining work

- Replace string state checks with `RunState` and `ConnectionState` enum checks.
- Continue shrinking legacy compatibility property usage in UI mixins.
- Add complete state-graph tests for every invalid transition and exception cleanup path.
