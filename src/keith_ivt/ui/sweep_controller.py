from __future__ import annotations

import queue
import threading
import time
import traceback
from pathlib import Path
from tkinter import messagebox, simpledialog

from keith_ivt.core.current_range import CurrentRangeState
from keith_ivt.data.backup import autosave_result
from keith_ivt.models import (
    SweepConfig,
    SweepKind,
    SweepResult,
    validate_config,
)
from keith_ivt.services.measurement_service import MeasurementService
from keith_ivt.services.power_guard import prevent_system_sleep
from keith_ivt.ui.app_state import AppAction


from keith_ivt.ui.mixin_typing import UiMixinTyping


class SweepControllerMixin(UiMixinTyping):
    _last_result: SweepResult | None
    _last_backup_path: Path | None
    _last_live_plot_refresh_at: float | None

    def start_sweep(self) -> None:
        if not self._connected:
            messagebox.showinfo(
                "Not connected",
                "Connect a device before starting a sweep. Debug simulator also requires Connect.",
            )
            self._update_run_button_states()
            return
        ready_states = {"idle", "stopped", "completed", "aborted"}
        if self._run_state not in ready_states:
            self._update_run_button_states()
            return
        try:
            config = self._make_config()
            validate_config(config)
            if config.sweep_kind is SweepKind.MANUAL_OUTPUT:
                self._manual_output_interlock(config)
                return
            # Adaptive table/logic is parsed by SweepRunner; it no longer requires
            # a separate validate click before a debug or real run.
        except Exception as exc:
            messagebox.showerror("Invalid sweep configuration", str(exc))
            self._refresh_run_status_from_state()
            self._update_run_button_states()
            return
        self._set_run_state("preparing")
        try:
            self._stop_event.clear()
            self._pause_event.clear()
        except Exception:
            pass
        self._x_data.clear()
        self._y_data.clear()
        self._live_points.clear()
        self._live_config = config
        self._last_live_plot_refresh_at = None
        if config.measure_scpi == "CURR":
            self._current_range_control.update_state(
                CurrentRangeState(
                    autorange=bool(config.auto_measure_range),
                    actual_range_A=(
                        config.measure_range
                        if (not config.auto_measure_range and config.measure_range > 0)
                        else None
                    ),
                    fixed_range_A=(
                        config.measure_range
                        if (not config.auto_measure_range and config.measure_range > 0)
                        else None
                    ),
                )
            )
        self._reset_live_measurement_status()
        try:
            self._measurement_xy.clear()
            self.app_state.point_count = 0
            self.app_state.estimated_total = 0
        except Exception:
            pass
        self._set_run_state("running")
        self._open_front_panel_for_sweep_start()
        self._redraw_all_plots(live_only=True, force=True)
        self.log_event(f"Sweep started: {config.mode.value} / {config.sweep_kind.value}.")
        t = threading.Thread(target=self._run_sweep_thread, args=(config,), daemon=True)
        t.start()

    def _open_front_panel_for_sweep_start(self) -> None:
        try:
            enabled = bool(self.show_front_panel_on_start.get())
        except Exception:
            enabled = True
        if enabled:
            self._open_front_panel_popup(auto_open=True)

    def _run_sweep_thread(self, config: SweepConfig) -> None:
        try:
            with prevent_system_sleep(logger=lambda message: self._queue.put(("log", message))):
                with self._make_instrument(config) as inst:
                    stop_event = getattr(self, "_stop_event", None)
                    pause_event = getattr(self, "_pause_event", None)
                    # Live current-range control is only valid for I-measure.
                    # Current-source / V-measure uses a separate voltage range
                    # subsystem that will be introduced later.
                    current_range_control = (
                        getattr(self, "_current_range_control", None)
                        if config.measure_scpi == "CURR"
                        else None
                    )
                    result = MeasurementService.run_source_meter(
                        inst,
                        config,
                        on_point=self._on_point_thread,
                        should_stop=(
                            stop_event.is_set
                            if stop_event is not None
                            else lambda: self._stop_requested
                        ),
                        should_pause=(
                            pause_event.is_set if pause_event is not None else lambda: self._paused
                        ),
                        current_range_control=current_range_control,
                    )
            self._queue.put(("complete", result))
        except Exception as exc:
            detail = traceback.format_exc()
            self._queue.put(("error", RuntimeError(f"{exc}\n{detail}")))

    def _on_point_thread(self, point, index: int, total: int) -> None:
        self._queue.put(("point", (point, index, total)))

    def toggle_pause(self) -> None:
        if self._run_state not in {"running", "paused"}:
            self._update_run_button_states()
            return
        if self._run_state == "running":
            try:
                self._pause_event.set()
                self.app_state.request_pause()
            except Exception:
                pass
            self._set_run_state("paused")
            self.log_event("Sweep paused.")
        elif self._run_state == "paused":
            try:
                self._pause_event.clear()
                self.app_state.clear_pause_request()
            except Exception:
                pass
            self._set_run_state("running")
            self.log_event("Sweep resumed.")

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
        self.log_event("Emergency stop requested.")

    def _manual_output_interlock(self, config: SweepConfig) -> None:
        msg = (
            "Manual output is hazardous. It directly enables source output without a fixed duration sweep.\n\n"
            f"Mode: {config.mode.value}\nValue: {config.constant_value}\nCompliance: {config.compliance}\n\n"
            "Type ENABLE OUTPUT to continue."
        )
        token = simpledialog.askstring("Manual output safety interlock", msg)
        if token != "ENABLE OUTPUT":
            self.log_event("Manual output cancelled by safety interlock.")
            return
        if not messagebox.askyesno(
            "Final confirmation", "Turn source output ON now? You must stop it manually."
        ):
            return
        try:
            with self._make_instrument(config) as inst:
                try:
                    inst.reset()
                    inst.configure_for_sweep(config)
                    inst.set_source(config.source_scpi, config.constant_value)
                    inst.output_on()
                    time.sleep(0.2)
                finally:
                    inst.output_off()
            self.log_event(
                "Manual output interlock path executed. Alpha implementation turns output off after smoke-test pulse."
            )
            messagebox.showinfo(
                "Manual output", "Alpha safety path executed and output was turned off."
            )
        except Exception as exc:
            self.log_event(f"Manual output failed: {exc}")
            messagebox.showerror("Manual output failed", str(exc))

    def _process_queue(self) -> None:
        """Drain worker messages without starving Tk button events.

        The simulator can generate points faster than Matplotlib can redraw.  The
        previous implementation drained the whole queue and redrew once per
        point, which could keep Tk busy long enough that Pause/Stop clicks were
        not delivered until the sweep had already finished.  Process a bounded
        batch and redraw at most once per tick so operator controls stay
        responsive.
        """
        redraw_live = False
        processed = 0
        max_messages = 40
        try:
            while processed < max_messages:
                kind, payload = self._queue.get_nowait()
                processed += 1
                if kind == "point":
                    point, index, total = payload
                    self._live_points.append(point)
                    self._x_data.append(point.source_value)
                    self._y_data.append(point.measured_value)
                    try:
                        self._measurement_xy.append(point.source_value, point.measured_value)
                        self.app_state.point_count = index
                        self.app_state.estimated_total = max(0, int(total))
                    except Exception:
                        pass
                    self._last_source_value = point.source_value
                    self._last_measured_value = point.measured_value
                    self._refresh_live_measurement_status()
                    if self._run_state != "stopping":
                        self._refresh_run_status_from_state()
                    redraw_live = True
                elif kind == "complete":
                    self._handle_complete(payload)
                    redraw_live = False
                elif kind == "error":
                    self._handle_error(payload)
                    redraw_live = False
                elif kind == "update_check":
                    result, prompt_install = payload
                    self._handle_update_check_result(result, prompt_install=bool(prompt_install))
                elif kind == "log":
                    self.log_event(str(payload))
        except queue.Empty:
            pass
        if (
            redraw_live
            and self._run_state in {"running", "paused", "stopping"}
            and self._live_plot_refresh_due()
        ):
            self._redraw_all_plots(live_only=True)
        self.root.after(35 if processed >= max_messages else 100, self._process_queue)

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
        try:
            self._last_backup_path = autosave_result(result)
            self.backup_text.set(f"Backup: {self._last_backup_path.name}")
            self._mark_last_save("auto-backup")
            self.log_event(f"Sweep completed. Auto-backup saved: {self._last_backup_path}")
        except Exception as exc:
            self.log_event(f"Sweep completed, backup failed: {exc}")
        self._reset_live_measurement_status()
        self._close_auto_front_panel_popup()

    def _handle_error(self, exc: Exception) -> None:
        error_text = str(exc)
        self.app_state.dispatch(AppAction.SWEEP_ERROR, error=error_text)
        try:
            self._refresh_run_status_from_state()
            self._update_run_button_states()
            self.log_event(f"Error: {error_text}")

            self._live_points.clear()
            self._x_data.clear()
            self._y_data.clear()
            self._live_config = None
            try:
                self._measurement_xy.clear()
            except Exception:
                pass
            try:
                self._stop_event.clear()
                self._pause_event.clear()
            except Exception:
                pass
            try:
                self._current_range_control.drain_actions()
                self._current_range_control.update_state(CurrentRangeState())
            except Exception:
                pass
            self._reset_live_measurement_status()
            self._close_auto_front_panel_popup()
            self._redraw_all_plots()

            messagebox.showerror("Sweep error", error_text)
        finally:
            self.app_state.dispatch(AppAction.FORCE_IDLE)
            self._refresh_run_status_from_state()
            self._update_run_button_states()
