from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable
import threading


class RunState(Enum):
    """Central run-state values used by the UI and future controllers."""

    IDLE = "idle"
    PREPARING = "preparing"
    SWEEPING = "sweeping"
    RUNNING = "sweeping"  # legacy alias retained for old call sites
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    COMPLETED = "completed"
    ERROR = "error"
    ABORTED = "aborted"


class ConnectionState(Enum):
    """Central connection-state values used by the UI and future controllers."""

    DISCONNECTED = "disconnected"
    SIMULATED = "simulated"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class AppAction(Enum):
    """Authoritative state transition actions.

    UI and worker paths should dispatch these actions instead of guessing or
    directly mutating display labels.
    """

    CONNECT_START = "connect_start"
    CONNECT_SIMULATED = "connect_simulated"
    CONNECT_SUCCESS = "connect_success"
    CONNECT_FAILED = "connect_failed"
    DISCONNECT = "disconnect"
    RESET_CONNECTION = "reset_connection"
    PREPARE_SWEEP = "prepare_sweep"
    START_SWEEP = "start_sweep"
    PAUSE_SWEEP = "pause_sweep"
    RESUME_SWEEP = "resume_sweep"
    REQUEST_STOP = "request_stop"
    SWEEP_STOPPED = "sweep_stopped"
    SWEEP_COMPLETED = "sweep_completed"
    SWEEP_ERROR = "sweep_error"
    ABORT_SWEEP = "abort_sweep"
    FORCE_IDLE = "force_idle"


class SweepKind(Enum):
    """UI-facing sweep family names independent of the core model enum."""

    STEP = "step"
    CONSTANT_TIME = "constant_time"
    ADAPTIVE = "adaptive"


@dataclass(frozen=True)
class StateChangeEvent:
    """Small immutable event emitted after a state transition."""

    timestamp: datetime = field(default_factory=datetime.now)
    old_state: str = ""
    new_state: str = ""
    context: dict = field(default_factory=dict)


