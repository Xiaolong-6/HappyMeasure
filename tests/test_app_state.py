from __future__ import annotations

import threading

from keith_ivt.ui.app_state import AppAction, AppState, ConnectionState, RunState


def test_authoritative_state_enums_match_contract():
    assert {state.name for state in ConnectionState} == {
        "DISCONNECTED",
        "SIMULATED",
        "CONNECTING",
        "CONNECTED",
        "ERROR",
    }
    assert {state.name for state in RunState} == {
        "IDLE",
        "PREPARING",
        "SWEEPING",
        "PAUSED",
        "STOPPING",
        "STOPPED",
        "COMPLETED",
        "ERROR",
        "ABORTED",
    }


def test_initial_state_and_connection_gate():
    state = AppState()
    assert state.run_state is RunState.IDLE
    assert state.connection_state is ConnectionState.DISCONNECTED
    assert not state.can_start_sweep()
    assert state.dispatch(AppAction.CONNECT_SIMULATED, device_id="sim", device_model="Keithley 2400")
    assert state.can_start_sweep()
    assert state.connection_state is ConnectionState.SIMULATED


def test_run_transitions_and_events():
    state = AppState()
    events = []
    state.on_state_change("run_state", events.append)
    assert state.set_run_state(RunState.PAUSED) is False
    assert state.set_run_state(RunState.RUNNING) is True
    assert state.set_run_state(RunState.PAUSED) is True
    assert state.set_run_state(RunState.RUNNING) is True
    assert state.request_stop() is True
    assert state.stop_requested is True
    assert state.set_run_state(RunState.STOPPING) is True
    assert state.set_run_state(RunState.IDLE) is True
    assert state.stop_requested is False
    assert [e.new_state for e in events] == ["sweeping", "paused", "sweeping", "stopping", "idle"]


def test_status_string_and_error_reset():
    state = AppState()
    state.dispatch(AppAction.START_SWEEP)
    state.point_count = 3
    state.estimated_total = 10
    assert state.get_status_string() == "Running 3/10"
    state.set_error("serial timeout")
    assert "serial timeout" in state.get_status_string()
    state.clear_error()
    assert state.run_state is RunState.IDLE


def test_dispatch_drives_terminal_run_states():
    state = AppState()
    assert state.dispatch(AppAction.START_SWEEP)
    assert state.run_state is RunState.SWEEPING
    assert state.dispatch(AppAction.SWEEP_COMPLETED)
    assert state.run_state is RunState.COMPLETED
    assert state.get_status_string() == "Completed"
    assert state.dispatch(AppAction.FORCE_IDLE)
    assert state.run_state is RunState.IDLE


def test_thread_safe_state_does_not_corrupt():
    state = AppState()
    failures = []

    def worker() -> None:
        for _ in range(100):
            ok1 = state.set_run_state(RunState.RUNNING)
            ok2 = state.set_run_state(RunState.IDLE)
            if not (ok1 and ok2):
                failures.append((ok1, ok2))

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert not failures
    assert state.run_state is RunState.IDLE
