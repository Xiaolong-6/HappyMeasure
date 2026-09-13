from __future__ import annotations

from tkinter import messagebox

from keith_ivt.ui.mixin_typing import UiMixinTyping


class ShutdownSafetyMixin(UiMixinTyping):
    """Own cooperative Stop and safe main-window shutdown semantics."""

    def _bind_variables(self) -> None:
        super()._bind_variables()
        self.root.protocol("WM_DELETE_WINDOW", self._request_safe_close)

    def abort_sweep(self) -> None:
        if self._run_state not in {"running", "paused"}:
            self._update_run_button_states()
            return
        try:
            self._stop_event.set()
            self._pause_event.clear()
            self.app_state.request_stop()
        except Exception:
            pass
        self._set_run_state("stopping")
        self._reset_live_measurement_status()
        self._close_auto_front_panel_popup()
        self.log_event(
            "Stop requested. Active instrument I/O must return before OUTPUT OFF cleanup can complete."
        )

    def _request_safe_close(self) -> None:
        state = getattr(self, "_run_state", "idle")
        active = state in {"preparing", "running", "paused", "stopping"}
        if not active:
            self._app_closing = True
            self.root.destroy()
            return

        if getattr(self, "_close_after_sweep", False):
            messagebox.showwarning(
                "Measurement still stopping",
                "HappyMeasure is waiting for active instrument I/O and OUTPUT OFF cleanup. "
                "If the instrument is unresponsive, use its physical OUTPUT OFF control.",
                parent=self.root,
            )
            return

        if not messagebox.askyesno(
            "Measurement active",
            "Stop the measurement and close only after software cleanup completes?\n\n"
            "The Stop request cannot interrupt a serial read already in progress. "
            "Use the instrument front panel for immediate physical output-off if needed.",
            parent=self.root,
        ):
            return

        self._close_after_sweep = True
        if state in {"running", "paused"}:
            self.abort_sweep()
        else:
            try:
                self._stop_event.set()
                self._pause_event.clear()
                self.app_state.request_stop()
            except Exception:
                pass
        self.log_event("Application close requested; waiting for measurement cleanup.")

    def _handle_complete(self, result) -> None:
        close_after = bool(getattr(self, "_close_after_sweep", False))
        super()._handle_complete(result)
        if close_after:
            self._close_after_sweep = False
            self._app_closing = True
            self.log_event("Measurement cleanup completed; closing application.")
            self.root.destroy()

    def _handle_error(self, exc: Exception) -> None:
        close_after = bool(getattr(self, "_close_after_sweep", False))
        super()._handle_error(exc)
        if close_after:
            self._close_after_sweep = False
            messagebox.showwarning(
                "Close cancelled after measurement error",
                "HappyMeasure kept the application open because the measurement/cleanup path reported an error. "
                "Verify OUTPUT OFF on the instrument front panel before closing.",
                parent=self.root,
            )


__all__ = ["ShutdownSafetyMixin"]
