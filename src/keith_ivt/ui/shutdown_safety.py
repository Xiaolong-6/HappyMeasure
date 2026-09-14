from __future__ import annotations

from tkinter import messagebox

from keith_ivt.data.backup import autosave_result
from keith_ivt.models import SweepResult
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

    def _rescue_partial_result(self, exc: Exception) -> SweepResult | None:
        config = getattr(self, "_live_config", None)
        points = list(getattr(self, "_live_points", []) or [])
        if config is None or not points:
            return None

        first_line = str(exc).splitlines()[0] if str(exc) else type(exc).__name__
        result = SweepResult(
            config=config,
            points=points,
            warnings=[f"Partial data recovered after measurement error: {first_line}"],
        )
        setattr(self, "_last_result", result)

        try:
            trace = self._datasets.add_result(result, f"{config.device_name} (partial)")
            setattr(self, "_selected_trace_id", trace.trace_id)
            self._refresh_trace_list()
            self.log_event(f"Recovered {len(points)} partial point(s) into the trace list.")
        except Exception as dataset_exc:
            self.log_event(f"Partial dataset registration failed: {dataset_exc}")

        settings = getattr(self, "settings", None)
        if bool(getattr(settings, "auto_save_backup", True)):
            try:
                backup_path = autosave_result(result)
                setattr(self, "_last_backup_path", backup_path)
                self.backup_text.set(f"Backup: {backup_path.name}")
                self._mark_last_save("error-backup")
                self.log_event(f"Partial measurement auto-backup saved: {backup_path}")
            except Exception as backup_exc:
                self.log_event(f"Partial measurement backup failed: {backup_exc}")
        else:
            self.backup_text.set("Backup: auto-save off")
            self.log_event(
                "Partial measurement recovered in memory; automatic backup is disabled in Default Settings."
            )
        return result

    def _handle_error(self, exc: Exception) -> None:
        close_after = bool(getattr(self, "_close_after_sweep", False))
        self._rescue_partial_result(exc)
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
