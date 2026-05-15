from __future__ import annotations

from keith_ivt.ui.app_state import ConnectionState, RunState


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
            "idle": RunState.IDLE,
            "running": RunState.RUNNING,
            "paused": RunState.PAUSED,
            "stopping": RunState.STOPPING,
            "error": RunState.ERROR,
        }.get(str(value).lower())
        if target is None:
            raise ValueError(f"Unknown run state: {value}")
        if target is RunState.IDLE:
            self.app_state.force_idle()
        elif self.app_state.run_state != target:
            self.app_state.set_run_state(target)

    @property
    def _connected(self) -> bool:
        return self.app_state.is_connected

    @_connected.setter
    def _connected(self, value: bool) -> None:
        if value:
            if not self.app_state.is_connected:
                self.app_state.set_connection_state(ConnectionState.CONNECTED)
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
            self.app_state.set_run_state(RunState.PAUSED)

    @property
    def _stop_requested(self) -> bool:
        return self.app_state.stop_requested

    @_stop_requested.setter
    def _stop_requested(self, value: bool) -> None:
        self.app_state.stop_requested = bool(value)

