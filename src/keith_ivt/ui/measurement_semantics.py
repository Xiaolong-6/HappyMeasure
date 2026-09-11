"""Cross-cutting measurement UI guards for range and capability semantics.

This mixin intentionally sits before the established UI/workflow mixins in the
application MRO.  It hardens a few measurement-facing contracts without moving
ownership out of the existing status-bar, hardware-controller, and sweep-runner
modules.
"""

from __future__ import annotations

from typing import Any

from keith_ivt.acquisition import resolve_time_acquisition
from keith_ivt.core.current_range import format_current_range, parse_current_range_label
from keith_ivt.drivers.base import DriverCapabilities, instrument_model_from_idn
from keith_ivt.models import SweepMode


_READY_STATES = {"idle", "stopped", "completed", "aborted"}
_RUNTIME_RANGE_STATES = {"running", "paused"}


class MeasurementSemanticsMixin:
    """Enforce range-control, telemetry, and model-detection semantics."""

    def _is_current_measurement(self) -> bool:
        live_config = getattr(self, "_live_config", None)
        if live_config is not None:
            return getattr(live_config, "measure_scpi", "CURR") == "CURR"
        try:
            return str(self.mode.get()) != SweepMode.CURRENT_SOURCE.value
        except Exception:
            return True

    def _range_runtime_active(self) -> bool:
        return bool(
            self._is_current_measurement()
            and getattr(self, "_run_state", "idle") in _RUNTIME_RANGE_STATES
        )

    def _effective_range_telemetry_enabled(self) -> bool:
        """Return the telemetry state actually used by the active acquisition."""

        live_config = getattr(self, "_live_config", None)
        if live_config is not None:
            try:
                return bool(resolve_time_acquisition(live_config).range_telemetry)
            except Exception:
                pass
        try:
            profile = str(self.acquisition_profile.get())
        except Exception:
            profile = ""
        if profile == "Standard":
            return True
        if profile == "Fast":
            return False
        try:
            return bool(self.range_telemetry.get())
        except Exception:
            return True

    @staticmethod
    def _set_widget_state(widget: Any, state: str) -> None:
        if widget is None:
            return
        try:
            if widget.winfo_exists():
                widget.configure(state=state)
        except Exception:
            pass

    def start_sweep(self) -> None:
        """Drop stale runtime range actions before constructing a new run."""

        control = getattr(self, "_current_range_control", None)
        if control is not None:
            try:
                control.drain_actions()
            except Exception:
                pass
        return super().start_sweep()

    def _front_panel_autorange_changed(self) -> None:
        if not self._is_current_measurement():
            self._refresh_live_measurement_status()
            return
        enabled = bool(self.auto_measure_range.get())
        control = getattr(self, "_current_range_control", None)
        if control is not None and self._range_runtime_active():
            control.request_autorange(enabled)
        self._refresh_live_measurement_status()

    def _front_panel_fixed_range_selected(self, _event=None) -> None:
        if not self._is_current_measurement():
            self._refresh_live_measurement_status()
            return
        combo = getattr(self, "_front_panel_range_combo", None)
        value = parse_current_range_label(combo.get() if combo is not None else "")
        if value is None:
            return
        self.auto_measure_range.set(False)
        self.measure_range.set(value)
        control = getattr(self, "_current_range_control", None)
        if control is not None and self._range_runtime_active():
            control.request_fixed_range(value)
        self._refresh_live_measurement_status()

    def _front_panel_lock_current_range(self) -> None:
        if not self._range_runtime_active() or not self._effective_range_telemetry_enabled():
            self._refresh_live_measurement_status()
            return
        state = self._current_range_snapshot()
        if state is None or state.actual_range_A is None:
            self._refresh_live_measurement_status()
            return
        self.measure_range.set(state.actual_range_A)
        self.auto_measure_range.set(False)
        control = getattr(self, "_current_range_control", None)
        if control is not None:
            control.request_lock_current()
        self._refresh_live_measurement_status()

    def _current_range_status_fragment(self) -> str:
        if not self._is_current_measurement():
            return "N/A"
        return super()._current_range_status_fragment()

    def _refresh_live_measurement_status(self) -> None:
        src_label, meas_label, cmpl_unit = self._current_source_measure_labels()
        source_unit = "A" if src_label.startswith("I") else "V"
        measure_unit = "V" if meas_label.startswith("V") else "A"
        try:
            compliance_value = float(self.compliance.get())
        except Exception:
            compliance_value = None
        range_text = (
            f"Irange {self._current_range_status_fragment()}"
            if self._is_current_measurement()
            else "Vrange N/A"
        )
        text = (
            f"{src_label} {self._format_eng_value(getattr(self, '_last_source_value', None), source_unit)} · "
            f"{meas_label} {self._format_eng_value(getattr(self, '_last_measured_value', None), measure_unit)} · "
            f"{range_text} · "
            f"Cmpl {self._format_eng_value(compliance_value, cmpl_unit)}"
        )
        if hasattr(self, "measurement_status_text"):
            self.measurement_status_text.set(text)
        self._refresh_front_panel_popup()

    def _refresh_front_panel_range_widgets(self) -> None:
        # Let the mature status-bar implementation populate values and menus,
        # then enforce the measurement-mode and effective-profile semantics.
        super()._refresh_front_panel_range_widgets()
        if not hasattr(self, "_front_panel_range_mode_value"):
            return

        connected = bool(getattr(self, "_connected", False))
        if not self._is_current_measurement():
            for attr in (
                "_front_panel_range_mode_value",
                "_front_panel_range_actual_value",
                "_front_panel_range_menu_value",
                "_front_panel_range_change_value",
            ):
                widget = getattr(self, attr, None)
                try:
                    if widget is not None:
                        widget.configure(text="N/A")
                except Exception:
                    pass
            warning = getattr(self, "_front_panel_range_warning", None)
            try:
                if warning is not None:
                    warning.configure(
                        text="Voltage measurement range is configured from Sweep settings; current-range controls are unavailable."
                    )
            except Exception:
                pass
            self._set_widget_state(getattr(self, "_front_panel_autorange_check", None), "disabled")
            self._set_widget_state(getattr(self, "_front_panel_range_combo", None), "disabled")
            self._set_widget_state(getattr(self, "_front_panel_lock_btn", None), "disabled")
            return

        run_state = getattr(self, "_run_state", "idle")
        editable_or_runtime = connected and (
            run_state in _READY_STATES or run_state in _RUNTIME_RANGE_STATES
        )
        telemetry_enabled = self._effective_range_telemetry_enabled()
        state = self._current_range_snapshot()
        auto = bool(self.auto_measure_range.get())

        self._set_widget_state(
            getattr(self, "_front_panel_autorange_check", None),
            "normal" if editable_or_runtime else "disabled",
        )
        self._set_widget_state(
            getattr(self, "_front_panel_range_combo", None),
            "disabled" if (not editable_or_runtime or auto) else "readonly",
        )
        lock_enabled = bool(
            connected
            and run_state in _RUNTIME_RANGE_STATES
            and telemetry_enabled
            and state is not None
            and state.actual_range_A is not None
        )
        self._set_widget_state(
            getattr(self, "_front_panel_lock_btn", None),
            "normal" if lock_enabled else "disabled",
        )

        actual_title = getattr(self, "_front_panel_range_actual_title", None)
        change_value = getattr(self, "_front_panel_range_change_value", None)
        warning = getattr(self, "_front_panel_range_warning", None)
        try:
            if actual_title is not None:
                actual_title.configure(text="Actual range" if telemetry_enabled else "Range snapshot")
            if change_value is not None:
                change_value.configure(
                    text=(
                        state.last_change_text()
                        if telemetry_enabled and state is not None
                        else "Not monitored"
                    )
                )
            if warning is not None:
                if auto and not telemetry_enabled:
                    warning.configure(
                        text="Live autorange transitions are not monitored in Fast. Select a fixed measurement range before the run for quantitative work."
                    )
                elif auto:
                    warning.configure(
                        text="Autorange may switch range during I-t acquisition; lock range for final data."
                    )
                else:
                    warning.configure(
                        text="Fixed range is active; readings remain continuous unless overload occurs."
                    )
        except Exception:
            pass

    def _on_mode_changed(self, *_args) -> None:
        super()._on_mode_changed(*_args)
        try:
            self._refresh_live_measurement_status()
        except Exception:
            pass

    def _detect_capabilities_from_idn(self, idn: str) -> DriverCapabilities:
        text = str(idn or "").upper()
        if "SIMULATED" in text:
            return self._full_cap(
                "Debug simulator / Keithley 2400 profile",
                "simulator",
                "smu-iv",
                fast_acquisition=True,
            )

        model = instrument_model_from_idn(idn)
        if "KEITHLEY" in text and model == "2401":
            return self._full_cap(
                "Keithley 2401 SMU",
                "Keithley",
                "2400-series-smu",
                fast_acquisition=True,
            )
        if "KEITHLEY" in text and model in {"2400", "2410", "2420", "2430", "2440"}:
            return self._full_cap("Keithley 2400-series SMU", "Keithley", "2400-series-smu")
        if "KEITHLEY" in text and model == "2450":
            return self._full_cap("Keithley 2450 SMU", "Keithley", "2450-smu")
        return DriverCapabilities(
            name="Generic IV instrument",
            vendor="unknown",
            model_family="generic-iv",
            supports_cv=False,
        )
