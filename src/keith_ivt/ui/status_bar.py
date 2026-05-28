from __future__ import annotations

import math
import tkinter as tk
from tkinter import Toplevel, ttk

from keith_ivt.core.current_range import current_range_labels, format_current_range, parse_current_range_label
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
            f"Irange {self._current_range_status_fragment()} · "
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

    def _current_range_snapshot(self):
        control = getattr(self, "_current_range_control", None)
        if control is None:
            return None
        try:
            return control.snapshot()
        except Exception:
            return None

    def _current_range_status_fragment(self) -> str:
        state = self._current_range_snapshot()
        if state is not None:
            return state.status_fragment()
        try:
            if bool(self.auto_measure_range.get()):
                return "Auto/Unknown"
        except Exception:
            return "Unknown"
        try:
            return f"Fixed/{format_current_range(float(self.measure_range.get()))}"
        except Exception:
            return "Fixed/Unknown"

    def _front_panel_autorange_changed(self) -> None:
        enabled = bool(self.auto_measure_range.get())
        control = getattr(self, "_current_range_control", None)
        if control is not None:
            control.request_autorange(enabled)
        self._refresh_live_measurement_status()

    def _front_panel_fixed_range_selected(self, _event=None) -> None:
        combo = getattr(self, "_front_panel_range_combo", None)
        value = parse_current_range_label(combo.get() if combo is not None else "")
        if value is None:
            return
        self.auto_measure_range.set(False)
        self.measure_range.set(value)
        control = getattr(self, "_current_range_control", None)
        if control is not None:
            control.request_fixed_range(value)
        self._refresh_live_measurement_status()

    def _front_panel_lock_current_range(self) -> None:
        state = self._current_range_snapshot()
        if state is not None and state.actual_range_A is not None:
            self.measure_range.set(state.actual_range_A)
        self.auto_measure_range.set(False)
        control = getattr(self, "_current_range_control", None)
        if control is not None:
            control.request_lock_current()
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
        win.geometry("760x430")
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
        meta.columnconfigure(0, weight=1)
        meta.columnconfigure(1, weight=2)
        self._front_panel_meta = ttk.Label(meta, text="", style="Card.TLabel", justify="left")
        self._front_panel_meta.grid(row=0, column=0, sticky="nw", padx=(6, 12), pady=(0, 8))
        range_box = ttk.LabelFrame(meta, text="Current range")
        range_box.grid(row=0, column=1, sticky="ew", padx=6, pady=(0, 8))
        for col in range(4):
            range_box.columnconfigure(col, weight=1)
        self._front_panel_range_headline = ttk.Label(range_box, text="", style="Card.TLabel")
        self._front_panel_range_headline.grid(row=0, column=0, columnspan=4, sticky="w", padx=6, pady=(4, 2))
        self._front_panel_range_detail = ttk.Label(range_box, text="", style="Card.TLabel")
        self._front_panel_range_detail.grid(row=1, column=0, columnspan=4, sticky="w", padx=6, pady=(0, 6))
        self._front_panel_autorange_check = ttk.Checkbutton(
            range_box,
            text="Auto current range",
            variable=self.auto_measure_range,
            command=self._front_panel_autorange_changed,
        )
        self._front_panel_autorange_check.grid(row=2, column=0, columnspan=2, sticky="w", padx=6, pady=4)
        self._front_panel_range_combo = ttk.Combobox(range_box, values=current_range_labels(), state="readonly", width=18)
        self._front_panel_range_combo.grid(row=2, column=2, sticky="ew", padx=6, pady=4)
        self._front_panel_range_combo.bind("<<ComboboxSelected>>", self._front_panel_fixed_range_selected)
        ttk.Button(range_box, text="Lock current range", command=self._front_panel_lock_current_range).grid(row=2, column=3, sticky="ew", padx=6, pady=4)
        ttk.Label(range_box, text="Range settle delay").grid(row=3, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(range_box, textvariable=self.range_settle_delay_ms, width=7).grid(row=3, column=1, sticky="w", padx=6, pady=4)
        ttk.Label(range_box, text="ms").grid(row=3, column=1, sticky="e", padx=6, pady=4)
        ttk.Label(range_box, text="Discard readings").grid(row=3, column=2, sticky="w", padx=6, pady=4)
        ttk.Entry(range_box, textvariable=self.discard_after_range_change, width=6).grid(row=3, column=3, sticky="w", padx=6, pady=4)
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

    def _refresh_front_panel_range_widgets(self) -> None:
        if not hasattr(self, "_front_panel_range_headline"):
            return
        range_state = self._current_range_snapshot()
        if range_state is not None:
            headline = range_state.headline()
            detail = (
                f"Autorange: {'ON' if range_state.autorange else 'OFF' if range_state.autorange is False else 'Unknown'}   "
                f"Actual range: {format_current_range(range_state.actual_range_A)}   "
                f"Last range change: {range_state.last_change_text()}"
            )
            if range_state.warning:
                detail += f"\nWarning: {range_state.warning}"
        else:
            headline = "Current range: Unknown"
            detail = "Autorange: Unknown   Actual range: Unknown   Last range change: none"
        self._front_panel_range_headline.configure(text=headline)
        self._front_panel_range_detail.configure(text=detail)
        try:
            fixed_value = float(self.measure_range.get())
        except Exception:
            fixed_value = range_state.fixed_range_A if range_state is not None else None
        label = next((item for item in current_range_labels() if fixed_value is not None and item.startswith(format_current_range(fixed_value))), "")
        if label:
            self._front_panel_range_combo.set(label)
        self._front_panel_range_combo.configure(state="disabled" if bool(self.auto_measure_range.get()) else "readonly")

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
        self._refresh_front_panel_range_widgets()
        self._front_panel_meta.configure(text=(
            f"Model: {model}\n"
            f"Connection: {conn}\n"
            f"Run state: {state.title()}\n"
            f"Terminal: {terminal} · Sense: {getattr(self, 'sense_mode', None).get() if hasattr(self, 'sense_mode') else '--'}"
        ))
