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
        icon_size = self._status_icon_size()
        self.connection_light_canvas = tk.Canvas(
            conn,
            width=icon_size,
            height=icon_size,
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


    def _status_icon_size(self) -> int:
        """Return the UI-scale-aware status icon size in pixels."""
        try:
            size_pt = int(self.ui_font_size.get()) if hasattr(self, "ui_font_size") else int(getattr(self.settings, "ui_font_size", 10))
        except Exception:
            size_pt = 10
        return max(14, min(28, size_pt + 7))

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
        """Draw a UI-scale-aware status icon without relying on emoji fallback.

        Tk/Windows may render emoji circles as monochrome fallback glyphs.  The
        status icon is therefore a Canvas drawing. Its size follows the UI scale
        while remaining independent of the selected font family.
        """
        canvas = getattr(self, "connection_light_canvas", None)
        if canvas is None:
            return
        colors = self._status_icon_palette()
        try:
            icon_size = self._status_icon_size()
            canvas.configure(width=icon_size, height=icon_size, background=colors["bg"])
            canvas.delete("all")
            normalized = str(kind).lower()
            if normalized == "simulated":
                self._draw_status_gear(canvas, colors, icon_size)
                return
            fill = {
                "connected": colors["green"],
                "connecting": colors["amber"],
                "error": colors["red"],
                "disconnected": colors["red"],
            }.get(normalized, colors["gray"])
            margin = max(2, icon_size // 5)
            shine_margin = margin + max(2, icon_size // 7)
            shine_size = max(3, icon_size // 4)
            canvas.create_oval(margin, margin, icon_size - margin, icon_size - margin, fill=fill, outline=colors["border"], width=1)
            canvas.create_oval(shine_margin, shine_margin, shine_margin + shine_size, shine_margin + shine_size, fill="#FFFFFF", outline="")
        except Exception:
            # Status rendering must never block the measurement UI.
            return

    def _draw_status_gear(self, canvas: tk.Canvas, colors: dict[str, str], icon_size: int) -> None:
        """Draw a compact UI-scale-aware gear icon for simulator/debug mode."""
        cx = cy = icon_size / 2
        tooth_outer = max(6, icon_size / 2 - 1)
        tooth_inner = max(4, icon_size / 2 - 4)
        points: list[float] = []
        for i in range(16):
            angle = -math.pi / 2 + i * math.pi / 8
            radius = tooth_outer if i % 2 == 0 else tooth_inner
            points.extend([cx + radius * math.cos(angle), cy + radius * math.sin(angle)])
        hole_outer = max(4, icon_size * 0.25)
        hole_inner = max(2, icon_size * 0.12)
        canvas.create_polygon(points, fill=colors["accent"], outline=colors["border"], width=1)
        canvas.create_oval(cx - hole_outer, cy - hole_outer, cx + hole_outer, cy + hole_outer, fill=colors["bg"], outline=colors["fg"], width=1)
        canvas.create_oval(cx - hole_inner, cy - hole_inner, cx + hole_inner, cy + hole_inner, fill=colors["fg"], outline="")

    def _set_connection_status_icon(self, kind: str) -> None:
        self._draw_connection_status_icon(kind)
