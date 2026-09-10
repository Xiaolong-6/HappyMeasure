from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from keith_ivt.acquisition import FAST_BENCHMARK_NOTE, FAST_NPLC
from keith_ivt.models import SweepKind
from keith_ivt.ui.mixin_typing import UiMixinTyping
from keith_ivt.ui.widgets import ToolTip, add_tip


PROFILE_STANDARD = "Standard"
PROFILE_FAST = "Fast"
PROFILE_CUSTOM = "Custom"


class FastAcquisitionMixin(UiMixinTyping):
    """Constant-Time acquisition profile UI layered over SweepConfigMixin."""

    _ADVANCED_VAR_NAMES = (
        "zero_refresh_before_run",
        "autozero_during_run",
        "digital_filter",
        "digital_filter_count",
        "concurrent_measurement",
        "display_during_run",
        "measurement_only_read",
        "range_telemetry",
        "source_write_each_sample",
        "trigger_delay_s",
    )

    def _ensure_acquisition_vars(self) -> None:
        if hasattr(self, "acquisition_profile"):
            return
        self.acquisition_profile = tk.StringVar(master=self.root, value=PROFILE_STANDARD)
        self.acquisition_advanced_visible = tk.BooleanVar(master=self.root, value=False)
        self.zero_refresh_before_run = tk.BooleanVar(master=self.root, value=True)
        self.autozero_during_run = tk.BooleanVar(master=self.root, value=False)
        self.digital_filter = tk.BooleanVar(master=self.root, value=False)
        self.digital_filter_count = tk.IntVar(master=self.root, value=2)
        self.concurrent_measurement = tk.BooleanVar(master=self.root, value=False)
        self.display_during_run = tk.BooleanVar(master=self.root, value=True)
        self.measurement_only_read = tk.BooleanVar(master=self.root, value=True)
        self.range_telemetry = tk.BooleanVar(master=self.root, value=False)
        self.source_write_each_sample = tk.BooleanVar(master=self.root, value=False)
        self.trigger_delay_s = tk.DoubleVar(master=self.root, value=0.0)
        self._pre_fast_nplc: float | None = None
        self._pre_fast_delay_s: float | None = None
        self._custom_acquisition_snapshot: dict[str, object] | None = None
        self._last_acquisition_profile = PROFILE_STANDARD

    def _acquisition_profile_config_kwargs(self, sweep_kind: SweepKind) -> dict[str, Any]:
        self._ensure_acquisition_vars()
        profile = (
            self.acquisition_profile.get()
            if sweep_kind is SweepKind.CONSTANT_TIME
            else PROFILE_STANDARD
        )
        fast = profile == PROFILE_FAST
        custom = profile == PROFILE_CUSTOM
        return {
            "fast_acquisition": fast,
            "custom_acquisition": custom,
            "zero_refresh_before_run": bool(self.zero_refresh_before_run.get()),
            "autozero_during_run": bool(self.autozero_during_run.get()),
            "digital_filter": bool(self.digital_filter.get()),
            "digital_filter_count": int(self.digital_filter_count.get()),
            "concurrent_measurement": bool(self.concurrent_measurement.get()),
            "display_during_run": bool(self.display_during_run.get()),
            "measurement_only_read": bool(self.measurement_only_read.get()),
            "range_telemetry": bool(self.range_telemetry.get()),
            "source_write_each_sample": bool(self.source_write_each_sample.get()),
            "trigger_delay_s": float(self.trigger_delay_s.get()),
        }

    def _update_dynamic_sweep_fields(self) -> None:
        # Sibling SweepConfigMixin provides this at runtime via the MRO.
        super()._update_dynamic_sweep_fields()  # type: ignore[misc]
        if self.sweep_kind.get() != SweepKind.CONSTANT_TIME.value:
            self._restore_pre_fast_common_values()
            return
        self._ensure_acquisition_vars()
        self._build_fast_acquisition_controls()
        self._apply_acquisition_profile_state()

    def _build_fast_acquisition_controls(self) -> None:
        parent = self.dynamic_box
        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        frame.columnconfigure(1, weight=1)
        self.fast_acquisition_frame = frame

        ttk.Label(frame, text="Acquisition", style="Card.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=3
        )
        self.acquisition_profile_combo = ttk.Combobox(
            frame,
            textvariable=self.acquisition_profile,
            values=[PROFILE_STANDARD, PROFILE_FAST, PROFILE_CUSTOM],
            state="readonly",
        )
        self.acquisition_profile_combo.grid(row=0, column=1, sticky="ew", pady=3)
        self.acquisition_profile_combo.bind(
            "<<ComboboxSelected>>",
            lambda _e: self._on_acquisition_profile_changed(),
            add="+",
        )
        add_tip(
            self.acquisition_profile_combo,
            "Standard preserves the historical path. Fast applies the benchmark-backed "
            "host-query preset. Custom exposes individual acquisition controls.",
        )
        # The per-profile explanation lives on this affordance hover so the
        # panel stays compact instead of spreading a paragraph inline.
        self.acquisition_profile_help = ttk.Label(
            frame, text="?", style="Muted.TLabel", cursor="question_arrow"
        )
        self.acquisition_profile_help.grid(row=0, column=2, sticky="w", padx=(6, 0))
        self.acquisition_profile_tip = ToolTip(self.acquisition_profile_help, "")

        self.advanced_acquisition_button = ttk.Button(
            frame,
            text="Show advanced acquisition",
            style="Soft.TButton",
            command=self._toggle_advanced_acquisition,
        )
        self.advanced_acquisition_button.grid(
            row=1, column=0, columnspan=3, sticky="ew", pady=(3, 4)
        )

        advanced = ttk.Frame(frame, style="Card.TFrame", padding=(8, 6))
        advanced.columnconfigure(1, weight=1)
        self.advanced_acquisition_frame = advanced
        self._build_advanced_rows(advanced)
        if self.acquisition_advanced_visible.get():
            advanced.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(4, 0))

    def _build_advanced_rows(self, parent) -> None:
        ttk.Label(
            parent,
            text="Instrument / transfer settings",
            style="Card.TLabel",
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))

        self._advanced_widgets: list[object] = []

        def bool_row(row: int, label: str, var, recommended: str, tip: str) -> None:
            ttk.Label(parent, text=label, style="Card.TLabel").grid(
                row=row, column=0, sticky="w", padx=(0, 8), pady=2
            )
            widget = ttk.Checkbutton(parent, variable=var)
            widget.grid(row=row, column=1, sticky="w", pady=2)
            ttk.Label(parent, text=recommended, style="Muted.TLabel").grid(
                row=row, column=2, sticky="e", padx=(8, 0), pady=2
            )
            add_tip(widget, tip)
            self._advanced_widgets.append(widget)

        bool_row(
            1,
            "Zero refresh before run",
            self.zero_refresh_before_run,
            "Recommended: On",
            "Perform one zero refresh before high-rate acquisition.",
        )
        bool_row(
            2,
            "Auto zero during run",
            self.autozero_during_run,
            "Recommended: Off",
            "Auto zero costs throughput. Fast performs one refresh then disables it during the run.",
        )
        bool_row(
            3,
            "Digital filter",
            self.digital_filter,
            "Recommended: Off",
            "Keithley digital averaging increases point time. Leave off for maximum host-query rate.",
        )

        ttk.Label(parent, text="Filter count", style="Card.TLabel").grid(
            row=4, column=0, sticky="w", padx=(0, 8), pady=2
        )
        self.digital_filter_count_entry = ttk.Entry(
            parent, textvariable=self.digital_filter_count, width=8
        )
        self.digital_filter_count_entry.grid(row=4, column=1, sticky="ew", pady=2)
        ttk.Label(parent, text="Only when filter On", style="Muted.TLabel").grid(
            row=4, column=2, sticky="e", padx=(8, 0), pady=2
        )
        self._advanced_widgets.append(self.digital_filter_count_entry)

        bool_row(
            5,
            "Concurrent measurement",
            self.concurrent_measurement,
            "Recommended: Off",
            "Disable concurrent measurement for the leanest 2400/2401 measurement path.",
        )
        bool_row(
            6,
            "Instrument display",
            self.display_during_run,
            "Recommended: On",
            "The RS-232 host-loop benchmark showed no useful speed gain from disabling the display.",
        )
        bool_row(
            7,
            "Measurement-only read",
            self.measurement_only_read,
            "Recommended: On",
            "Return only the measured field during Constant Time. The fixed source is already known locally.",
        )
        bool_row(
            8,
            "Live range telemetry",
            self.range_telemetry,
            "Recommended: Off",
            "Per-sample AUTO? + RANGE? polling added about 28 ms in the tested 2401 / 57600 baud path.",
        )
        bool_row(
            9,
            "Source write each sample",
            self.source_write_each_sample,
            "Recommended: Off",
            "Constant Time normally sets the source once before sampling.",
        )

        ttk.Label(parent, text="Trigger delay (s)", style="Card.TLabel").grid(
            row=10, column=0, sticky="w", padx=(0, 8), pady=2
        )
        self.trigger_delay_entry = ttk.Entry(
            parent, textvariable=self.trigger_delay_s, width=8
        )
        self.trigger_delay_entry.grid(row=10, column=1, sticky="ew", pady=2)
        ttk.Label(parent, text="Recommended: 0", style="Muted.TLabel").grid(
            row=10, column=2, sticky="e", padx=(8, 0), pady=2
        )
        self._advanced_widgets.append(self.trigger_delay_entry)

        ttk.Separator(parent).grid(
            row=11, column=0, columnspan=3, sticky="ew", pady=(6, 5)
        )
        ttk.Label(
            parent,
            text=(
                "NPLC: 0.1 recommended · Software delay: 0 s recommended · "
                "Fixed measure range preferred for mapping. RS-232: 57600 baud "
                "recommended when supported; Fast never changes connection baud automatically."
            ),
            style="Muted.TLabel",
            wraplength=390,
            justify="left",
        ).grid(row=12, column=0, columnspan=3, sticky="ew")

    def _toggle_advanced_acquisition(self) -> None:
        visible = not bool(self.acquisition_advanced_visible.get())
        self.acquisition_advanced_visible.set(visible)
        frame = getattr(self, "advanced_acquisition_frame", None)
        if frame is not None and frame.winfo_exists():
            if visible:
                frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(4, 0))
            else:
                frame.grid_remove()
        button = getattr(self, "advanced_acquisition_button", None)
        if button is not None and button.winfo_exists():
            button.configure(
                text=(
                    "Hide advanced acquisition"
                    if visible
                    else "Show advanced acquisition"
                )
            )
        try:
            self._refresh_content_scrollregion_later()
        except Exception:
            pass

    def _on_acquisition_profile_changed(self) -> None:
        self._apply_acquisition_profile_state()
        self._update_point_count()

    def _advanced_snapshot(self) -> dict[str, object]:
        return {name: getattr(self, name).get() for name in self._ADVANCED_VAR_NAMES}

    def _restore_advanced_snapshot(self, values: dict[str, object] | None) -> None:
        if not values:
            return
        for name, value in values.items():
            var = getattr(self, name, None)
            if var is not None:
                var.set(value)

    def _set_fast_recommended_vars(self) -> None:
        self.zero_refresh_before_run.set(True)
        self.autozero_during_run.set(False)
        self.digital_filter.set(False)
        self.digital_filter_count.set(2)
        self.concurrent_measurement.set(False)
        self.display_during_run.set(True)
        self.measurement_only_read.set(True)
        self.range_telemetry.set(False)
        self.source_write_each_sample.set(False)
        self.trigger_delay_s.set(0.0)

    @staticmethod
    def _find_entry_for_var(parent, var):
        if parent is None:
            return None
        try:
            children = parent.winfo_children()
        except Exception:
            return None
        for child in children:
            if isinstance(child, ttk.Entry):
                try:
                    if str(child.cget("textvariable")) == str(var):
                        return child
                except Exception:
                    pass
            found = FastAcquisitionMixin._find_entry_for_var(child, var)
            if found is not None:
                return found
        return None

    def _common_entry_for_var(self, var):
        return self._find_entry_for_var(getattr(self, "common_box", None), var)

    def _time_entry_for_var(self, var):
        return self._find_entry_for_var(getattr(self, "dynamic_box", None), var)

    def _restore_pre_fast_common_values(self) -> None:
        if getattr(self, "_pre_fast_nplc", None) is not None:
            self.nplc.set(self._pre_fast_nplc)
            self._pre_fast_nplc = None
        if getattr(self, "_pre_fast_delay_s", None) is not None:
            self.delay_s.set(self._pre_fast_delay_s)
            self._pre_fast_delay_s = None
        for var in (getattr(self, "nplc", None), getattr(self, "delay_s", None)):
            if var is None:
                continue
            widget = self._common_entry_for_var(var)
            if widget is not None:
                widget.state(["!disabled"])

    def _apply_acquisition_profile_state(self) -> None:
        self._ensure_acquisition_vars()
        profile = self.acquisition_profile.get()
        previous = getattr(self, "_last_acquisition_profile", PROFILE_STANDARD)
        is_fast = profile == PROFILE_FAST
        is_custom = profile == PROFILE_CUSTOM

        if previous == PROFILE_CUSTOM and profile != PROFILE_CUSTOM:
            self._custom_acquisition_snapshot = self._advanced_snapshot()

        if is_fast:
            if self._pre_fast_nplc is None:
                self._pre_fast_nplc = float(self.nplc.get())
            if self._pre_fast_delay_s is None:
                self._pre_fast_delay_s = float(self.delay_s.get())
            self.nplc.set(FAST_NPLC)
            self.delay_s.set(0.0)
            self._set_fast_recommended_vars()
        else:
            self._restore_pre_fast_common_values()
            if is_custom and previous != PROFILE_CUSTOM:
                self._restore_advanced_snapshot(self._custom_acquisition_snapshot)

        nplc_entry = self._common_entry_for_var(self.nplc)
        delay_entry = self._common_entry_for_var(self.delay_s)
        interval_entry = self._time_entry_for_var(self.interval_s)
        for widget in (nplc_entry, delay_entry, interval_entry):
            if widget is not None:
                widget.state(["disabled"] if is_fast else ["!disabled"])

        for widget in getattr(self, "_advanced_widgets", []):
            try:
                widget.state(["!disabled"] if is_custom else ["disabled"])
            except Exception:
                try:
                    widget.configure(state="normal" if is_custom else "disabled")
                except Exception:
                    pass

        tip = getattr(self, "acquisition_profile_tip", None)
        if tip is not None:
            if is_fast:
                text = (
                    "Fast preset: sample as fast as the host/instrument path allows; "
                    "Interval, NPLC and software delay are preset/disabled. 0.1 NPLC, "
                    "one zero refresh, autozero/filter/concurrent/range telemetry Off, "
                    "measurement-only reads, zero delays. Measure range remains selectable. "
                    + FAST_BENCHMARK_NOTE
                )
            elif is_custom:
                text = (
                    "Custom acquisition: advanced controls are editable. Recommended values "
                    "are shown at right; actual speed depends on transport and hardware."
                )
            else:
                text = (
                    "Standard acquisition preserves historical HappyMeasure behavior. "
                    "Choose Fast for the benchmark-backed Constant-Time host-query preset."
                )
            tip.text = text

        self._last_acquisition_profile = profile
        try:
            self._refresh_content_scrollregion_later()
        except Exception:
            pass