class AppState:
    """Thread-safe application state skeleton.

    This module is intentionally introduced before the full UI migration.  It
    provides a tested single-state model for subsequent refactors without
    destabilising the current alpha UI in one large change.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.run_state: RunState = RunState.IDLE
        self.connection_state: ConnectionState = ConnectionState.DISCONNECTED
        self.stop_requested = False
        self.pause_requested = False
        self.connected_device_id = ""
        self.connected_device_model = ""
        self.last_error: str | None = None
        self.last_connection_error: str | None = None
        self.last_backup_path: Path | None = None
        self.sweep_kind: SweepKind = SweepKind.STEP
        self.point_count = 0
        self.estimated_total = 0
        self._listeners: dict[str, list[Callable[[StateChangeEvent], None]]] = {
            "run_state": [],
            "connection_state": [],
            "stop_requested": [],
            "error": [],
        }


    @property
    def run_state_text(self) -> str:
        with self._lock:
            if self.run_state is RunState.SWEEPING:
                return "running"
            return self.run_state.value

    @property
    def is_connected(self) -> bool:
        with self._lock:
            return self.connection_state in {ConnectionState.CONNECTED, ConnectionState.SIMULATED}

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self.run_state in {
                RunState.PREPARING,
                RunState.SWEEPING,
                RunState.PAUSED,
                RunState.STOPPING,
            }

    @property
    def is_paused(self) -> bool:
        with self._lock:
            return self.run_state == RunState.PAUSED

    def force_idle(self) -> None:
        """Return to idle from any run state and clear transient operator flags."""
        self.dispatch(AppAction.FORCE_IDLE)

    def force_disconnected(self) -> None:
        """Return to disconnected from any connection state."""
        self.dispatch(AppAction.DISCONNECT)

    def on_state_change(self, event_type: str, callback: Callable[[StateChangeEvent], None]) -> None:
        with self._lock:
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            self._listeners[event_type].append(callback)

    def _emit_event(self, event_type: str, event: StateChangeEvent) -> None:
        callbacks = list(self._listeners.get(event_type, []))
        for callback in callbacks:
            try:
                callback(event)
            except Exception:
                # State notifications must not break sweep control paths.
                pass

    def can_start_sweep(self) -> bool:
        with self._lock:
            return (
                self.run_state in {RunState.IDLE, RunState.STOPPED, RunState.COMPLETED}
                and self.connection_state in {ConnectionState.CONNECTED, ConnectionState.SIMULATED}
                and not self.stop_requested
            )

    def can_pause_sweep(self) -> bool:
        with self._lock:
            return self.run_state == RunState.SWEEPING

    def can_resume_sweep(self) -> bool:
        with self._lock:
            return self.run_state == RunState.PAUSED and not self.stop_requested

    def can_stop_sweep(self) -> bool:
        with self._lock:
            return self.run_state in {RunState.SWEEPING, RunState.PAUSED}

    def set_run_state(self, new_state: RunState) -> bool:
        action = {
            RunState.IDLE: AppAction.FORCE_IDLE,
            RunState.PREPARING: AppAction.PREPARE_SWEEP,
            RunState.SWEEPING: AppAction.START_SWEEP,
            RunState.PAUSED: AppAction.PAUSE_SWEEP,
            RunState.STOPPING: AppAction.REQUEST_STOP,
            RunState.STOPPED: AppAction.SWEEP_STOPPED,
            RunState.COMPLETED: AppAction.SWEEP_COMPLETED,
            RunState.ERROR: AppAction.SWEEP_ERROR,
            RunState.ABORTED: AppAction.ABORT_SWEEP,
        }.get(new_state)
        if action is None:
            return False
        return self.dispatch(action)

    def _set_run_state_locked(self, new_state: RunState, context: dict | None = None) -> bool:
        with self._lock:
            if self.run_state == new_state:
                return True
            if not self._is_valid_transition(self.run_state, new_state):
                return False
            old_state = self.run_state
            self.run_state = new_state
            if new_state in {RunState.IDLE, RunState.STOPPED, RunState.COMPLETED, RunState.ABORTED}:
                self.stop_requested = False
                self.pause_requested = False
                if new_state == RunState.IDLE:
                    self.point_count = 0
                    self.estimated_total = 0
            event = StateChangeEvent(old_state=old_state.value, new_state=new_state.value, context=context or {})
            self._emit_event("run_state", event)
            return True

    def _force_run_state_locked(self, new_state: RunState, context: dict | None = None) -> bool:
        with self._lock:
            old_state = self.run_state
            self.run_state = new_state
            self.stop_requested = False
            self.pause_requested = False
            if new_state == RunState.IDLE:
                self.point_count = 0
                self.estimated_total = 0
            if old_state != new_state:
                self._emit_event(
                    "run_state",
                    StateChangeEvent(old_state=old_state.value, new_state=new_state.value, context=context or {}),
                )
            return True

    def set_connection_state(
        self,
        new_state: ConnectionState,
        device_id: str = "",
        device_model: str = "",
    ) -> bool:
        action = {
            ConnectionState.DISCONNECTED: AppAction.DISCONNECT,
            ConnectionState.SIMULATED: AppAction.CONNECT_SIMULATED,
            ConnectionState.CONNECTING: AppAction.CONNECT_START,
            ConnectionState.CONNECTED: AppAction.CONNECT_SUCCESS,
            ConnectionState.ERROR: AppAction.CONNECT_FAILED,
        }.get(new_state)
        if action is None:
            return False
        return self.dispatch(action, device_id=device_id, device_model=device_model)

    def _set_connection_state_locked(
        self,
        new_state: ConnectionState,
        device_id: str = "",
        device_model: str = "",
        error_message: str = "",
    ) -> bool:
        with self._lock:
            if self.connection_state == new_state:
                if new_state in {ConnectionState.CONNECTED, ConnectionState.SIMULATED}:
                    self.connected_device_id = device_id or self.connected_device_id
                    self.connected_device_model = device_model or self.connected_device_model
                return True
            if not self._is_valid_connection_transition(self.connection_state, new_state):
                return False
            old_state = self.connection_state
            self.connection_state = new_state
            if new_state in {ConnectionState.CONNECTED, ConnectionState.SIMULATED}:
                self.connected_device_id = device_id
                self.connected_device_model = device_model
            elif new_state == ConnectionState.DISCONNECTED:
                self.connected_device_id = ""
                self.connected_device_model = ""
                self.last_connection_error = None
            elif new_state == ConnectionState.ERROR:
                self.connected_device_id = ""
                self.connected_device_model = ""
                self.last_connection_error = error_message
            event = StateChangeEvent(
                old_state=old_state.value,
                new_state=new_state.value,
                context={
                    "device_id": self.connected_device_id,
                    "device_model": self.connected_device_model,
                },
            )
            self._emit_event("connection_state", event)
            return True

    def request_stop(self) -> bool:
        return self.dispatch(AppAction.REQUEST_STOP)

    def request_pause(self) -> bool:
        return self.dispatch(AppAction.PAUSE_SWEEP)

    def clear_pause_request(self) -> None:
        self.dispatch(AppAction.RESUME_SWEEP)

    def set_error(self, error: str) -> None:
        self.dispatch(AppAction.SWEEP_ERROR, error=error)

    def clear_error(self) -> None:
        with self._lock:
            self.last_error = None
            if self.run_state == RunState.ERROR:
                self.dispatch(AppAction.FORCE_IDLE)

    def dispatch(self, action: AppAction | str, **context) -> bool:
        """Apply a state transition through the single authoritative gate."""
        if not isinstance(action, AppAction):
            action = AppAction(str(action))

        if action is AppAction.CONNECT_START:
            return self._set_connection_state_locked(ConnectionState.CONNECTING)
        if action is AppAction.CONNECT_SIMULATED:
            return self._set_connection_state_locked(
                ConnectionState.SIMULATED,
                context.get("device_id", ""),
                context.get("device_model", "Debug simulator / Keithley 2400"),
            )
        if action is AppAction.CONNECT_SUCCESS:
            return self._set_connection_state_locked(
                ConnectionState.CONNECTED,
                context.get("device_id", ""),
                context.get("device_model", ""),
            )
        if action is AppAction.CONNECT_FAILED:
            return self._set_connection_state_locked(
                ConnectionState.ERROR,
                error_message=str(context.get("error", "")),
            )
        if action in {AppAction.DISCONNECT, AppAction.RESET_CONNECTION}:
            return self._set_connection_state_locked(ConnectionState.DISCONNECTED)

        if action is AppAction.PREPARE_SWEEP:
            return self._set_run_state_locked(RunState.PREPARING, context)
        if action is AppAction.START_SWEEP:
            return self._set_run_state_locked(RunState.SWEEPING, context)
        if action is AppAction.PAUSE_SWEEP:
            with self._lock:
                if self.run_state == RunState.PAUSED:
                    return True
                if not self.can_pause_sweep():
                    return False
                self.pause_requested = True
            return self._set_run_state_locked(RunState.PAUSED, context)
        if action is AppAction.RESUME_SWEEP:
            with self._lock:
                self.pause_requested = False
            return self._set_run_state_locked(RunState.SWEEPING, context)
        if action is AppAction.REQUEST_STOP:
            with self._lock:
                if self.run_state == RunState.STOPPING:
                    return True
                if not self.can_stop_sweep():
                    return False
                self.stop_requested = True
                self.pause_requested = False
                self._emit_event("stop_requested", StateChangeEvent(context={"reason": "user_stop"}))
            return self._set_run_state_locked(RunState.STOPPING, context)
        if action is AppAction.SWEEP_STOPPED:
            return self._set_run_state_locked(RunState.STOPPED, context)
        if action is AppAction.SWEEP_COMPLETED:
            return self._set_run_state_locked(RunState.COMPLETED, context)
        if action is AppAction.SWEEP_ERROR:
            with self._lock:
                self.last_error = str(context.get("error", self.last_error or "Unknown"))
            old_state = self.run_state
            changed = self._set_run_state_locked(RunState.ERROR, context)
            self._emit_event(
                "error",
                StateChangeEvent(
                    old_state=old_state.value,
                    new_state=RunState.ERROR.value,
                    context={"error": self.last_error},
                ),
            )
            return changed
        if action is AppAction.ABORT_SWEEP:
            return self._set_run_state_locked(RunState.ABORTED, context)
        if action is AppAction.FORCE_IDLE:
            return self._force_run_state_locked(RunState.IDLE, context)
        return False

    @staticmethod
    def _is_valid_transition(from_state: RunState, to_state: RunState) -> bool:
        valid = {
            RunState.IDLE: {RunState.PREPARING, RunState.SWEEPING, RunState.ERROR},
            RunState.PREPARING: {RunState.SWEEPING, RunState.STOPPING, RunState.ERROR, RunState.ABORTED},
            RunState.SWEEPING: {RunState.PAUSED, RunState.STOPPING, RunState.COMPLETED, RunState.ERROR, RunState.ABORTED},
            RunState.PAUSED: {RunState.SWEEPING, RunState.STOPPING, RunState.ERROR, RunState.ABORTED},
            RunState.STOPPING: {RunState.STOPPED, RunState.ABORTED, RunState.ERROR},
            RunState.STOPPED: {RunState.IDLE, RunState.PREPARING, RunState.SWEEPING, RunState.ERROR},
            RunState.COMPLETED: {RunState.IDLE, RunState.PREPARING, RunState.SWEEPING, RunState.ERROR},
            RunState.ABORTED: {RunState.IDLE, RunState.PREPARING, RunState.ERROR},
            RunState.ERROR: {RunState.IDLE},
        }
        return to_state in valid.get(from_state, set())

    @staticmethod
    def _is_valid_connection_transition(from_state: ConnectionState, to_state: ConnectionState) -> bool:
        valid = {
            ConnectionState.DISCONNECTED: {ConnectionState.CONNECTING, ConnectionState.CONNECTED, ConnectionState.SIMULATED, ConnectionState.ERROR},
            ConnectionState.CONNECTING: {ConnectionState.CONNECTED, ConnectionState.SIMULATED, ConnectionState.DISCONNECTED, ConnectionState.ERROR},
            ConnectionState.CONNECTED: {ConnectionState.DISCONNECTED, ConnectionState.ERROR},
            ConnectionState.SIMULATED: {ConnectionState.DISCONNECTED, ConnectionState.ERROR},
            ConnectionState.ERROR: {ConnectionState.DISCONNECTED, ConnectionState.CONNECTING},
        }
        return to_state in valid.get(from_state, set())

    def get_status_string(self) -> str:
        with self._lock:
            if self.run_state == RunState.ERROR:
                return f"Error: {self.last_error or 'Unknown'}"
            if self.run_state == RunState.PREPARING:
                return "Preparing"
            if self.run_state == RunState.SWEEPING:
                if self.estimated_total:
                    return f"Running {self.point_count}/{self.estimated_total}"
                return f"Running {self.point_count}"
            if self.run_state == RunState.PAUSED:
                return f"Paused ({self.point_count} points)"
            return {
                RunState.IDLE: "Ready",
                RunState.STOPPING: "Stopping",
                RunState.STOPPED: "Stopped",
                RunState.COMPLETED: "Completed",
                RunState.ABORTED: "Aborted",
            }.get(self.run_state, self.run_state.value.capitalize())

    def get_connection_status_string(self, debug_selected: bool = False) -> str:
        with self._lock:
            if self.connection_state == ConnectionState.SIMULATED:
                return "Instrument: debug simulator | Keithley 2400"
            if debug_selected and self.connection_state == ConnectionState.DISCONNECTED:
                return "Instrument: debug simulator selected"
            if self.connection_state == ConnectionState.CONNECTED:
                model = self.connected_device_model or "Detected instrument"
                return f"Instrument: {model}"
            if self.connection_state == ConnectionState.CONNECTING:
                return "Instrument: connecting..."
            if self.connection_state == ConnectionState.ERROR:
                return "Instrument: connection error"
            return "Instrument: --"
