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
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


class ConnectionState(Enum):
    """Central connection-state values used by the UI and future controllers."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"


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
            return self.run_state.value

    @property
    def is_connected(self) -> bool:
        with self._lock:
            return self.connection_state == ConnectionState.CONNECTED

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self.run_state in {RunState.RUNNING, RunState.PAUSED, RunState.STOPPING}

    @property
    def is_paused(self) -> bool:
        with self._lock:
            return self.run_state == RunState.PAUSED

    def force_idle(self) -> None:
        """Return to idle from any run state and clear transient operator flags."""
        with self._lock:
            old_state = self.run_state
            self.run_state = RunState.IDLE
            self.stop_requested = False
            self.pause_requested = False
            self.point_count = 0
            self.estimated_total = 0
            if old_state != RunState.IDLE:
                self._emit_event("run_state", StateChangeEvent(old_state=old_state.value, new_state=RunState.IDLE.value))

    def force_disconnected(self) -> None:
        """Return to disconnected from any connection state."""
        with self._lock:
            old_state = self.connection_state
            self.connection_state = ConnectionState.DISCONNECTED
            self.connected_device_id = ""
            self.connected_device_model = ""
            if old_state != ConnectionState.DISCONNECTED:
                self._emit_event("connection_state", StateChangeEvent(old_state=old_state.value, new_state=ConnectionState.DISCONNECTED.value))

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
                self.run_state == RunState.IDLE
                and self.connection_state == ConnectionState.CONNECTED
                and not self.stop_requested
            )

    def can_pause_sweep(self) -> bool:
        with self._lock:
            return self.run_state == RunState.RUNNING

    def can_resume_sweep(self) -> bool:
        with self._lock:
            return self.run_state == RunState.PAUSED and not self.stop_requested

    def can_stop_sweep(self) -> bool:
        with self._lock:
            return self.run_state in {RunState.RUNNING, RunState.PAUSED}

    def set_run_state(self, new_state: RunState) -> bool:
        with self._lock:
            if self.run_state == new_state:
                return True
            if not self._is_valid_transition(self.run_state, new_state):
                return False
            old_state = self.run_state
            self.run_state = new_state
            if new_state == RunState.IDLE:
                self.stop_requested = False
                self.pause_requested = False
                self.point_count = 0
                self.estimated_total = 0
            event = StateChangeEvent(old_state=old_state.value, new_state=new_state.value)
            self._emit_event("run_state", event)
            return True

    def set_connection_state(
        self,
        new_state: ConnectionState,
        device_id: str = "",
        device_model: str = "",
    ) -> bool:
        with self._lock:
            if self.connection_state == new_state:
                if new_state == ConnectionState.CONNECTED:
                    self.connected_device_id = device_id or self.connected_device_id
                    self.connected_device_model = device_model or self.connected_device_model
                return True
            if not self._is_valid_connection_transition(self.connection_state, new_state):
                return False
            old_state = self.connection_state
            self.connection_state = new_state
            if new_state == ConnectionState.CONNECTED:
                self.connected_device_id = device_id
                self.connected_device_model = device_model
            elif new_state == ConnectionState.DISCONNECTED:
                self.connected_device_id = ""
                self.connected_device_model = ""
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
        with self._lock:
            if not self.can_stop_sweep():
                return False
            self.stop_requested = True
            self._emit_event("stop_requested", StateChangeEvent(context={"reason": "user_stop"}))
            return True

    def request_pause(self) -> bool:
        with self._lock:
            if not self.can_pause_sweep():
                return False
            self.pause_requested = True
            return True

    def clear_pause_request(self) -> None:
        with self._lock:
            self.pause_requested = False

    def set_error(self, error: str) -> None:
        with self._lock:
            old_state = self.run_state
            self.last_error = error
            self.run_state = RunState.ERROR
            self._emit_event(
                "error",
                StateChangeEvent(old_state=old_state.value, new_state=RunState.ERROR.value, context={"error": error}),
            )

    def clear_error(self) -> None:
        with self._lock:
            self.last_error = None
            if self.run_state == RunState.ERROR:
                self.set_run_state(RunState.IDLE)

    @staticmethod
    def _is_valid_transition(from_state: RunState, to_state: RunState) -> bool:
        valid = {
            RunState.IDLE: {RunState.RUNNING, RunState.ERROR},
            RunState.RUNNING: {RunState.PAUSED, RunState.STOPPING, RunState.IDLE, RunState.ERROR},
            RunState.PAUSED: {RunState.RUNNING, RunState.STOPPING, RunState.IDLE, RunState.ERROR},
            RunState.STOPPING: {RunState.IDLE, RunState.ERROR},
            RunState.ERROR: {RunState.IDLE},
        }
        return to_state in valid.get(from_state, set())

    @staticmethod
    def _is_valid_connection_transition(from_state: ConnectionState, to_state: ConnectionState) -> bool:
        valid = {
            ConnectionState.DISCONNECTED: {ConnectionState.CONNECTING, ConnectionState.CONNECTED},
            ConnectionState.CONNECTING: {ConnectionState.CONNECTED, ConnectionState.DISCONNECTED},
            ConnectionState.CONNECTED: {ConnectionState.DISCONNECTING, ConnectionState.DISCONNECTED},
            ConnectionState.DISCONNECTING: {ConnectionState.DISCONNECTED},
        }
        return to_state in valid.get(from_state, set())

    def get_status_string(self) -> str:
        with self._lock:
            if self.run_state == RunState.ERROR:
                return f"Error: {self.last_error or 'Unknown'}"
            if self.run_state == RunState.RUNNING:
                if self.estimated_total:
                    return f"Running {self.point_count}/{self.estimated_total}"
                return f"Running {self.point_count}"
            if self.run_state == RunState.PAUSED:
                return f"Paused ({self.point_count} points)"
            return self.run_state.value.capitalize()
