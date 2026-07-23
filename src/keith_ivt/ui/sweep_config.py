from __future__ import annotations

from tkinter import DoubleVar, messagebox
from tkinter import ttk

from keith_ivt.ui.widgets import add_tip

from keith_ivt.core.adaptive_logic import adaptive_values_from_logic
from keith_ivt.models import (
    SweepKind,
    SweepMode,
    estimate_point_seconds,
    make_constant_time_values,
    make_hysteresis_values,
    make_source_values,
)


from keith_ivt.ui.mixin_typing import UiMixinTyping


class SweepConfigMixin(UiMixinTyping):
    def _refresh_time_config(self, *_args) -> None:
        self._update_time_duration_state()
        self._update_point_count()

    def _mode_from_ui(self) -> SweepMode:
        value = str(self.mode.get()).strip()
        aliases = {
            SweepMode.VOLTAGE_SOURCE.value: SweepMode.VOLTAGE_SOURCE,
            SweepMode.CURRENT_SOURCE.value: SweepMode.CURRENT_SOURCE,
            "Voltage": SweepMode.VOLTAGE_SOURCE,
            "Voltage source": SweepMode.VOLTAGE_SOURCE,
            "V-source": SweepMode.VOLTAGE_SOURCE,
            "Current": SweepMode.CURRENT_SOURCE,
            "Current source": SweepMode.CURRENT_SOURCE,
            "I-source": SweepMode.CURRENT_SOURCE,
        }
        try:
            return aliases[value]
        except KeyError:
            return SweepMode(value)

    def _sweep_kind_from_ui(self) -> SweepKind:
        value = str(self.sweep_kind.get()).strip()
        aliases = {
            SweepKind.STEP.value: SweepKind.STEP,
            SweepKind.CONSTANT_TIME.value: SweepKind.CONSTANT_TIME,
            SweepKind.ADAPTIVE.value: SweepKind.ADAPTIVE,
            SweepKind.MANUAL_OUTPUT.value: SweepKind.MANUAL_OUTPUT,
            "Step": SweepKind.STEP,
            "Time": SweepKind.CONSTANT_TIME,
            "Constant time": SweepKind.CONSTANT_TIME,
            "Adaptive": SweepKind.ADAPTIVE,
            "Manual output": SweepKind.MANUAL_OUTPUT,
        }
        try:
            return aliases[value]
        except KeyError:
            return SweepKind(value)

    def _bind_variables(self) -> None:
        self.mode.trace_add("write", self._on_mode_changed)
        self.sweep_kind.trace_add("write", self._on_sweep_kind_changed)
        for var in [
            self.start,
            self.stop,
            self.step,
            self.constant_value,
            self.duration_s,
            self.interval_s,
            self.nplc,
            self.delay_s,
            self.adaptive_logic,
            self.adaptive_start,
            self.adaptive_stop,
            self.adaptive_step,
            self.debug_model,
        ]:
            var.trace_add("write", lambda *_: self._update_point_count())
        self.hysteresis.trace_add("write", lambda *_: self._update_point_count())
        self.constant_until_stop.trace_add("write", self._refresh_time_config)
        self.debug.trace_add("write", self._on_debug_changed)

    def _on_mode_changed(self, *_):
        new_value = self.mode.get()
        if new_value == self._last_mode_value:
            return
        if not self._confirm_clear_existing_data("changing source mode"):
            self.mode.set(self._last_mode_value)
            return
        self._last_mode_value = new_value
        self._apply_mode_safe_defaults(new_value)
        self._update_units_for_mode()
        self._update_dynamic_sweep_fields()
        self._update_point_count()

    def _on_sweep_kind_changed(self, *_):
        new_value = self.sweep_kind.get()
        if new_value == self._last_sweep_kind_value:
            return
        if not self._confirm_clear_existing_data("changing sweep type"):
            self.sweep_kind.set(self._last_sweep_kind_value)
            return
        self._last_sweep_kind_value = new_value
        self._apply_default_views_for_sweep_kind(new_value)
        self._update_dynamic_sweep_fields()
        self._update_hysteresis_state()
        self._update_point_count()

    def _confirm_clear_existing_data(self, reason: str) -> bool:
        if not self._datasets.all():
            return True
        answer = messagebox.askyesnocancel(
            "Save or clear existing data?",
            f"Existing device traces are present. Before {reason}, save or clear them.\n\nYes = Export Data, then clear\nNo = Clear without saving\nCancel = Do not change",
        )
        if answer is None:
            return False
        if answer is True:
            if not self.save_all_traces():
                return False
        self._datasets.clear()
        self._refresh_trace_list()
        self._redraw_all_plots()
        self.log_event(f"Existing traces cleared before {reason}.")
        return True

    def _apply_mode_safe_defaults(self, mode_value: str) -> None:
        """Apply unit-consistent debug-safe defaults when switching source mode.

        Without this, switching from voltage-source defaults (-1..1 V) to
        current-source keeps -1..1 A with a 0.01 V compliance, so a linear
        resistor looks flat because the simulated measurement correctly hits
        voltage compliance.  These defaults keep the first debug curve readable.
        """
        try:
            if mode_value == SweepMode.CURRENT_SOURCE.value:
                self.start.set(-1e-3)
                self.stop.set(1e-3)
                self.step.set(1e-4)
                self.constant_value.set(1e-4)
                self.compliance.set(10.0)
                if not self.auto_source_range.get():
                    self.source_range.set(max(float(self.source_range.get()), 1e-3))
                if not self.auto_measure_range.get():
                    self.measure_range.set(max(float(self.measure_range.get()), 10.0))
            else:
                self.start.set(-1.0)
                self.stop.set(1.0)
                self.step.set(0.1)
                self.constant_value.set(0.1)
                self.compliance.set(0.01)
                if not self.auto_source_range.get():
                    self.source_range.set(max(float(self.source_range.get()), 1.0))
                if not self.auto_measure_range.get():
                    self.measure_range.set(max(float(self.measure_range.get()), 0.01))
        except Exception:
            pass

    def _update_units_for_mode(self) -> None:
        if self.mode.get() == SweepMode.VOLTAGE_SOURCE.value:
            self.start_label.set("Start (V)")
            self.stop_label.set("Stop (V)")
            self.step_label.set("Step (V)")
            self.const_label.set("Const value (V)")
            self.compliance_label.set("Compliance (A)")
        else:
            self.start_label.set("Start (A)")
            self.stop_label.set("Stop (A)")
            self.step_label.set("Step (A)")
            self.const_label.set("Const value (A)")
            self.compliance_label.set("Compliance (V)")

    def _update_hysteresis_state(self) -> None:
        enabled_kind = self.sweep_kind.get() in {SweepKind.STEP.value, SweepKind.ADAPTIVE.value}
        if not enabled_kind:
            self.hysteresis.set(False)
        btn = getattr(self, "hysteresis_check", None)
        try:
            if btn and btn.winfo_exists():
                run_state = getattr(self, "_run_state", "idle")
                editable = bool(
                    getattr(self, "_connected", False)
                    and run_state in {"idle", "stopped", "completed", "aborted"}
                )
                btn.configure(state="normal" if enabled_kind and editable else "disabled")
        except Exception:
            self.hysteresis_check = None

    def _update_dynamic_sweep_fields(self) -> None:
        if not hasattr(self, "dynamic_box") or not self.dynamic_box.winfo_exists():
            return
        for child in self.dynamic_box.winfo_children():
            child.destroy()
        self.dynamic_box.columnconfigure(1, weight=1)
        kind = self.sweep_kind.get()
        try:
            self.dynamic_box.pack_configure(
                fill="both" if kind == SweepKind.ADAPTIVE.value else "x",
                expand=(kind == SweepKind.ADAPTIVE.value),
            )
        except Exception:
            pass
        if kind == SweepKind.STEP.value:
            self._entry(
                self.dynamic_box,
                self.start_label,
                self.start,
                0,
                "Sweep start value. Units follow Mode.",
            )
            self._entry(
                self.dynamic_box,
                self.stop_label,
                self.stop,
                1,
                "Sweep stop value. Units follow Mode.",
            )
            self._entry(
                self.dynamic_box,
                self.step_label,
                self.step,
                2,
                "Sweep step. Use negative step for decreasing sweep.",
            )
        elif kind == SweepKind.CONSTANT_TIME.value:
            self._entry(
                self.dynamic_box,
                self.const_label,
                self.constant_value,
                0,
                "Constant source value for time sweep.",
            )
            self.constant_until_stop_check = self._check(
                self.dynamic_box,
                "Constant until Stop",
                self.constant_until_stop,
                1,
                "Hold the source at the constant value and measure every interval until Stop is pressed.",
                command=self._refresh_time_config,
            )
            self.duration_row = self._entry(
                self.dynamic_box,
                "Duration (s)",
                self.duration_s,
                2,
                "Total duration for finite time sweep. Disabled for Constant until Stop.",
            )
            self._entry(
                self.dynamic_box,
                "Interval (s)",
                self.interval_s,
                3,
                "Sampling interval. Limited by NPLC integration time.",
            )
            self._update_time_duration_state()
        elif kind == SweepKind.ADAPTIVE.value:
            self._build_adaptive_segment_table(self.dynamic_box)
        self._update_hysteresis_state()
        self._update_point_count()
        try:
            self._refresh_content_scrollregion_later()
        except Exception:
            pass

    def _update_time_duration_state(self) -> None:
        pair = getattr(self, "duration_row", None)
        try:
            if pair and len(pair) > 1 and pair[1].winfo_exists():
                pair[1].configure(state="disabled" if self.constant_until_stop.get() else "normal")
        except Exception:
            self.duration_row = None

    def _adaptive_values_from_rows(self) -> list[float]:
        values: list[float] = []
        rows = self.adaptive_rows or [
            {"start": self.adaptive_start, "stop": self.adaptive_stop, "step": self.adaptive_step}
        ]
        for row in rows:
            start = float(row["start"].get())
            stop = float(row["stop"].get())
            step = float(row["step"].get())
            segment = make_source_values(start, stop, step)
            if values and segment and abs(values[-1] - segment[0]) < 1e-15:
                segment = segment[1:]
            values.extend(segment)
        if not values:
            raise ValueError("Adaptive table produced no source values.")
        return values

    def _make_adaptive_row(
        self, start: float = 0.0, stop: float = 1.0, step: float = 0.1
    ) -> dict[str, DoubleVar]:
        row = {
            "start": DoubleVar(value=start),
            "stop": DoubleVar(value=stop),
            "step": DoubleVar(value=step),
        }
        for var in row.values():
            var.trace_add("write", lambda *_: self._update_point_count())
        return row

    def _ensure_adaptive_rows(self) -> None:
        if not self.adaptive_rows:
            for start, stop, step in self.DEFAULT_ADAPTIVE_ROWS:
                self.adaptive_rows.append(self._make_adaptive_row(start, stop, step))

    def _build_adaptive_segment_table(self, parent) -> None:
        """Build a full adaptive segment table using the page scrollbar only."""
        self._ensure_adaptive_rows()
        parent.columnconfigure(0, weight=1)

        holder = ttk.Frame(parent, style="Card.TFrame")
        holder.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 4))
        holder.columnconfigure(0, weight=0, minsize=32)
        for c in range(1, 4):
            holder.columnconfigure(c, weight=1, uniform="adaptive_compact", minsize=72)

        ttk.Label(holder, text="#", style="Muted.TLabel").grid(
            row=0, column=0, sticky="w", padx=(8, 6), pady=(6, 3)
        )
        for c, title in enumerate(["Start", "Stop", "Step"], start=1):
            ttk.Label(holder, text=title, style="Muted.TLabel").grid(
                row=0, column=c, sticky="w", padx=3, pady=(6, 3)
            )

        for r, row in enumerate(self.adaptive_rows, start=1):
            ttk.Label(holder, text=str(r), style="Muted.TLabel").grid(
                row=r, column=0, sticky="w", padx=(8, 6), pady=2
            )
            for c, key in enumerate(["start", "stop", "step"], start=1):
                ent = ttk.Entry(holder, textvariable=row[key], width=8)
                ent.grid(row=r, column=c, sticky="ew", padx=3, pady=2)
                add_tip(ent, f"Adaptive segment {r}: {key} value.")

        btns = ttk.Frame(parent, style="ToolbarInner.TFrame")
        btns.grid(row=1, column=0, sticky="ew", padx=1, pady=(6, 0))
        for c in range(3):
            btns.columnconfigure(c, weight=1, uniform="adaptive_buttons")
        ttk.Button(btns, text="＋ Row", style="Soft.TButton", command=self._add_adaptive_row).grid(
            row=0, column=0, sticky="ew", padx=(0, 3)
        )
        ttk.Button(
            btns, text="－ Row", style="Soft.TButton", command=self._remove_adaptive_row
        ).grid(row=0, column=1, sticky="ew", padx=3)
        ttk.Button(
            btns, text="Reset", style="Soft.TButton", command=self._reset_adaptive_rows
        ).grid(row=0, column=2, sticky="ew", padx=(3, 0))

        note = ttk.Label(
            parent,
            text="Duplicate boundaries are removed automatically. Use negative step for decreasing ranges.",
            style="Muted.TLabel",
            wraplength=420,
            justify="left",
        )
        note.grid(row=2, column=0, sticky="ew", padx=3, pady=(6, 2))

        # Force geometry and canvas scrollregion to catch up after a mode switch.
        try:
            holder.update_idletasks()
            parent.update_idletasks()
            self._refresh_content_scrollregion_later()
        except Exception:
            pass

    def _add_adaptive_row(self) -> None:
        self._ensure_adaptive_rows()
        last = self.adaptive_rows[-1]
        start = float(last["stop"].get())
        step = float(last["step"].get())
        self._adaptive_advanced_active = False
        self.adaptive_rows.append(self._make_adaptive_row(start, start + step * 10, step))
        self._update_dynamic_sweep_fields()

    def _remove_adaptive_row(self) -> None:
        self._ensure_adaptive_rows()
        if len(self.adaptive_rows) > 1:
            self._adaptive_advanced_active = False
            self.adaptive_rows.pop()
        self._update_dynamic_sweep_fields()

    def _reset_adaptive_rows(self) -> None:
        self.adaptive_rows.clear()
        self._adaptive_advanced_active = False
        self._ensure_adaptive_rows()
        self._update_dynamic_sweep_fields()

    def _adaptive_logic_from_table(self) -> str:
        values = self._adaptive_values_from_rows()
        return "values = " + repr([float(v) for v in values])

    def _sync_adaptive_logic_text(self) -> None:
        if hasattr(self, "adaptive_text") and self.adaptive_text.winfo_exists():
            self.adaptive_logic.set(self.adaptive_text.get("1.0", "end").strip())
            self._adaptive_advanced_active = True
        elif not getattr(self, "_adaptive_advanced_active", False):
            self.adaptive_logic.set(self._adaptive_logic_from_table())

    def _open_adaptive_logic_dialog(self):
        messagebox.showinfo(
            "Adaptive table",
            "Advanced text mode was removed. Use the start / stop / step table so rows and generated values stay synchronized.",
        )

    def validate_adaptive_logic(self, use_existing_logic: bool = False) -> bool:
        if not use_existing_logic:
            self.adaptive_logic.set(self._adaptive_logic_from_table())
        try:
            values = adaptive_values_from_logic(self.adaptive_logic.get())
        except Exception as exc:
            messagebox.showerror("Adaptive sweep error", str(exc))
            self.log_event(f"Adaptive sweep validation failed: {exc}")
            return False
        messagebox.showinfo(
            "Adaptive sweep valid",
            f"Generated {len(values)} source values.\nFirst: {values[0]:.6g}\nLast: {values[-1]:.6g}",
        )
        self.log_event(f"Adaptive sweep validated: {len(values)} points.")
        self._update_point_count()
        return True

    def _update_range_state(self) -> None:
        pairs = (
            ("source_range_row", self.auto_source_range),
            ("measure_range_row", self.auto_measure_range),
        )
        busy = getattr(self, "_run_state", "idle") not in {
            "idle",
            "stopped",
            "completed",
            "aborted",
        }
        editable = bool(self._connected and not busy)
        for attr, auto_var in pairs:
            pair = getattr(self, attr, None)
            try:
                is_auto = bool(auto_var.get())
                if pair and len(pair) > 1 and pair[1].winfo_exists():
                    pair[1].configure(state="disabled" if (is_auto or not editable) else "normal")
                if pair and len(pair) > 2 and pair[2].winfo_exists():
                    pair[2].configure(state="normal" if editable else "disabled")
                    self._sync_toggle_button(pair[2], "Auto", auto_var)
            except Exception:
                setattr(self, attr, None)

    def _update_point_count(self) -> None:
        try:
            kind = self.sweep_kind.get()
            if kind == SweepKind.CONSTANT_TIME.value:
                if self.constant_until_stop.get():
                    values = [float(self.constant_value.get())]
                    per_point = estimate_point_seconds(
                        self.nplc.get(),
                        kind,
                        self.interval_s.get(),
                        self.delay_s.get(),
                        int(self.baud_rate.get()),
                    )
                    self.points_text.set(f"Points: continuous · Interval: {per_point:.2f}s")
                    self.controls_title_text.set(f"Controls (continuous, {per_point:.2f} s/pt)")
                    self._set_sweep_fields_state()
                    return
                values = make_constant_time_values(
                    self.constant_value.get(), self.duration_s.get(), self.interval_s.get()
                )
                per_point = estimate_point_seconds(
                    self.nplc.get(),
                    kind,
                    self.interval_s.get(),
                    self.delay_s.get(),
                    int(self.baud_rate.get()),
                )
            elif kind == SweepKind.ADAPTIVE.value:
                logic = (
                    self.adaptive_logic.get()
                    if getattr(self, "_adaptive_advanced_active", False)
                    else self._adaptive_logic_from_table()
                )
                values = adaptive_values_from_logic(logic)
                if self.hysteresis.get():
                    values = make_hysteresis_values(values)
                per_point = estimate_point_seconds(
                    self.nplc.get(), delay_s=self.delay_s.get(), baud_rate=int(self.baud_rate.get())
                )
            else:
                values = make_source_values(self.start.get(), self.stop.get(), self.step.get())
                if self.hysteresis.get():
                    values = make_hysteresis_values(values)
                per_point = estimate_point_seconds(
                    self.nplc.get(), delay_s=self.delay_s.get(), baud_rate=int(self.baud_rate.get())
                )
            total_s = len(values) * per_point
            self.points_text.set(f"Points: {len(values)} · Est: {total_s:.1f}s")
            self.controls_title_text.set(f"Controls ({len(values)} pts, {total_s:.1f} sec)")
        except Exception:
            self.points_text.set("Points: invalid · Est: --")
            self.controls_title_text.set("Controls (--)")
        self._set_sweep_fields_state()
