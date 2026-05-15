from __future__ import annotations

from tkinter import messagebox

from keith_ivt.drivers.base import DriverCapabilities
from keith_ivt.instrument.serial_2400 import Keithley2400Serial
from keith_ivt.instrument.simulator import SimulatedKeithley
from keith_ivt.models import SweepKind, SweepMode
from keith_ivt.ui.app_state import ConnectionState, RunState


class HardwareControllerMixin:

    def _detect_serial_ports(self) -> list[str]:
        """Return available serial ports. Debug mode always exposes COM3 for offline tests."""
        if getattr(self, "debug", None) is not None and self.debug.get():
            return ["COM3"]
        ports: list[str] = []
        try:
            from serial.tools import list_ports
            ports = [p.device for p in list_ports.comports()]
        except Exception as exc:
            try:
                self.log_event(f"Serial port detection unavailable: {exc}")
            except Exception:
                pass
        return ports or [self.port.get() or "COM3"]

    def _refresh_port_choices(self) -> list[str]:
        ports = self._detect_serial_ports()
        try:
            if hasattr(self, "port_combo") and self.port_combo.winfo_exists():
                self.port_combo.configure(values=ports)
        except Exception:
            pass
        if self.port.get() not in ports:
            self.port.set(ports[0])
        return ports
    def _default_capabilities(self, connected: bool = False) -> DriverCapabilities:
        if not connected:
            return DriverCapabilities(
                name="No device detected",
                vendor="none",
                model_family="none",
                supports_voltage_source=False,
                supports_current_source=False,
                supports_cv=False,
                supports_front_rear=False,
                supports_4wire=False,
                supports_fixed_range=False,
                supports_manual_output=False,
            )
        return DriverCapabilities(name="Generic source-meter", vendor="generic", model_family="generic-smu")

    def _detect_capabilities_from_idn(self, idn: str) -> DriverCapabilities:
        text = idn.upper()
        if "SIMULATED" in text:
            return DriverCapabilities(
                name="Debug simulator / Keithley 2400 profile",
                vendor="simulator",
                model_family="smu-iv",
                supports_voltage_source=True,
                supports_current_source=True,
                supports_cv=False,
                supports_front_rear=True,
                supports_4wire=True,
                supports_fixed_range=True,
                supports_manual_output=True,
            )
        if "KEITHLEY" in text and ("2400" in text or "2410" in text or "2420" in text or "2430" in text or "2440" in text):
            return DriverCapabilities(
                name="Keithley 2400-series SMU",
                vendor="Keithley",
                model_family="2400-series-smu",
                supports_voltage_source=True,
                supports_current_source=True,
                supports_cv=False,
                supports_front_rear=True,
                supports_4wire=True,
                supports_fixed_range=True,
                supports_manual_output=True,
            )
        if "KEITHLEY" in text and "2450" in text:
            return DriverCapabilities(
                name="Keithley 2450 SMU",
                vendor="Keithley",
                model_family="2450-smu",
                supports_voltage_source=True,
                supports_current_source=True,
                supports_cv=False,
                supports_front_rear=True,
                supports_4wire=True,
                supports_fixed_range=True,
                supports_manual_output=True,
            )
        # Conservative fallback: IV only until a real driver advertises more.
        return DriverCapabilities(name="Generic IV instrument", vendor="unknown", model_family="generic-iv", supports_cv=False)

    def _available_modes(self) -> list[str]:
        cap = self._active_capabilities
        values: list[str] = []
        if cap.supports_voltage_source or not self._connected:
            values.append(SweepMode.VOLTAGE_SOURCE.value)
        if cap.supports_current_source or not self._connected:
            values.append(SweepMode.CURRENT_SOURCE.value)
        return values or [SweepMode.VOLTAGE_SOURCE.value]

    def _available_sweep_kinds(self) -> list[str]:
        return [SweepKind.STEP.value, SweepKind.CONSTANT_TIME.value, SweepKind.ADAPTIVE.value]

    def _capability_summary(self) -> str:
        return self._detected_device_model()

    def _detected_device_model(self) -> str:
        if not self._connected:
            return "--"
        if self.debug.get():
            return "Debug simulator / Keithley 2400"
        parts = [p.strip() for p in (self._connected_idn or "").split(",") if p.strip()]
        if len(parts) >= 2:
            return parts[1]
        return self._active_capabilities.name or "Detected instrument"

    def _sweep_capability_note(self) -> str:
        if not self._connected:
            return "Connect a real instrument or debug simulator before editing/running sweeps."
        return "Keithley 2400-series IV workflow: Step, Time, and Adaptive sweeps are available."

    def _refresh_capability_widgets(self) -> None:
        mode_combo = self._widget_alive("mode_combo")
        if mode_combo is not None:
            values = self._available_modes()
            mode_combo.configure(values=values)
            if self.mode.get() not in values:
                self.mode.set(values[0])
        sweep_kind_combo = self._widget_alive("sweep_kind_combo")
        if sweep_kind_combo is not None:
            values = self._available_sweep_kinds()
            sweep_kind_combo.configure(values=values)
            if self.sweep_kind.get() not in values:
                self.sweep_kind.set(values[0])
        note = self._widget_alive("sweep_capability_note")
        if note is not None:
            note.configure(text=self._sweep_capability_note())
        if hasattr(self, "hardware_profile_text") and self.hardware_profile_text is not None:
            try:
                self.hardware_profile_text.set(self._capability_summary())
            except Exception:
                pass

    def _widget_alive(self, attr: str):
        widget = getattr(self, attr, None)
        try:
            if widget is not None and widget.winfo_exists():
                return widget
        except Exception:
            pass
        if hasattr(self, attr):
            setattr(self, attr, None)
        return None

    def _safe_configure(self, attr: str, **kwargs) -> None:
        widget = self._widget_alive(attr)
        if widget is None:
            return
        try:
            widget.configure(**kwargs)
        except Exception:
            setattr(self, attr, None)

    def _set_run_state(self, state: str) -> None:
        if state not in {"idle", "running", "paused", "stopping"}:
            raise ValueError(f"Unknown run state: {state}")
        previous = getattr(self, "_run_state", "idle")
        self._run_state = state
        self._running = state in {"running", "paused", "stopping"}
        self._paused = state == "paused"
        # Entering stopping must release a paused runner so it can see should_stop().
        self._stop_requested = state == "stopping"
        try:
            target = {
                "idle": RunState.IDLE,
                "running": RunState.RUNNING,
                "paused": RunState.PAUSED,
                "stopping": RunState.STOPPING,
            }[state]
            if getattr(self.app_state, "run_state", RunState.IDLE) != target:
                self.app_state.set_run_state(target)
        except Exception:
            # Keep the legacy fields authoritative during the migration.
            pass
        if previous != state:
            try:
                self.log_event(f"Run state: {previous} -> {state}")
            except Exception:
                pass
        self._safe_configure("pause_btn", text="▶ Resume" if state == "paused" else "⏸ Pause")
        self._update_run_button_states()

    def _update_run_button_states(self) -> None:
        state = getattr(self, "_run_state", "idle")
        can_start = bool(self._connected and state == "idle")
        can_pause = bool(self._connected and state in {"running", "paused"})
        can_stop = bool(self._connected and state in {"running", "paused"})
        can_connect_or_disconnect = bool(state == "idle")
        self._safe_configure("start_btn", state="normal" if can_start else "disabled")
        self._safe_configure("pause_btn", state="normal" if can_pause else "disabled")
        self._safe_configure("stop_btn", state="normal" if can_stop else "disabled")
        self._safe_configure("connect_btn", state="normal" if can_connect_or_disconnect else "disabled")
        self._set_hardware_fields_state()
        self._set_sweep_fields_state()
        self._set_operator_identity_state()

    def _set_hardware_fields_state(self) -> None:
        busy = getattr(self, "_run_state", "idle") != "idle"
        state = "disabled" if (self._connected or busy) else "normal"
        for attr in ("port_combo", "baud_combo", "terminal_combo", "sense_combo"):
            widget = getattr(self, attr, None)
            try:
                if widget and widget.winfo_exists():
                    widget.configure(state="disabled" if (self._connected or busy) else "readonly")
            except Exception:
                pass

    def _set_sweep_fields_state(self) -> None:
        editable = bool(self._connected and getattr(self, "_run_state", "idle") == "idle")
        state = "normal" if editable else "disabled"
        for attr in ("mode_combo", "sweep_kind_combo", "debug_model_row"):
            widget = getattr(self, attr, None)
            try:
                if widget and widget.winfo_exists(): widget.configure(state="readonly" if state == "normal" else "disabled")
            except Exception:
                pass
        for box_attr in ("dynamic_box", "common_box"):
            box = getattr(self, box_attr, None)
            try:
                if box and box.winfo_exists():
                    for child in box.winfo_children():
                        try:
                            child.configure(state=state)
                        except Exception as e:
                            # Log widget configuration errors at debug level
                            import logging
                            logger = logging.getLogger("keith_ivt.ui.hardware_controller")
                            logger.debug(f"Failed to configure child widget state: {e}")
                            for sub in getattr(child, "winfo_children", lambda: [])():
                                try:
                                    sub.configure(state=state)
                                except Exception as e2:
                                    logger.debug(f"Failed to configure sub-widget state: {e2}")
            except Exception as e:
                import logging
                logger = logging.getLogger("keith_ivt.ui.hardware_controller")
                logger.debug(f"Failed to update dynamic controls state: {e}")
        self._update_range_state()

    def _set_operator_identity_state(self) -> None:
        state = "normal" if getattr(self, "_run_state", "idle") == "idle" else "disabled"
        for attr in ("device_entry", "operator_entry"):
            self._safe_configure(attr, state=state)

    def _make_instrument(self, config=None):
        """Create an instrument without reading Tk variables from a worker thread.

        When called by the sweep worker, pass the immutable SweepConfig built on
        the UI thread.  Tkinter variables are not thread-safe; reading them from
        the worker was the root cause of Pause/Stop failures reported as
        "main thread is not in main loop".
        """
        if config is not None:
            if config.debug:
                return SimulatedKeithley(model_name=config.debug_model)
            return Keithley2400Serial(port=config.port, baud_rate=int(config.baud_rate))
        if self.debug.get():
            return SimulatedKeithley(model_name=self.debug_model.get())
        return Keithley2400Serial(port=self.port.get(), baud_rate=int(self.baud_rate.get()))


    def connect_or_disconnect(self) -> None:
        """Single hardware action button: connect when idle/disconnected, disconnect when idle/connected."""
        if getattr(self, "_connected", False):
            self.disconnect_hardware()
        else:
            self.connect_or_check()

    def connect_or_check(self) -> None:
        try:
            with self._make_instrument() as inst:
                idn = inst.identify()
            self._connected = True
            self._connected_idn = idn
            self._active_capabilities = self._detect_capabilities_from_idn(idn)
            try:
                self.app_state.set_connection_state(ConnectionState.CONNECTED, device_id=idn, device_model=self._active_capabilities.name)
            except Exception:
                pass
            self.status.set("Ready")
            self.log_event(f"Connected/detected: {idn}; profile={self._active_capabilities.name}")
        except Exception as exc:
            self._connected = False
            self._connected_idn = ""
            self._active_capabilities = self._default_capabilities(connected=False)
            try:
                self.app_state.set_connection_state(ConnectionState.DISCONNECTED)
            except Exception:
                pass
            self.status.set("Connection failed")
            self.log_event(f"Connection failed: {exc}")
            messagebox.showerror("Connection failed", str(exc))
        self._refresh_port_choices()
        self._refresh_port_choices()
        self._refresh_instrument_indicator()
        self._refresh_capability_widgets()
        self._update_run_button_states()

    def disconnect_hardware(self) -> None:
        self._connected = False
        self._connected_idn = ""
        self._active_capabilities = self._default_capabilities(connected=False)
        try:
            self.app_state.set_connection_state(ConnectionState.DISCONNECTED)
        except Exception:
            pass
        self.status.set("Ready")
        self.log_event("Instrument status set to disconnected.")
        self._refresh_instrument_indicator()
        self._refresh_capability_widgets()
        self._update_run_button_states()

    def _on_debug_changed(self, *_args) -> None:
        # Changing debug/non-debug swaps the instrument backend. Any existing
        # connection profile is now stale, so force a fresh Connect.
        if self._connected:
            self._connected = False
            self._connected_idn = ""
            self._active_capabilities = self._default_capabilities(connected=False)
            try:
                self.app_state.set_connection_state(ConnectionState.DISCONNECTED)
            except Exception:
                pass
            self.status.set("Connection reset")
            self.log_event("Connection reset after debug simulator toggle; re-detect required.")
        self._refresh_port_choices()
        self._refresh_instrument_indicator()
        self._refresh_capability_widgets()
        if getattr(self, "_active_nav", None) in {"Sweep", "Settings"}:
            self._show_nav(self._active_nav)

    def _refresh_instrument_indicator(self) -> None:
        if self.debug.get() and self._connected:
            self.instrument_status.set("Debug simulator ready")
            self.status_connection_text.set("Instrument: debug simulator | Keithley 2400")
            self.connection_light_text.set("😈")
        elif self.debug.get():
            self.instrument_status.set("Debug simulator")
            self.status_connection_text.set("Instrument: debug simulator selected")
            self.connection_light_text.set("😈")
        elif self._connected:
            self.instrument_status.set("Ready")
            self.status_connection_text.set(f"Instrument: {self.port.get()} | {self._detected_device_model()}")
            self.connection_light_text.set("🟢")
        else:
            self.instrument_status.set("Not connected")
            self.status_connection_text.set("Instrument: --")
            self.connection_light_text.set("🔴")
        self._safe_configure("connection_light_label", style="ConnGreen.TLabel" if self._connected else "ConnRed.TLabel")
        self._safe_configure("connect_btn", text="Disconnect" if self._connected else "Connect", style="Connected.TButton" if self._connected else "TButton")
        self._set_hardware_fields_state()
        self._set_sweep_fields_state()
        self._update_range_state()
        self._update_run_button_states()
