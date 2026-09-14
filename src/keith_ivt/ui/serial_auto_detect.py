from __future__ import annotations

from tkinter import messagebox

from keith_ivt.services.serial_discovery import available_serial_ports
from keith_ivt.ui.mixin_typing import UiMixinTyping


class SerialAutoDetectMixin(UiMixinTyping):
    """Detect OS serial ports without guessing instrument baud settings."""

    def _set_discovery_label(self, text: str) -> None:
        profile = getattr(self, "hardware_profile_text", None)
        if profile is not None:
            try:
                profile.set(text)
            except Exception:
                pass

    def auto_detect_hardware(self, *, show_error: bool = True) -> bool:
        """Refresh available COM ports without sending any SCPI command.

        Baud remains fully operator-selected. Instrument identity is read later
        by the normal Connect path using the selected COM/baud pair. This avoids
        sending garbled SCPI while probing alternative baud rates.
        """

        if getattr(self, "_connected", False):
            return True
        if self.debug.get():
            if show_error:
                messagebox.showinfo(
                    "Detect COM",
                    "COM detection is for real serial hardware. Disable the debug simulator first.",
                )
            return False

        self._safe_configure("detect_btn", state="disabled", text="Detecting...")
        self._set_discovery_label("Scanning Windows COM ports...")
        try:
            self.log_event("COM detection started (OS enumeration only; no SCPI sent).")
        except Exception:
            pass

        try:
            try:
                self.root.update_idletasks()
            except Exception:
                pass

            ports = available_serial_ports()
            if not ports:
                self._set_discovery_label("No serial COM ports detected")
                try:
                    self.log_event("COM detection found no serial ports.")
                except Exception:
                    pass
                if show_error:
                    messagebox.showwarning(
                        "No COM ports detected",
                        "Windows did not report any serial COM ports.\n\n"
                        "Check the USB/RS-232 adapter and its driver, then try Detect COM again.",
                    )
                return False

            try:
                if hasattr(self, "port_combo") and self.port_combo.winfo_exists():
                    self.port_combo.configure(values=ports)
            except Exception:
                pass

            current = str(self.port.get() or "").strip()
            if current not in ports:
                self.port.set(ports[0])
            selected = str(self.port.get())

            try:
                baud = int(self.baud_rate.get())
                baud_text = str(baud)
            except (TypeError, ValueError):
                baud_text = str(self.baud_rate.get())

            if len(ports) == 1:
                label = (
                    f"{selected} detected — select baud ({baud_text}) and Connect to identify model"
                )
            else:
                label = (
                    f"{len(ports)} COM ports detected — selected {selected}; "
                    "choose COM/baud, then Connect"
                )
            self._set_discovery_label(label)
            try:
                self.log_event(
                    f"COM detection found {len(ports)} port(s): {', '.join(ports)}. "
                    f"Selected {selected}; baud remains {baud_text}."
                )
            except Exception:
                pass
            return True
        finally:
            self._safe_configure("detect_btn", text="Detect COM")
            try:
                self._update_run_button_states()
            except Exception:
                pass
