from __future__ import annotations

from keith_ivt.services.serial_discovery import discover_supported_serial_hardware
from keith_ivt.ui.mixin_typing import UiMixinTyping


class SerialAutoDetectMixin(UiMixinTyping):
    """Opportunistically resolve a supported COM port and baud before Connect."""

    def connect_or_disconnect(self) -> None:
        connected = bool(getattr(self, "_connected", False))
        debug = bool(self.debug.get())
        if not connected and not debug:
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

            if match is not None:
                self.port.set(match.port)
                self.baud_rate.set(match.baud_rate)
                try:
                    self.log_event(
                        f"Auto-detected Keithley {match.model} on {match.port} at "
                        f"{match.baud_rate} baud."
                    )
                except Exception:
                    pass
            else:
                try:
                    self.log_event(
                        "No supported Keithley 2400-family instrument was auto-detected; "
                        "trying the selected COM/baud settings."
                    )
                except Exception:
                    pass

        super().connect_or_disconnect()
