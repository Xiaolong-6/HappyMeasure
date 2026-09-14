from __future__ import annotations

from tkinter import ttk

from keith_ivt.ui.mixin_typing import UiMixinTyping
from keith_ivt.ui.widgets import add_tip


class HardwareDiscoveryUiMixin(UiMixinTyping):
    """Add an explicit hardware auto-detect control to the Hardware panel."""

    def _build_hardware_panel(self, parent) -> None:
        super()._build_hardware_panel(parent)

        row = self.connect_btn.master
        row.columnconfigure(0, weight=1)
        row.columnconfigure(1, weight=1)
        self.connect_btn.grid_configure(row=0, column=1, sticky="ew", padx=(6, 0))
        self.detect_btn = ttk.Button(row, text="Auto Detect", command=self.auto_detect_hardware)
        self.detect_btn.grid(row=0, column=0, sticky="ew")
        add_tip(
            self.detect_btn,
            "Scan detected COM ports and supported baud rates using *IDN? only, then fill COM/Baud automatically.",
        )

    def _update_run_button_states(self) -> None:
        super()._update_run_button_states()
        state = getattr(self, "_run_state", "idle")
        can_detect = bool(
            not getattr(self, "_connected", False)
            and not self.debug.get()
            and state in {"idle", "stopped", "completed", "aborted"}
        )
        self._safe_configure("detect_btn", state="normal" if can_detect else "disabled")
