from __future__ import annotations

import math
import tkinter as tk
from tkinter import Toplevel, ttk

from keith_ivt.models import SweepMode


class StatusBarMixin:
    """Dedicated bottom status bar builder for compact connection/run/live readout."""

    def _build_status_bar(self) -> None:
        self.status_bar = ttk.Frame(self.root, style="Status.TFrame", padding=(8, 5))
        self.status_bar.grid(row=2, column=getattr(self, "_workspace_column", 0), sticky="ew")
        for i, (weight, minsize) in enumerate([(2, 180), (2, 130), (3, 360)]):
            self.status_bar.columnconfigure(i, weight=weight, minsize=minsize)

        conn = ttk.Frame(self.status_bar, style="Status.TFrame")
        conn.grid(row=0, column=0, sticky="ew", padx=(0, 8))
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
        self.connection_light_label = self.connection_light_canvas
        self._draw_connection_status_icon("disconnected")
        ttk.Label(conn, textvariable=self.status_connection_text, style="StatusCell.TLabel").grid(row=0, column=1, sticky="ew")

        ttk.Label(self.status_bar, textvariable=self.status, style="StatusCell.TLabel").grid(row=0, column=1, sticky="ew", padx=(0, 8))
        live = ttk.Label(self.status_bar, textvariable=self.measurement_status_text, style="StatusCell.TLabel")
        live.grid(row=0, column=2, sticky="ew")
        live.bind("<Double-1>", lambda _e: self._open_front_panel_popup(auto_open=False))
        self.connection_light_canvas.bind("<Double-1>", lambda _e: self._open_front_panel_popup(auto_open=False))

    def _status_icon_size(self) -> int:
        try:
            size_pt = int(self.ui_font_size.get()) if hasattr(self, "ui_font_size") else int(getattr(self.settings, "ui_font_size", 10))
        except Exception:
            size_pt = 10
        return max(14, min(30, size_pt + 7))

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

    def _set_connection_status_icon(self, kind: str) -> None:
        self._draw_connection_status_icon(kind)

    def _draw_connection_status_icon(self, kind: str) -> None:
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
            return

    def _draw_status_gear(self, canvas: tk.Canvas, colors: dict[str, str], icon_size: int) -> None:
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
        canvas.create_oval(cx - hole_outer, cy - hole_outer, cx + hole_outer, cy + hole_outer, fill=colors["bg"], outline=colors["border"], width=1)
        canvas.create_oval(cx - hole_inner, cy - hole_inner, cx + hole_inner, cy + hole_inner, fill=colors["accent"], outline="")

    def _format_eng_value(self, value: float | None, unit: str) -> str:
        if value is None:
            return f"-- {unit}".strip()
        prefixes = [(1e9, "G"), (1e6, "M"), (1e3, "k"), (1.0, ""), (1e-3, "m"), (1e-6, "μ"), (1e-9, "n"), (1e-12, "p")]
        magnitude = abs(float(value))
        scale, prefix = 1.0, ""
        for cand_scale, cand_prefix in prefixes:
            if magnitude >= cand_scale * 0.999 or cand_scale == 1e-12:
                scale, prefix = cand_scale, cand_prefix
                break
        scaled = float(value) / scale
        if abs(scaled) >= 100:
            digits = 2
        elif abs(scaled) >= 10:
            digits = 3
        else:
            digits = 4
        return f"{scaled:+0.{digits}f} {prefix}{unit}".strip()

    def _current_source_measure_labels(self) -> tuple[str, str, str]:
        config = getattr(self, "_live_config", None)
        if config is not None and config.mode is SweepMode.CURRENT_SOURCE:
            return "Isrc", "Vmeas", "V"
        if hasattr(self, "mode") and str(self.mode.get()) == SweepMode.CURRENT_SOURCE.value:
            return "Isrc", "Vmeas", "V"
        return "Vsrc", "Imeas", "A"

    def _refresh_live_measurement_status(self) -> None:
        src_label, meas_label, cmpl_unit = self._current_source_measure_labels()
        source_unit = "A" if src_label.startswith("I") else "V"
        measure_unit = "V" if meas_label.startswith("V") else "A"
        compliance_value = None
        try:
            compliance_value = float(self.compliance.get())
        except Exception:
            compliance_value = None
        text = (
            f"{src_label} {self._format_eng_value(getattr(self, '_last_source_value', None), source_unit)} · "
            f"{meas_label} {self._format_eng_value(getattr(self, '_last_measured_value', None), measure_unit)} · "
            f"Cmpl {self._format_eng_value(compliance_value, cmpl_unit)}"
        )
        if hasattr(self, "measurement_status_text"):
            self.measurement_status_text.set(text)
        self._refresh_front_panel_popup()

    def _reset_live_measurement_status(self) -> None:
        # After STOP/output-off, show the instrument display as zeroed rather
        # than leaving the last measured value on the status bar/front panel.
        self._last_source_value = 0.0
        self._last_measured_value = 0.0
        self._refresh_live_measurement_status()

    def _open_front_panel_popup(self, *, auto_open: bool = False) -> None:
        if getattr(self, "_front_panel_window", None) is not None:
            try:
                if self._front_panel_window.winfo_exists():
                    self._front_panel_window.deiconify(); self._front_panel_window.lift(); self._front_panel_auto_opened = bool(auto_open); self._refresh_front_panel_popup(); return
            except Exception:
                pass
        win = Toplevel(self.root)
        win.title("Keithley-style front panel")
        win.geometry("700x260")
        win.configure(background="#CFCFCB")
        self._front_panel_window = win
        self._front_panel_auto_opened = bool(auto_open)
        main = tk.Frame(win, bg="#CFCFCB", padx=12, pady=12)
        main.pack(fill="both", expand=True)
        display = tk.Frame(main, bg="#030507", highlightbackground="#5F666C", highlightthickness=2)
        display.pack(fill="x", pady=(0, 12))
        self._front_panel_main_value = tk.Label(display, text="+0.0000", fg="#BDEFE6", bg="#030507", font=("Courier New", 30, "bold"), anchor="w")
        self._front_panel_main_value.pack(fill="x", padx=12, pady=(10, 2))
        self._front_panel_sub_value = tk.Label(display, text="", fg="#BDEFE6", bg="#030507", font=("Courier New", 16), anchor="w")
        self._front_panel_sub_value.pack(fill="x", padx=12, pady=(0, 10))
        meta = ttk.Frame(main, style="Card.TFrame")
        meta.pack(fill="both", expand=True)
        self._front_panel_meta = ttk.Label(meta, text="", style="Card.TLabel", justify="left")
        self._front_panel_meta.pack(anchor="w", padx=6, pady=(0, 8))
        btns = ttk.Frame(main)
        btns.pack(fill="x")
        ttk.Button(btns, text="Close", command=self._close_front_panel_popup).pack(side="right")
        win.protocol("WM_DELETE_WINDOW", self._close_front_panel_popup)
        self._refresh_front_panel_popup()

    def _close_front_panel_popup(self) -> None:
        win = getattr(self, "_front_panel_window", None)
        self._front_panel_auto_opened = False
        if win is None:
            return
        try:
            if win.winfo_exists():
                win.destroy()
        except Exception:
            pass
        self._front_panel_window = None

    def _close_auto_front_panel_popup(self) -> None:
        if not getattr(self, "_front_panel_auto_opened", False):
            return
        self._close_front_panel_popup()

    def _refresh_front_panel_popup(self) -> None:
        win = getattr(self, "_front_panel_window", None)
        if win is None:
            return
        try:
            if not win.winfo_exists():
                self._front_panel_window = None
                return
        except Exception:
            self._front_panel_window = None
            return
        src_label, meas_label, cmpl_unit = self._current_source_measure_labels()
        source_unit = "A" if src_label.startswith("I") else "V"
        measure_unit = "V" if meas_label.startswith("V") else "A"
        compliance_value = None
        try:
            compliance_value = float(self.compliance.get())
        except Exception:
            pass
        main_value = self._format_eng_value(getattr(self, "_last_measured_value", None), measure_unit)
        sub_value = f"{src_label}:{self._format_eng_value(getattr(self, '_last_source_value', None), source_unit)}   Cmpl:{self._format_eng_value(compliance_value, cmpl_unit)}"
        self._front_panel_main_value.configure(text=main_value)
        self._front_panel_sub_value.configure(text=sub_value)
        try:
            terminal = self.terminal.get()
        except Exception:
            terminal = "--"
        try:
            model = self._detected_device_model()
        except Exception:
            model = "--"
        state = getattr(self, "_run_state", "idle")
        conn = self.status_connection_text.get() if hasattr(self, "status_connection_text") else "--"
        self._front_panel_meta.configure(text=(
            f"Model: {model}\n"
            f"Connection: {conn}\n"
            f"Run state: {state.title()}\n"
            f"Terminal: {terminal} · Sense: {getattr(self, 'sense_mode', None).get() if hasattr(self, 'sense_mode') else '--'}"
        ))

