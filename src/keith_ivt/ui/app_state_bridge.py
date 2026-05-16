from __future__ import annotations

from keith_ivt.ui.app_state import AppAction, ConnectionState, RunState


class AppStateBridgeMixin:
    """Compatibility properties backed by AppState.

    Existing UI mixins still use legacy attribute names.  These properties keep
    those call sites working while making AppState the source for run and
    connection state.
    """
    @property
    def _run_state(self) -> str:
        return self.app_state.run_state_text

    @_run_state.setter
    def _run_state(self, value: str) -> None:
        target = {
            "idle": AppAction.FORCE_IDLE,
            "preparing": AppAction.PREPARE_SWEEP,
            "running": AppAction.START_SWEEP,
            "sweeping": AppAction.START_SWEEP,
            "paused": AppAction.PAUSE_SWEEP,
            "stopping": AppAction.REQUEST_STOP,
            "stopped": AppAction.SWEEP_STOPPED,
            "completed": AppAction.SWEEP_COMPLETED,
            "error": AppAction.SWEEP_ERROR,
            "aborted": AppAction.ABORT_SWEEP,
        }.get(str(value).lower())
        if target is None:
            raise ValueError(f"Unknown run state: {value}")
        self.app_state.dispatch(target)

    @property
    def _connected(self) -> bool:
        return self.app_state.is_connected

    @_connected.setter
    def _connected(self, value: bool) -> None:
        if value:
            if not self.app_state.is_connected:
                self.app_state.dispatch(AppAction.CONNECT_SUCCESS)
        else:
            self.app_state.force_disconnected()

    @property
    def _running(self) -> bool:
        return self.app_state.is_running

    @_running.setter
    def _running(self, value: bool) -> None:
        if not value and self.app_state.is_running:
            self.app_state.force_idle()

    @property
    def _paused(self) -> bool:
        return self.app_state.is_paused

    @_paused.setter
    def _paused(self, value: bool) -> None:
        if value and self.app_state.run_state == RunState.RUNNING:
            self.app_state.dispatch(AppAction.PAUSE_SWEEP)

    @property
    def _stop_requested(self) -> bool:
        return self.app_state.stop_requested

    @_stop_requested.setter
    def _stop_requested(self, value: bool) -> None:
        if value:
            self.app_state.dispatch(AppAction.REQUEST_STOP)
        else:
            self.app_state.stop_requested = False

    def _refresh_run_status_from_state(self) -> None:
        """Render the run status label from AppState only."""
        if hasattr(self, "status"):
            self.status.set(self.app_state.get_status_string())

    def _refresh_connection_status_from_state(self) -> None:
        """Render connection labels from AppState only."""
        debug_selected = bool(getattr(self, "debug", None) is not None and self.debug.get())
        state = self.app_state.connection_state
        text = self.app_state.get_connection_status_string(debug_selected=debug_selected)
        if state is ConnectionState.CONNECTED and hasattr(self, "port"):
            text = f"Instrument: {self.port.get()} | {self._detected_device_model()}"

        if hasattr(self, "status_connection_text"):
            self.status_connection_text.set(text)
        if hasattr(self, "instrument_status"):
            labels = {
                ConnectionState.DISCONNECTED: "Debug simulator" if debug_selected else "Not connected",
                ConnectionState.SIMULATED: "Debug simulator ready",
                ConnectionState.CONNECTING: "Connecting",
                ConnectionState.CONNECTED: "Ready",
                ConnectionState.ERROR: "Connection error",
            }
            self.instrument_status.set(labels.get(state, "Not connected"))
        if hasattr(self, "connection_light_text"):
            # Retained for backward-compatible StringVar consumers only; the
            # visible status icon is Canvas-rendered to avoid Windows/Tk emoji
            # fallback problems.
            self.connection_light_text.set(
                "simulated"
                if state is ConnectionState.SIMULATED
                else "connected"
                if state is ConnectionState.CONNECTED
                else "connecting"
                if state is ConnectionState.CONNECTING
                else "error"
                if state is ConnectionState.ERROR
                else "disconnected"
            )
        if hasattr(self, "_set_connection_status_icon"):
            icon_kind = (
                "simulated"
                if state is ConnectionState.SIMULATED
                else "connected"
                if state is ConnectionState.CONNECTED
                else "connecting"
                if state is ConnectionState.CONNECTING
                else "error"
                if state is ConnectionState.ERROR
                else "disconnected"
            )
            self._set_connection_status_icon(icon_kind)

