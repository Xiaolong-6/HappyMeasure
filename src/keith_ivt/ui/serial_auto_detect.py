from __future__ import annotations

from tkinter import messagebox

from keith_ivt.services.serial_discovery import discover_supported_serial_hardware
from keith_ivt.ui.mixin_typing import UiMixinTyping


class SerialAutoDetectMixin(UiMixinTyping):
    """Resolve a supported COM port and baud before Connect and on demand."""

    def _set_discovery_label(self, text: str) -> None:
        profile = getattr(self, "hardware_profile_text", None)
        if profile is not None:
            try:
                profile.set(text)
            except Exception:
                pass

    def auto_detect_hardware(self, *, show_error: bool = True) -> bool:
        """Scan for a supported Keithley and fill the COM/baud selectors.

        Discovery is intentionally identity-only: it sends ``*IDN?`` with a
        short timeout and does not reset the instrument, source anything,
        acquire a measurement, or alter output state.
        """

        if getattr(self, "_connected", False):
            return True
        if self.debug.get():
            if show_error:
                messagebox.showinfo(
                    "Auto Detect",
                    "Auto Detect is for real serial hardware. Disable the debug simulator first.",
                )
            return False

        self._safe_configure("detect_btn", state="disabled", text="Detecting...")
        self._set_discovery_label("Scanning COM ports...")
        try:
            self.log_event("Hardware auto-detect started (*IDN? only).")
        except Exception:
            pass
        try:
            try:
                self.root.update_idletasks()
            except Exception:
                pass

            preferred_port = str(self.port.get() or "").strip() or None
            try:
                preferred_baud = int(self.baud_rate.get())
            except (TypeError, ValueError):
                preferred_baud = None

            try:
                match = discover_supported_serial_hardware(
                    preferred_port=preferred_port,
                    preferred_baud=preferred_baud,
                )
            except Exception as exc:
                match = None
                try:
                    self.log_event(f"Serial auto-detect unavailable: {exc}")
                except Exception:
                    pass

            if match is None:
                self._set_discovery_label("No supported Keithley detected")
                try:
                    self.log_event(
                        "No supported Keithley 2400-family instrument was auto-detected; "
                        "manual COM/baud selection remains available."
                    )
                except Exception:
                    pass
                if show_error:
                    messagebox.showwarning(
                        "Hardware not detected",
                        "No supported Keithley 2400-family instrument responded on the detected COM ports and supported baud rates.\n\n"
                        "Keep OUTPUT OFF, check the RS-232 cable and instrument serial settings, then retry or select COM/Baud manually.",
                    )
                return False

            self.port.set(match.port)
            self.baud_rate.set(match.baud_rate)
            try:
                ports = self._refresh_port_choices()
                if match.port not in ports:
                    self.port_combo.configure(values=[match.port, *ports])
            except Exception:
                pass
            self.port.set(match.port)
            self.baud_rate.set(match.baud_rate)
            self._set_discovery_label(
                f"Keithley {match.model} — detected on {match.port} @ {match.baud_rate}"
            )
            try:
                self.log_event(
                    f"Auto-detected Keithley {match.model} on {match.port} at "
                    f"{match.baud_rate} baud."
                )
            except Exception:
                pass
            return True
        finally:
            self._safe_configure("detect_btn", text="Auto Detect")
            try:
                self._update_run_button_states()
            except Exception:
                pass

    def connect_or_disconnect(self) -> None:
        connected = bool(getattr(self, "_connected", False))
        debug = bool(self.debug.get())
        if not connected and not debug:
            detected = self.auto_detect_hardware(show_error=False)
            if not detected:
                try:
                    self.log_event(
                        "Auto-detect did not find a supported 2400-family device; "
                        "trying the selected COM/baud settings."
                    )
                except Exception:
                    pass

        super().connect_or_disconnect()
