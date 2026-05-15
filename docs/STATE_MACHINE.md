# State Machine Notes

HappyMeasure 0.5.0-alpha.1 reduces the dual-state risk by backing legacy UI attributes with `AppState`.

## Run states

```text
idle -> running -> paused -> running
idle -> running -> stopping -> idle
running/paused/stopping -> error -> idle
```

## Connection states

```text
disconnected -> connecting -> connected -> disconnecting -> disconnected
```

The existing mixins still use compatibility names such as `_run_state` and `_connected`, but these are now properties that read/write `AppState`. This avoids a risky one-shot rewrite before hardware bring-up while making `AppState` the effective source for run/connection state.

## Remaining work

- Move run/connection transitions out of mixins and into dedicated controller services.
- Replace string state checks with `RunState` and `ConnectionState` enum checks.
- Add complete state-graph tests for invalid transitions and exception cleanup.
