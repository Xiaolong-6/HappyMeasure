from __future__ import annotations

from pathlib import Path

from keith_ivt.data.backup import autosave_result
from keith_ivt.models import SweepConfig, SweepResult
from keith_ivt.ui.mixin_typing import UiMixinTyping


class AutoBackupPreferenceMixin(UiMixinTyping):
    """Apply the persisted auto-backup preference to completed sweeps.

    This mixin sits between ``ShutdownSafetyMixin`` and ``SweepControllerMixin``
    in the cooperative MRO. Manual ``backup_now()`` remains available regardless
    of the automatic-backup preference.
    """

    _last_result: SweepResult | None
    _last_backup_path: Path | None
    _live_config: SweepConfig | None

    def _handle_complete(self, result: SweepResult) -> None:
        was_stopping = self._run_state == "stopping" or self._stop_requested
        self._set_run_state("stopped" if was_stopping else "completed")
        self._last_result = result
        trace = self._datasets.add_result(result, result.config.device_name)
        self._selected_trace_id = trace.trace_id
        self._live_points.clear()
        self._x_data.clear()
        self._y_data.clear()
        self._live_config = None
        self._refresh_trace_list()
        self._redraw_all_plots()

        if bool(getattr(self.settings, "auto_save_backup", True)):
            try:
                self._last_backup_path = autosave_result(result)
                self.backup_text.set(f"Backup: {self._last_backup_path.name}")
                self._mark_last_save("auto-backup")
                self.log_event(f"Sweep completed. Auto-backup saved: {self._last_backup_path}")
            except Exception as exc:
                self.log_event(f"Sweep completed, backup failed: {exc}")
        else:
            self.backup_text.set("Backup: auto-save off")
            self.log_event("Sweep completed. Automatic backup is disabled in Default Settings.")

        self._reset_live_measurement_status()
        self._close_auto_front_panel_popup()


__all__ = ["AutoBackupPreferenceMixin"]
