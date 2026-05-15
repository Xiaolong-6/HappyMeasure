from __future__ import annotations

from tkinter import ttk

from keith_ivt.ui.widgets import add_tip


class OperatorBarMixin:
    """Bottom device/operator/control strip.

    Contract: this strip hosts editable run metadata and Start/Pause/Stop only.
    Connection/run indicators stay in the independent status bar.
    """

    def _build_operator_bar(self) -> None:
        """Bottom device-operation strip shared by all pages."""
        self.action_bar = ttk.Frame(self.root, style="Operator.TFrame", padding=(12, 10))
        self.action_bar.grid(row=1, column=getattr(self, "_workspace_column", 0), sticky="ew", padx=8, pady=(2, 4))
        for col, (weight, minsize) in enumerate([(2, 170), (2, 170), (3, 300)]):
            self.action_bar.columnconfigure(col, weight=weight, minsize=minsize)

        device_box = ttk.Frame(self.action_bar, style="OperatorGroup.TFrame")
        device_box.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        device_box.columnconfigure(0, weight=1)
        ttk.Label(device_box, text="Device", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        self.device_entry = ttk.Entry(device_box, textvariable=self.device_name)
        self.device_entry.grid(row=1, column=0, sticky="ew", pady=(3, 0))
        add_tip(self.device_entry, "Name attached to the next completed trace.")

        operator_box = ttk.Frame(self.action_bar, style="OperatorGroup.TFrame")
        operator_box.grid(row=0, column=1, sticky="ew", padx=(0, 12))
        operator_box.columnconfigure(0, weight=1)
        ttk.Label(operator_box, text="Operator", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        self.operator_entry = ttk.Entry(operator_box, textvariable=self.operator)
        self.operator_entry.grid(row=1, column=0, sticky="ew", pady=(3, 0))
        add_tip(self.operator_entry, "Operator name saved in CSV metadata.")

        controls = ttk.Frame(self.action_bar, style="OperatorGroup.TFrame")
        controls.grid(row=0, column=2, sticky="ew", padx=(0, 12))
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)
        controls.columnconfigure(2, weight=1)
        ttk.Label(controls, text="Controls", style="Muted.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        self.start_btn = ttk.Button(controls, text="Start", style="Start.TButton", command=self.start_sweep)
        self.start_btn.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(3, 0))
        add_tip(
            self.start_btn,
            "Start the selected sweep. Real hardware output may turn ON after configuration.",
        )
        self.pause_btn = ttk.Button(controls, text="Pause", style="Pause.TButton", command=self.toggle_pause, state="disabled")
        self.pause_btn.grid(row=1, column=1, sticky="ew", padx=6, pady=(3, 0))
        add_tip(
            self.pause_btn,
            "Pause or resume point collection. Pause holds the current source state; it does not turn output off. Use STOP for output off.",
        )
        self.stop_btn = ttk.Button(controls, text="STOP", style="Stop.TButton", command=self.abort_sweep)
        self.stop_btn.grid(row=1, column=2, sticky="ew", padx=(6, 0), pady=(3, 0))
        add_tip(
            self.stop_btn,
            "Safety stop: abort the sweep and request output off at the next safe point. Confirm Output OFF on the instrument front panel.",
        )

        self._operator_groups = (device_box, operator_box, controls)
        self.root.bind("<Configure>", lambda _e: self._update_operator_layout(), add="+")
        self.root.after(80, self._update_operator_layout)

    def _update_operator_layout(self) -> None:
        """Responsive layout for the bottom device-operation strip."""
        if not hasattr(self, "_operator_groups"):
            return
        try:
            device_box, operator_box, controls = self._operator_groups
            narrow = self.root.winfo_width() < 980
            for col in range(3):
                self.action_bar.columnconfigure(col, weight=0, minsize=0)
            if narrow:
                self.action_bar.columnconfigure(0, weight=1, minsize=180)
                self.action_bar.columnconfigure(1, weight=1, minsize=180)
                device_box.grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=(0, 8))
                operator_box.grid(row=0, column=1, sticky="ew", padx=(0, 0), pady=(0, 8))
                controls.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0, 0), pady=(0, 0))
            else:
                for col, (weight, minsize) in enumerate([(2, 170), (2, 170), (3, 300)]):
                    self.action_bar.columnconfigure(col, weight=weight, minsize=minsize)
                device_box.grid(row=0, column=0, sticky="ew", padx=(0, 12), pady=0)
                operator_box.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=0)
                controls.grid(row=0, column=2, sticky="ew", padx=(0, 0), pady=0)
        except Exception:
            pass
