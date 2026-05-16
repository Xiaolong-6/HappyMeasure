from __future__ import annotations

import math
import tkinter as tk
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
        for i, (weight, minsize) in enumerate([(2, 300), (2, 150), (2, 190), (2, 210), (2, 220)]):
            self.status_bar.columnconfigure(i, weight=weight, minsize=minsize)
        conn = ttk.Frame(self.status_bar, style="Status.TFrame")
        conn.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        conn.columnconfigure(1, weight=1)
        self.connection_light_canvas = tk.Canvas(
            conn,
            width=16,
            height=16,
            borderwidth=0,
            highlightthickness=0,
            relief="flat",
            background=getattr(self, "_palette", {}).get("bg", "#F7F9FB"),
        )
        self.connection_light_canvas.grid(row=0, column=0, sticky="w", padx=(0, 6))
        # Backward-compatible alias for older code/tests that only check existence.
        self.connection_light_label = self.connection_light_canvas
        self._draw_connection_status_icon("disconnected")
        ttk.Label(conn, textvariable=self.status_connection_text, style="StatusCell.TLabel").grid(row=0, column=1, sticky="ew")
        ttk.Label(self.status_bar, textvariable=self.status, style="StatusCell.TLabel").grid(row=0, column=1, sticky="ew", padx=(0, 10))
        ttk.Label(self.status_bar, textvariable=self.points_text, style="StatusCell.TLabel").grid(row=0, column=2, sticky="ew", padx=(0, 10))
        ttk.Label(self.status_bar, textvariable=self.last_save_text, style="StatusCell.TLabel").grid(row=0, column=3, sticky="ew", padx=(0, 10))
        ttk.Label(self.status_bar, textvariable=self.update_status_text, style="StatusCell.TLabel").grid(row=0, column=4, sticky="ew")


    def _status_icon_palette(self) -> dict[str, str]:
        palette = getattr(self, "_palette", {})
        return {
            "bg": palette.get("bg", "#F7F9FB"),
            "fg": palette.get("fg", "#1F2933"),
            "muted": palette.get("muted", "#66788A"),
            "green": palette.get("forest", "#1ABC9C"),
            "red": palette.get("danger", "#E74C3C"),
            "amber": "#F2B84B",
            "gray": palette.get("muted", "#66788A"),
            "accent": palette.get("accent", "#3498DB"),
            "border": palette.get("border", "#D6E3EA"),
        }

    def _draw_connection_status_icon(self, kind: str) -> None:
        """Draw a fixed-size status icon without relying on emoji fallback.

        Tk/Windows may render emoji circles as monochrome fallback glyphs.  The
        status icon is therefore a small Canvas drawing whose size is independent
        of user-selected UI font family/size.
        """
        canvas = getattr(self, "connection_light_canvas", None)
        if canvas is None:
            return
        colors = self._status_icon_palette()
        try:
            canvas.configure(width=16, height=16, background=colors["bg"])
            canvas.delete("all")
            normalized = str(kind).lower()
            if normalized == "simulated":
                self._draw_status_gear(canvas, colors)
                return
            fill = {
                "connected": colors["green"],
                "connecting": colors["amber"],
                "error": colors["red"],
                "disconnected": colors["red"],
            }.get(normalized, colors["gray"])
            canvas.create_oval(3, 3, 13, 13, fill=fill, outline=colors["border"], width=1)
            canvas.create_oval(5, 5, 8, 8, fill="#FFFFFF", outline="")
        except Exception:
            # Status rendering must never block the measurement UI.
            return

    def _draw_status_gear(self, canvas: tk.Canvas, colors: dict[str, str]) -> None:
        """Draw a compact 16x16 gear icon for simulator/debug mode."""
        cx = cy = 8
        tooth_outer = 7
        tooth_inner = 5
        points: list[float] = []
        for i in range(16):
            angle = -math.pi / 2 + i * math.pi / 8
            radius = tooth_outer if i % 2 == 0 else tooth_inner
            points.extend([cx + radius * math.cos(angle), cy + radius * math.sin(angle)])
        canvas.create_polygon(points, fill=colors["accent"], outline=colors["border"], width=1)
        canvas.create_oval(4, 4, 12, 12, fill=colors["bg"], outline=colors["fg"], width=1)
        canvas.create_oval(6, 6, 10, 10, fill=colors["fg"], outline="")

    def _set_connection_status_icon(self, kind: str) -> None:
        self._draw_connection_status_icon(kind)
