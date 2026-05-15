from __future__ import annotations

from tkinter import ttk


class StatusBarMixin:
    """Dedicated bottom status bar builder for connection/run/backup state.

    Contract: connection indicators stay in the bottom status bar only.
    Header/page title must never host connection status labels.
    """

    def _build_status_bar(self) -> None:
        """Dedicated bottom status bar for connection/run/point/backup state."""
        self.status_bar = ttk.Frame(self.root, style="Status.TFrame", padding=(8, 5))
        self.status_bar.grid(row=2, column=getattr(self, "_workspace_column", 0), sticky="ew")
        for i, (weight, minsize) in enumerate([(2, 300), (2, 150), (2, 190), (2, 210)]):
            self.status_bar.columnconfigure(i, weight=weight, minsize=minsize)
        conn = ttk.Frame(self.status_bar, style="Status.TFrame")
        conn.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        conn.columnconfigure(1, weight=1)
        self.connection_light_label = ttk.Label(conn, textvariable=self.connection_light_text, style="ConnRed.TLabel")
        self.connection_light_label.grid(row=0, column=0, sticky="w", padx=(0, 6))
        ttk.Label(conn, textvariable=self.status_connection_text, style="StatusCell.TLabel").grid(row=0, column=1, sticky="ew")
        ttk.Label(self.status_bar, textvariable=self.status, style="StatusCell.TLabel").grid(row=0, column=1, sticky="ew", padx=(0, 10))
        ttk.Label(self.status_bar, textvariable=self.points_text, style="StatusCell.TLabel").grid(row=0, column=2, sticky="ew", padx=(0, 10))
        ttk.Label(self.status_bar, textvariable=self.last_save_text, style="StatusCell.TLabel").grid(row=0, column=3, sticky="ew")

