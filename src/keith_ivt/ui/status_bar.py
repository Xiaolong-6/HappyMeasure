from __future__ import annotations

import math
import tkinter as tk
from tkinter import Toplevel, ttk

from keith_ivt.core.current_range import (
    current_range_labels,
    format_current_range,
    parse_current_range_label,
)
from keith_ivt.models import SweepMode


from keith_ivt.ui.mixin_typing import UiMixinTyping


class StatusBarMixin(UiMixinTyping):
    """Dedicated bottom status bar builder for compact connection/run/live readout."""

    _front_panel_window: Toplevel | None
    _last_source_value: float | None
    _last_measured_value: float | None

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
        ttk.Label(conn, textvariable=self.status_connection_text, style="StatusCell.TLabel").grid(
            row=0, column=1, sticky="ew"
        )

        ttk.Label(self.status_bar, textvariable=self.status, style="StatusCell.TLabel").grid(
            row=0, column=1, sticky="ew", padx=(0, 8)
        )
        live = ttk.Label(
            self.status_bar, textvariable=self.measurement_status_text, style="StatusCell.TLabel"
        )
        live.grid(row=0, column=2, sticky="ew")
        live.bind("<Double-1>", lambda _e: self._open_front_panel_popup(auto_open=False))
        self.connection_light_canvas.bind(
            "<Double-1>", lambda _e: self._open_front_panel_popup(auto_open=False)
        )

    def _status_icon_size(self) -> int:
        try:
            size_pt = (
                int(self.ui_font_size.get())
                if hasattr(self, "ui_font_size")
                else int(getattr(self.settings, "ui_font_size", 10))
            )
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
            canvas.create_oval(
                margin,
                margin,
                icon_size - margin,
                icon_size - margin,
                fill=fill,
                outline=colors["border"],
                width=1,
            )
            canvas.create_oval(
                shine_margin,
                shine_margin,
                shine_margin + shine_size,
                shine_margin + shine_size,
                fill="#FFFFFF",
                outline="",
            )
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
        canvas.create_oval(
            cx - hole_outer,
            cy - hole_outer,
            cx + hole_outer,
            cy + hole_outer,
            fill=colors["bg"],
            outline=colors["border"],
            width=1,
        )
        canvas.create_oval(
            cx - hole_inner,
            cy - hole_inner,
            cx + hole_inner,
            cy + hole_inner,
            fill=colors["accent"],
            outline="",
        )

    def _format_eng_value(self, value: float | None, unit: str) -> str:
        if value is None:
            return f"-- {unit}".strip()
        prefixes = [
            (1e9, "G"),
            (1e6, "M"),
            (1e3, "k"),
            (1.0, ""),
            (1e-3, "m"),
            (1e-6, "μ"),
            (1e-9, "n"),
            (1e-12, "p"),
        ]
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
        # Live current-range control only applies to current measurement.
        # For voltage measure, the status bar should not claim Irange.
        try:
            live_cfg = getattr(self, "_live_config", None)
            if live_cfg is not None:
                if getattr(live_cfg, "measure_scpi", "CURR") != "CURR":
                    return "Vrange N/A"
            elif str(self.mode.get()) == SweepMode.CURRENT_SOURCE.value:
                return "Vrange N/A"
        except Exception:
            pass
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
        existing_window = getattr(self, "_front_panel_window", None)
        if existing_window is not None:
            try:
                if existing_window.winfo_exists():
                    existing_window.deiconify()
                    existing_window.lift()
                    self._front_panel_auto_opened = bool(auto_open)
                    self._refresh_front_panel_popup()
                    return
            except Exception:
                pass
        win = Toplevel(self.root)
        win.title("Keithley-style front panel")
        win.geometry("920x520")
        win.minsize(860, 470)
        panel_bg = "#EEF2F5"
        card_bg = "#FFFFFF"
        border = "#D7E1EA"
        muted = "#5F7083"
        win.configure(background=panel_bg)
        self._front_panel_window = win
        self._front_panel_auto_opened = bool(auto_open)

        main = tk.Frame(win, bg=panel_bg, padx=14, pady=14)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)

        display = tk.Frame(main, bg="#030507", highlightbackground="#31404B", highlightthickness=1)
        display.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        display.columnconfigure(0, weight=1)
        display.columnconfigure(1, weight=0)
        self._front_panel_main_value = tk.Label(
            display,
            text="+0.0000",
            fg="#BDEFE6",
            bg="#030507",
            font=("Courier New", 42, "bold"),
            anchor="w",
        )
        self._front_panel_main_value.grid(row=0, column=0, sticky="ew", padx=(26, 16), pady=(22, 0))
        indicators = tk.Frame(display, bg="#030507")
        indicators.grid(row=0, column=1, rowspan=2, sticky="ne", padx=(0, 24), pady=(26, 0))
        self._front_panel_output_indicator = tk.Label(
            indicators,
            text="● OUTPUT   ON",
            fg="#BDEFE6",
            bg="#030507",
            font=("Courier New", 12),
            anchor="e",
        )
        self._front_panel_output_indicator.grid(row=0, column=0, sticky="e")
        self._front_panel_measure_indicator = tk.Label(
            indicators,
            text="MEASURE   CURRENT",
            fg="#BDEFE6",
            bg="#030507",
            font=("Courier New", 12),
            anchor="e",
        )
        self._front_panel_measure_indicator.grid(row=1, column=0, sticky="e", pady=(12, 0))
        self._front_panel_sub_value = tk.Label(
            display,
            text="",
            fg="#BDEFE6",
            bg="#030507",
            font=("Courier New", 16),
            anchor="w",
        )
        self._front_panel_sub_value.grid(row=1, column=0, sticky="ew", padx=(26, 16), pady=(0, 18))

        body = tk.Frame(main, bg=card_bg, highlightbackground=border, highlightthickness=1)
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=0, minsize=280)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        meta_card = tk.Frame(body, bg=card_bg)
        meta_card.grid(row=0, column=0, sticky="nsew", padx=(14, 14), pady=14)
        meta_card.columnconfigure(0, weight=1)
        self._front_panel_meta = tk.Label(
            meta_card,
            text="",
            bg=card_bg,
            fg="#0F172A",
            justify="left",
            anchor="nw",
            font=("Segoe UI", 10),
        )
        self._front_panel_meta.grid(row=0, column=0, sticky="nw")

        range_card = tk.Frame(body, bg=card_bg)
        range_card.grid(row=0, column=1, sticky="nsew", padx=(0, 14), pady=14)
        range_card.columnconfigure(0, weight=1)
        tk.Label(
            range_card,
            text="Current range",
            bg=card_bg,
            fg="#0F172A",
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 10))

        summary = tk.Frame(range_card, bg=card_bg)
        summary.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        for col in range(4):
            summary.columnconfigure(col, weight=1, uniform="range_summary")

        range_title_widgets: list[tk.Label] = []
        range_value_widgets: list[tk.Label] = []
        for col, title in enumerate(
            ("Autorange", "Actual range", "Range menu", "Last range change")
        ):
            cell = tk.Frame(
                summary,
                bg="#F8FAFC",
                highlightbackground=border,
                highlightthickness=1,
                padx=10,
                pady=8,
            )
            cell.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 8, 0))
            cell.columnconfigure(0, weight=1)
            title_label = tk.Label(
                cell, text=title, bg="#F8FAFC", fg=muted, font=("Segoe UI", 9), anchor="center"
            )
            title_label.grid(row=0, column=0, sticky="ew")
            range_title_widgets.append(title_label)
            value = tk.Label(
                cell,
                text="Unknown",
                bg="#F8FAFC",
                fg="#165FA7",
                font=("Segoe UI", 14),
                anchor="center",
            )
            value.grid(row=1, column=0, sticky="ew", pady=(3, 0))
            range_value_widgets.append(value)
        self._front_panel_range_mode_value = range_value_widgets[0]
        self._front_panel_range_actual_value = range_value_widgets[1]
        self._front_panel_range_menu_value = range_value_widgets[2]
        self._front_panel_range_change_value = range_value_widgets[3]
        self._front_panel_range_actual_title = range_title_widgets[1]
        self._front_panel_range_change_title = range_title_widgets[3]

        controls = tk.Frame(range_card, bg=card_bg)
        controls.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        controls.columnconfigure(1, weight=1)

        self._front_panel_autorange_check = ttk.Checkbutton(
            controls,
            text="Auto current range",
            variable=self.auto_measure_range,
            command=self._front_panel_autorange_changed,
        )
        self._front_panel_autorange_check.grid(row=0, column=0, sticky="w", padx=(0, 18))

        self._front_panel_range_combo = ttk.Combobox(
            controls, values=current_range_labels(), state="readonly", width=22
        )
        self._front_panel_range_combo.grid(row=0, column=1, sticky="ew", padx=(0, 12))
        self._front_panel_range_combo.bind(
            "<<ComboboxSelected>>", self._front_panel_fixed_range_selected
        )

        self._front_panel_lock_btn = ttk.Button(
            controls,
            text="Lock current range",
            command=self._front_panel_lock_current_range,
        )
        self._front_panel_lock_btn.grid(row=0, column=2, sticky="ew")

        settle = tk.Frame(
            range_card,
            bg="#F8FAFC",
            highlightbackground=border,
            highlightthickness=1,
            padx=10,
            pady=9,
        )
        settle.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        settle.columnconfigure(8, weight=1)
        tk.Label(
            settle, text="After range change", bg="#F8FAFC", fg=muted, font=("Segoe UI", 9)
        ).grid(row=0, column=0, sticky="w", padx=(0, 16))
        tk.Label(
            settle, text="Range settle delay", bg="#F8FAFC", fg="#0F172A", font=("Segoe UI", 9)
        ).grid(row=0, column=1, sticky="w")
        settle_delay_entry = ttk.Entry(settle, textvariable=self.range_settle_delay_ms, width=7)
        settle_delay_entry.grid(row=0, column=2, sticky="w", padx=(6, 4))
        self._bind_numeric_entry_fallback(settle_delay_entry, self.range_settle_delay_ms)
        tk.Label(settle, text="ms", bg="#F8FAFC", fg="#0F172A", font=("Segoe UI", 9)).grid(
            row=0, column=3, sticky="w", padx=(0, 18)
        )
        tk.Label(settle, text="Discard", bg="#F8FAFC", fg="#0F172A", font=("Segoe UI", 9)).grid(
            row=0, column=4, sticky="w"
        )
        discard_entry = ttk.Entry(settle, textvariable=self.discard_after_range_change, width=7)
        discard_entry.grid(row=0, column=5, sticky="w", padx=(6, 4))
        self._bind_numeric_entry_fallback(discard_entry, self.discard_after_range_change)
        tk.Label(settle, text="readings", bg="#F8FAFC", fg="#0F172A", font=("Segoe UI", 9)).grid(
            row=0, column=6, sticky="w"
        )

        self._front_panel_range_warning = tk.Label(
            range_card,
            text="",
            bg="#F3F7FA",
            fg=muted,
            anchor="w",
            justify="left",
            font=("Segoe UI", 9),
            padx=8,
            pady=5,
        )
        self._front_panel_range_warning.grid(row=4, column=0, sticky="ew")

        btns = tk.Frame(main, bg=panel_bg)
        btns.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(btns, text="Close", command=self._close_front_panel_popup).pack(
            side="right", ipadx=14
        )
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
        if not hasattr(self, "_front_panel_range_mode_value"):
            return
        # Voltage-measure mode has no live current-range control.
        try:
            live_cfg = getattr(self, "_live_config", None)
            if live_cfg is not None:
                if getattr(live_cfg, "measure_scpi", "CURR") != "CURR":
                    self._front_panel_range_mode_value.configure(text="N/A")
                    self._front_panel_range_actual_value.configure(text="N/A")
                    if hasattr(self, "_front_panel_range_warning"):
                        self._front_panel_range_warning.configure(
                            text="Live current-range control unavailable in voltage-measure mode."
                        )
                    if hasattr(self, "_front_panel_lock_btn"):
                        try:
                            self._front_panel_lock_btn.configure(state="disabled")
                        except Exception:
                            pass
                    return
            elif str(self.mode.get()) == SweepMode.CURRENT_SOURCE.value:
                self._front_panel_range_mode_value.configure(text="N/A")
                self._front_panel_range_actual_value.configure(text="N/A")
                if hasattr(self, "_front_panel_range_warning"):
                    self._front_panel_range_warning.configure(
                        text="Voltage range configured; live current-range control unavailable."
                    )
                return
        except Exception:
            pass
        range_state = self._current_range_snapshot()
        telemetry_enabled = bool(getattr(self, "range_telemetry", self.auto_measure_range).get())
        if range_state is not None:
            mode = (
                "AUTO"
                if range_state.autorange is True
                else "FIXED" if range_state.autorange is False else "UNKNOWN"
            )
            actual = format_current_range(range_state.actual_range_A)
            change = range_state.last_change_text() if telemetry_enabled else "Not monitored"
            warning = f"Warning: {range_state.warning}" if range_state.warning else ""
        else:
            mode = "UNKNOWN"
            actual = "Unknown"
            change = "Not monitored" if not telemetry_enabled else "none"
            warning = ""
        self._front_panel_range_mode_value.configure(
            text="ON" if mode == "AUTO" else "OFF" if mode == "FIXED" else "Unknown"
        )
        self._front_panel_range_actual_value.configure(text=actual)
        if hasattr(self, "_front_panel_range_actual_title"):
            self._front_panel_range_actual_title.configure(
                text="Actual range" if telemetry_enabled else "Range snapshot"
            )
        if hasattr(self, "_front_panel_range_change_title"):
            self._front_panel_range_change_title.configure(text="Last range change")
        if hasattr(self, "_front_panel_range_menu_value"):
            self._front_panel_range_menu_value.configure(text="Auto" if mode == "AUTO" else actual)
        self._front_panel_range_change_value.configure(text=change)
        if hasattr(self, "_front_panel_range_warning"):
            if warning:
                self._front_panel_range_warning.configure(text=warning)
            elif mode == "AUTO":
                self._front_panel_range_warning.configure(
                    text="Autorange may switch range during I-t acquisition; lock range for final data."
                )
            else:
                self._front_panel_range_warning.configure(
                    text="Fixed range is active; readings remain continuous unless overload occurs."
                )
        # Fast Auto with telemetry off: snapshot may be stale, so lock is unsafe.
        if hasattr(self, "_front_panel_lock_btn"):
            try:
                if not telemetry_enabled and mode == "AUTO":
                    self._front_panel_lock_btn.configure(state="disabled")
                    if hasattr(self, "_front_panel_range_warning"):
                        self._front_panel_range_warning.configure(
                            text="Live autorange transitions are not monitored in Fast. Select a fixed measurement range before the run for quantitative work."
                        )
                else:
                    # Re-enable when not in the Fast Auto case; the top-level
                    # voltage-measure early return already handled that branch.
                    self._front_panel_lock_btn.configure(state="normal")
            except Exception:
                pass
        try:
            fixed_value = float(self.measure_range.get())
        except Exception:
            fixed_value = None
        if (
            bool(self.auto_measure_range.get())
            and range_state is not None
            and range_state.actual_range_A is not None
        ):
            fixed_value = range_state.actual_range_A
        elif fixed_value is None and range_state is not None:
            fixed_value = range_state.fixed_range_A or range_state.actual_range_A
        label = next(
            (
                item
                for item in current_range_labels()
                if fixed_value is not None and item.startswith(format_current_range(fixed_value))
            ),
            "",
        )
        if label:
            self._front_panel_range_combo.set(label)
        self._front_panel_range_combo.configure(
            state="disabled" if bool(self.auto_measure_range.get()) else "readonly"
        )

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
        main_value = self._format_eng_value(
            getattr(self, "_last_measured_value", None), measure_unit
        )
        sub_value = f"{src_label}:{self._format_eng_value(getattr(self, '_last_source_value', None), source_unit)}   Cmpl:{self._format_eng_value(compliance_value, cmpl_unit)}"
        self._front_panel_main_value.configure(text=main_value)
        self._front_panel_sub_value.configure(text=sub_value)
        self._front_panel_measure_indicator.configure(text=f"MEASURE   {meas_label}")
        try:
            terminal = self.terminal.get()
        except Exception:
            terminal = "--"
        try:
            model = self._detected_device_model()
        except Exception:
            model = "--"
        state = getattr(self, "_run_state", "idle")
        conn = (
            self.status_connection_text.get() if hasattr(self, "status_connection_text") else "--"
        )
        sense_var = getattr(self, "sense_mode", None)
        sense_text = sense_var.get() if sense_var is not None else "--"
        self._refresh_front_panel_range_widgets()
        self._front_panel_meta.configure(
            text=(
                f"Model: {model}\n"
                f"Connection: {conn}\n"
                f"Run state: {state.title()}\n"
                f"Terminal: {terminal} · Sense: {sense_text}"
            )
        )
