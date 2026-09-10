from __future__ import annotations

import math
from pathlib import Path
from tkinter import BooleanVar, StringVar, IntVar, END, messagebox, simpledialog
from tkinter import ttk

from keith_ivt.data.presets import (
    PRESET_SCHEMA_VERSION,
    clean_acquisition_state,
    default_acquisition_state,
    delete_preset,
    load_presets,
    normalize_preset,
    save_preset,
)
from keith_ivt.data.settings import AppSettings, load_settings, save_settings
from keith_ivt.instrument.simulator import debug_model_names


from keith_ivt.ui.mixin_typing import UiMixinTyping


class SettingsPresetMixin(UiMixinTyping):
    def _current_settings(self) -> AppSettings:
        self._restore_all_numeric_entry_defaults()
        return AppSettings(
            log_max_bytes=int(self.log_max_kb.get()) * 1024,
            default_mode=self.mode.get(),
            default_start=float(self.start.get()),
            default_stop=float(self.stop.get()),
            default_step=float(self.step.get()),
            default_compliance=float(self.compliance.get()),
            default_nplc=float(self.nplc.get()),
            default_delay_s=float(self.delay_s.get()),
            default_port=self.port.get(),
            default_baud_rate=int(self.baud_rate.get()),
            default_terminal=self._terminal_scpi(self.terminal.get()),
            default_sense_mode=self._sense_scpi(self.sense_mode.get()),
            default_debug=bool(self.debug.get()),
            default_debug_model=self.debug_model.get(),
            default_device_name=self.device_name.get(),
            default_operator=self.operator.get(),
            default_plot_layout=self.arrangement.get(),
            cache_enabled=bool(self.cache_enabled.get()),
            cache_interval_points=int(self.cache_interval_points.get()),
            default_autorange=bool(self.auto_source_range.get() and self.auto_measure_range.get()),
            auto_source_range=bool(self.auto_source_range.get()),
            auto_measure_range=bool(self.auto_measure_range.get()),
            default_source_range=float(self.source_range.get()),
            default_measure_range=float(self.measure_range.get()),
            default_sweep_kind=self.sweep_kind.get(),
            default_constant_value=float(self.constant_value.get()),
            default_duration_s=float(self.duration_s.get()),
            default_constant_until_stop=bool(self.constant_until_stop.get()),
            default_interval_s=float(self.interval_s.get()),
            default_adaptive_logic=(
                self._adaptive_logic_from_table()
                if self._adaptive_segment_text().strip()
                else self.adaptive_logic.get()
            ),
            default_adaptive_segments=self._adaptive_segment_text(),
            default_adaptive_remove_duplicates=bool(self.adaptive_remove_duplicates.get()),
            ui_font_family=self.ui_font_family.get(),
            ui_font_size=int(self.ui_font_size.get()),
            ui_theme=self.ui_theme.get(),
            show_front_panel_on_start=bool(self.show_front_panel_on_start.get()),
        )

    def _review_dict_dialog(
        self, title: str, fields: dict, choices: dict | None = None
    ) -> dict | None:
        """Review and edit settings dialog with categorized sections and themed styling."""
        import tkinter as tk

        # Create themed Toplevel window
        win = tk.Toplevel(self.root)
        win.title(title)
        win.transient(self.root)
        win.grab_set()

        # Apply current UI font settings for consistency
        ui_font = (
            getattr(self, "ui_font_family", StringVar(value="Verdana")).get()
            if hasattr(self, "ui_font_family")
            else "Verdana"
        )
        ui_size = (
            int(getattr(self, "ui_font_size", IntVar(value=10)).get())
            if hasattr(self, "ui_font_size")
            else 10
        )

        # Main container with padding
        main_frame = ttk.Frame(win, padding=(16, 12))
        main_frame.pack(fill="both", expand=True)

        # Buttons at top (compact, single row)
        btns = ttk.Frame(main_frame)
        btns.pack(fill="x", pady=(0, 8))

        result = {"data": None}

        def convert(raw: str, typ):
            if typ is bool:
                return raw.strip().lower() in {"1", "true", "yes", "y", "on"}
            if typ is int:
                return int(float(raw))
            if typ is float:
                return float(raw)
            return raw

        def restore_numeric_dialog_value(var, typ, fallback: str) -> None:
            try:
                value = convert(var.get(), typ)
                if not math.isfinite(float(value)):
                    raise ValueError("numeric value must be finite")
            except Exception:
                var.set(fallback)

        def numeric_focusout_handler(var, typ, fallback: str):
            def restore(_event) -> None:
                restore_numeric_dialog_value(var, typ, fallback)

            return restore

        def save():
            data = {}
            for key, (var, typ) in vars_by_key.items():
                if checks[key].get():
                    try:
                        data[key] = convert(var.get(), typ)
                    except Exception:
                        pass  # Skip invalid values
            result["data"] = data
            win.destroy()

        def factory_value_for(key: str):
            defaults = AppSettings()
            if key == "log_max_kb":
                return max(1, int((defaults.log_max_bytes + 1023) // 1024))
            return getattr(defaults, key, fields.get(key, ""))

        def restore_factory_fields() -> None:
            if not messagebox.askyesno(
                "Restore factory settings",
                "Restore all values in this dialog to the built-in factory defaults?\n\nNothing is saved until you click Save Selected.",
                parent=win,
            ):
                return
            for key, (var, typ) in vars_by_key.items():
                value = factory_value_for(key)
                if typ is bool:
                    var.set("Yes" if bool(value) else "No")
                else:
                    var.set(str(value))
                try:
                    checks[key].set(True)
                except Exception:
                    pass

        ttk.Button(btns, text="Save Selected", command=save).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Restore factory settings", command=restore_factory_fields).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side="left")

        # Separator
        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=(0, 8))

        # Scrollable canvas for settings
        canvas = tk.Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Bind mouse wheel only inside this dialog. A global bind_all callback can
        # survive dialog close and try to scroll a destroyed canvas.
        def _on_mousewheel(event):
            try:
                if not win.winfo_exists() or not canvas.winfo_exists():
                    return "break"
                if getattr(event, "num", None) == 4:
                    canvas.yview_scroll(-1, "units")
                elif getattr(event, "num", None) == 5:
                    canvas.yview_scroll(1, "units")
                else:
                    delta = getattr(event, "delta", 0)
                    if delta:
                        canvas.yview_scroll(int(-1 * (delta / 120)), "units")
                return "break"
            except Exception:
                return "break"

        def _bind_dialog_mousewheel(widget):
            widget.bind("<MouseWheel>", _on_mousewheel, add="+")
            widget.bind("<Button-4>", _on_mousewheel, add="+")
            widget.bind("<Button-5>", _on_mousewheel, add="+")

        vars_by_key = {}
        checks = {}
        choices = choices or {}

        # Group fields by category
        categories = self._categorize_settings(fields)

        row_offset = 0
        for category, cat_fields in categories.items():
            # Category header
            cat_label = ttk.Label(
                scroll_frame, text=category, style="Card.TLabel", font=(ui_font, ui_size, "bold")
            )
            cat_label.grid(
                row=row_offset, column=0, columnspan=3, sticky="w", pady=(12, 6), padx=(4, 0)
            )
            row_offset += 1

            # Fields in this category
            for key, value in cat_fields.items():
                checks[key] = BooleanVar(value=True)

                # Checkbox
                ttk.Checkbutton(scroll_frame, variable=checks[key]).grid(
                    row=row_offset, column=0, sticky="w", padx=(8, 4), pady=2
                )

                # Label with friendly name
                friendly_name = self._get_friendly_label(key)
                ttk.Label(scroll_frame, text=friendly_name, style="Card.TLabel").grid(
                    row=row_offset, column=1, sticky="w", padx=4, pady=2
                )

                # Value widget
                widget: ttk.Widget
                if isinstance(value, bool):
                    vals = ["Yes", "No"]
                    var = StringVar(value="Yes" if value else "No")
                    widget = ttk.Combobox(
                        scroll_frame, textvariable=var, values=vals, state="readonly", width=28
                    )
                elif key in choices:
                    var = StringVar(value=str(value))
                    widget = ttk.Combobox(
                        scroll_frame,
                        textvariable=var,
                        values=list(choices[key]),
                        state="readonly",
                        width=28,
                    )
                else:
                    var = StringVar(value=str(value))
                    widget = ttk.Entry(scroll_frame, textvariable=var, width=30)

                widget.grid(row=row_offset, column=2, sticky="ew", padx=(4, 8), pady=2)
                if type(value) in {int, float} and isinstance(widget, ttk.Entry):
                    widget.bind(
                        "<FocusOut>",
                        numeric_focusout_handler(var, type(value), str(value)),
                        add="+",
                    )
                _bind_dialog_mousewheel(widget)
                vars_by_key[key] = (var, type(value))
                row_offset += 1

        scroll_frame.columnconfigure(2, weight=1)

        # Pack canvas and scrollbar
        _bind_dialog_mousewheel(canvas)
        _bind_dialog_mousewheel(scroll_frame)
        canvas.pack(side="left", fill="both", expand=True, padx=(0, 4))
        scrollbar.pack(side="right", fill="y")

        # Set reasonable max height
        win.update_idletasks()
        max_height = min(win.winfo_screenheight() * 0.7, 600)
        win.geometry(f"600x{int(max_height)}")

        # Center the window
        win.update_idletasks()
        x = (win.winfo_screenwidth() // 2) - (600 // 2)
        y = (win.winfo_screenheight() // 2) - (int(max_height) // 2)
        win.geometry(f"+{x}+{y}")

        self.root.wait_window(win)
        return result["data"]

    def _categorize_settings(self, fields: dict) -> dict[str, dict]:
        """Group settings into logical categories (excluding sweep presets)."""
        categories: dict[str, dict[str, object]] = {
            "Logging & Cache": {},
            "Hardware Connection": {},
            "Plot & Display": {},
            "UI Appearance": {},
            "Debug Settings": {},
        }

        # Categorize each field
        for key, value in fields.items():
            if key in ("log_max_kb", "cache_enabled", "cache_interval_points"):
                categories["Logging & Cache"][key] = value
            elif key in (
                "default_port",
                "default_baud_rate",
                "default_terminal",
                "default_sense_mode",
            ):
                categories["Hardware Connection"][key] = value
            elif key in ("default_plot_layout",):
                categories["Plot & Display"][key] = value
            elif key in ("ui_font_family", "ui_font_size", "ui_theme", "show_front_panel_on_start"):
                categories["UI Appearance"][key] = value
            elif key in ("default_debug", "default_debug_model"):
                categories["Debug Settings"][key] = value
            else:
                # Put uncategorized in Logging & Cache as fallback
                categories["Logging & Cache"][key] = value

        # Remove empty categories
        return {k: v for k, v in categories.items() if v}

    def _get_friendly_label(self, key: str) -> str:
        """Convert internal setting keys to user-friendly labels."""
        label_map = {
            "log_max_kb": "Log Max KB",
            "cache_enabled": "Enable Cache",
            "cache_interval_points": "Cache Interval",
            "default_debug": "Debug Mode",
            "default_debug_model": "Debug Model",
            "default_port": "COM Port",
            "default_baud_rate": "Baud Rate",
            "default_terminal": "Terminal",
            "default_sense_mode": "Sense Mode",
            "default_plot_layout": "Plot Layout",
            "ui_font_family": "UI Font",
            "ui_font_size": "Font Size",
            "ui_theme": "Theme",
            "show_front_panel_on_start": "Auto-open Front Panel on Start",
            "check_updates_on_startup": "Check Updates on Startup",
            "default_mode": "Source Mode",
            "default_start": "Start",
            "default_stop": "Stop",
            "default_step": "Step",
            "default_compliance": "Compliance",
            "default_nplc": "NPLC",
            "default_delay_s": "Delay (s)",
            "default_sweep_kind": "Sweep Type",
            "default_constant_value": "Constant Value",
            "default_duration_s": "Duration (s)",
            "default_interval_s": "Interval (s)",
            "auto_source_range": "Auto Source Range",
            "auto_measure_range": "Auto Measure Range",
            "default_source_range": "Source Range",
            "default_measure_range": "Measure Range",
            "default_adaptive_segments": "Adaptive Segments",
            "default_adaptive_remove_duplicates": "Remove Duplicate Values",
        }
        return label_map.get(key, key.replace("_", " ").title())

    def review_and_save_settings(self):
        """Open a categorized dialog to review and save default settings (excluding sweep presets)."""
        settings = self._current_settings()

        # Only include non-sweep settings (sweep settings are managed by Presets)
        fields = {
            # Logging & Cache
            "log_max_kb": max(10, int((settings.log_max_bytes + 1023) // 1024)),
            "cache_enabled": settings.cache_enabled,
            "cache_interval_points": settings.cache_interval_points,
            # Hardware Connection Defaults
            "default_port": settings.default_port,
            "default_baud_rate": settings.default_baud_rate,
            "default_terminal": settings.default_terminal,
            "default_sense_mode": settings.default_sense_mode,
            # Plot & Display
            "default_plot_layout": settings.default_plot_layout,
            # UI Appearance
            "ui_font_family": settings.ui_font_family,
            "ui_font_size": settings.ui_font_size,
            "ui_theme": settings.ui_theme,
            "show_front_panel_on_start": settings.show_front_panel_on_start,
            "check_updates_on_startup": settings.check_updates_on_startup,
            # Debug Settings
            "default_debug": settings.default_debug,
            "default_debug_model": settings.default_debug_model,
        }

        chosen = self._review_dict_dialog(
            "Default Settings",
            fields,
            choices={
                "default_terminal": ["FRON", "REAR"],
                "default_sense_mode": ["2W", "4W"],
                "default_plot_layout": ["Auto", "Horizontal", "Vertical"],
                "ui_font_family": (
                    self._available_ui_fonts()
                    if hasattr(self, "_available_ui_fonts")
                    else ["Verdana"]
                ),
                "ui_theme": ["Light", "Dark", "Debug"],
                "default_debug_model": debug_model_names(),
            },
        )
        if chosen is None:
            return
        current = load_settings()
        data = current.__dict__.copy()
        chosen = dict(chosen)
        if "log_max_kb" in chosen:
            try:
                chosen["log_max_bytes"] = int(float(chosen.pop("log_max_kb"))) * 1024
            except Exception:
                chosen.pop("log_max_kb", None)
        data.update(chosen)
        path = save_settings(AppSettings(**data))
        self._apply_saved_settings_feedback(data, chosen, path)

    def _apply_saved_settings_feedback(self, data: dict, chosen: dict, path: Path) -> None:
        """Apply non-destructive settings feedback after a review-save action.

        Keep live Tk variables synchronized with the saved settings.  The
        review dialog returns plain Python values, but the running UI still
        reads BooleanVar/StringVar objects such as show_front_panel_on_start
        when Start is pressed.  Without this explicit sync, a user could save
        Auto-open Front Panel on Start = No and still get one more auto-popup
        until the next application restart.
        """
        from keith_ivt.data.settings import sanitize_settings_dict

        sanitized = sanitize_settings_dict(data)
        self.app_log.set_max_bytes(int(sanitized.get("log_max_bytes", self.app_log.max_bytes)))
        self._apply_settings_dict(sanitized)
        self.settings = AppSettings(**sanitized)
        self._init_style()
        self._refresh_instrument_indicator()
        self.log_event(f"Settings saved: {path}; keys={', '.join(sorted(chosen))}")
        messagebox.showinfo("Settings saved", "Saved settings:\n" + "\n".join(sorted(chosen)))

    def refresh_preset_list(self):
        if not hasattr(self, "preset_list"):
            return
        self.preset_list.delete(*self.preset_list.get_children())
        for name in sorted(load_presets().keys(), key=lambda n: (n != "Default", n.lower())):
            self.preset_list.insert("", END, values=(name,))

    def _fast_preset_review(self, name: str, data: dict) -> dict | None:
        """Review the exact Hardware + visible Sweep snapshot before saving."""
        hardware = data["hardware"]
        sweep = data["sweep"]
        parameters = sweep["parameters"]

        def display(value) -> str:
            return "Yes" if value is True else "No" if value is False else str(value)

        lines = [
            "[Hardware]",
            f"COM port: {display(hardware['port'])}",
            f"Baud: {display(hardware['baud_rate'])}",
            f"Terminal: {display(hardware['terminal'])}",
            f"Sense: {display(hardware['sense_mode'])}",
            "",
            "[Sweep]",
            f"Mode: {display(sweep['mode'])}",
            f"Sweep type: {display(sweep['kind'])}",
            f"Hysteresis: {display(sweep['hysteresis'])}",
            f"Compliance: {display(sweep['compliance'])}",
            f"NPLC: {display(sweep['nplc'])}",
            f"Delay (s): {display(sweep['delay_s'])}",
            f"Auto source range: {display(sweep['auto_source_range'])}",
            f"Source range: {display(sweep['source_range'])}",
            f"Auto measure range: {display(sweep['auto_measure_range'])}",
            f"Measure range: {display(sweep['measure_range'])}",
        ]
        if "debug_model" in sweep:
            lines.append(f"Debug model: {display(sweep['debug_model'])}")

        parameter_labels = {
            "start": "Start",
            "stop": "Stop",
            "step": "Step",
            "constant_value": "Constant value",
            "until_stop": "Until Stop",
            "duration_s": "Duration (s)",
            "interval_s": "Interval (s)",
            "segments": "Adaptive segments",
            "remove_duplicates": "Remove duplicate values",
        }
        if parameters:
            lines.extend(["", f"[{sweep['kind']} parameters]"])
            lines.extend(
                f"{parameter_labels.get(key, key)}: {display(value)}"
                for key, value in parameters.items()
            )

        message = f"Save preset '{name}' with this Hardware + Sweep snapshot?\n\n" + "\n".join(
            lines
        )
        if messagebox.askyesno("Review Sweep Preset", message):
            return data
        return None

    def save_named_preset_dialog(self):
        name = simpledialog.askstring("Save preset", "Preset name:")
        if not name:
            return
        data = self._current_preset_snapshot()
        chosen = self._fast_preset_review(name, data)
        if chosen is not None:
            save_preset(name, chosen)
            self.refresh_preset_list()
            self.log_event(f"Hardware/Sweep preset saved: {name}")

    def load_selected_preset(self):
        sel = self.preset_list.selection() if hasattr(self, "preset_list") else []
        if not sel:
            return
        name = self.preset_list.item(sel[0], "values")[0]
        data = load_presets().get(name, {})
        if not data:
            return
        if self._apply_preset_snapshot(data):
            self.log_event(f"Hardware/Sweep preset loaded: {name}")

    def delete_selected_preset(self):
        sel = self.preset_list.selection() if hasattr(self, "preset_list") else []
        if not sel:
            return
        name = self.preset_list.item(sel[0], "values")[0]
        if name == "Default":
            messagebox.showinfo("Built-in preset", "The built-in Default preset cannot be deleted.")
            return
        if messagebox.askyesno("Delete preset", f"Delete preset '{name}'?"):
            delete_preset(name)
            self.refresh_preset_list()
            self.log_event(f"Preset deleted: {name}")

    def _current_acquisition_snapshot(self, kind: str) -> dict:
        """Capture the acquisition profile truthfully for the active sweep kind."""
        try:
            self._ensure_acquisition_vars()
            profile = self.acquisition_profile.get()
        except Exception:
            return default_acquisition_state()
        if kind != "TIME" or profile not in {"Standard", "Fast", "Custom"}:
            return default_acquisition_state()
        try:
            return {
                "profile": profile,
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
        except Exception:
            return default_acquisition_state()

    def _apply_acquisition_snapshot(self, raw) -> None:
        """Restore a validated acquisition block without rebuilding pages."""
        state = clean_acquisition_state(raw)
        self._ensure_acquisition_vars()
        self.acquisition_profile.set(state["profile"])
        self.zero_refresh_before_run.set(state["zero_refresh_before_run"])
        self.autozero_during_run.set(state["autozero_during_run"])
        self.digital_filter.set(state["digital_filter"])
        self.digital_filter_count.set(state["digital_filter_count"])
        self.concurrent_measurement.set(state["concurrent_measurement"])
        self.display_during_run.set(state["display_during_run"])
        self.measurement_only_read.set(state["measurement_only_read"])
        self.range_telemetry.set(state["range_telemetry"])
        self.source_write_each_sample.set(state["source_write_each_sample"])
        self.trigger_delay_s.set(state["trigger_delay_s"])
        self._apply_acquisition_profile_state()

    def _current_preset_snapshot(self) -> dict:
        """Capture only the editable Hardware page and visible Sweep state."""
        self._restore_all_numeric_entry_defaults()
        kind = self._sweep_kind_from_ui().value
        sweep = {
            "mode": self._mode_from_ui().value,
            "kind": kind,
            "hysteresis": bool(self.hysteresis.get()),
            "compliance": float(self.compliance.get()),
            "nplc": float(self.nplc.get()),
            "delay_s": float(self.delay_s.get()),
            "auto_source_range": bool(self.auto_source_range.get()),
            "source_range": float(self.source_range.get()),
            "auto_measure_range": bool(self.auto_measure_range.get()),
            "measure_range": float(self.measure_range.get()),
        }
        if bool(self.debug.get()):
            sweep["debug_model"] = self.debug_model.get()

        if kind == "STEP":
            parameters = {
                "start": float(self.start.get()),
                "stop": float(self.stop.get()),
                "step": float(self.step.get()),
            }
        elif kind == "TIME":
            parameters = {
                "constant_value": float(self.constant_value.get()),
                "until_stop": bool(self.constant_until_stop.get()),
                "duration_s": float(self.duration_s.get()),
                "interval_s": float(self.interval_s.get()),
            }
        elif kind == "ADAPTIVE":
            parameters = {
                "segments": self._adaptive_segment_text(),
                "remove_duplicates": bool(self.adaptive_remove_duplicates.get()),
            }
        else:
            parameters = {}
        sweep["parameters"] = parameters
        sweep["acquisition"] = self._current_acquisition_snapshot(kind)

        return {
            "schema_version": PRESET_SCHEMA_VERSION,
            "hardware": {
                "port": self.port.get(),
                "baud_rate": int(self.baud_rate.get()),
                "terminal": self._terminal_scpi(self.terminal.get()),
                "sense_mode": self._sense_scpi(self.sense_mode.get()),
            },
            "sweep": sweep,
        }

    def _current_sweep_preset_dict(self) -> dict:
        """Compatibility alias for the former flat Sweep-only snapshot."""
        return self._current_preset_snapshot()

    def _apply_preset_snapshot(self, data: dict) -> bool:
        """Apply a validated v2 preset atomically without mode-default side effects."""
        data = normalize_preset(data)
        hardware = data["hardware"]
        sweep = data["sweep"]
        parameters = sweep["parameters"]
        current = self._current_preset_snapshot()

        if getattr(self, "_connected", False) and current["hardware"] != hardware:
            messagebox.showwarning(
                "Disconnect required",
                "This preset changes Hardware settings. Disconnect the active instrument, then load the preset again.",
            )
            return False
        if current["sweep"] != sweep and self._datasets.all():
            if not self._confirm_clear_existing_data("loading a Hardware/Sweep preset"):
                return False

        self._applying_preset = True
        try:
            self.port.set(hardware["port"])
            self.baud_rate.set(hardware["baud_rate"])
            self.terminal.set(self._display_terminal(hardware["terminal"]))
            self.sense_mode.set(self._display_sense(hardware["sense_mode"]))

            self.mode.set(sweep["mode"])
            self.sweep_kind.set(sweep["kind"])
            self.hysteresis.set(bool(sweep["hysteresis"]))
            self.compliance.set(sweep["compliance"])
            self.nplc.set(sweep["nplc"])
            self.delay_s.set(sweep["delay_s"])
            self.auto_source_range.set(bool(sweep["auto_source_range"]))
            self.source_range.set(sweep["source_range"])
            self.auto_measure_range.set(bool(sweep["auto_measure_range"]))
            self.measure_range.set(sweep["measure_range"])
            self.autorange.set(bool(sweep["auto_source_range"] and sweep["auto_measure_range"]))
            if "debug_model" in sweep:
                self.debug_model.set(sweep["debug_model"])

            kind = sweep["kind"]
            if kind == "STEP":
                self.start.set(parameters["start"])
                self.stop.set(parameters["stop"])
                self.step.set(parameters["step"])
            elif kind == "TIME":
                self.constant_value.set(parameters["constant_value"])
                self.constant_until_stop.set(bool(parameters["until_stop"]))
                self.duration_s.set(parameters["duration_s"])
                self.interval_s.set(parameters["interval_s"])
            elif kind == "ADAPTIVE":
                self.adaptive_segments.set(parameters["segments"])
                self.adaptive_remove_duplicates.set(bool(parameters["remove_duplicates"]))
            self._apply_acquisition_snapshot(sweep.get("acquisition"))
        finally:
            self._applying_preset = False

        self._last_mode_value = self.mode.get()
        self._last_sweep_kind_value = self.sweep_kind.get()
        self._capture_numeric_entry_defaults()
        self._update_units_for_mode()
        self._update_dynamic_sweep_fields()
        self._update_range_state()
        self._update_hysteresis_state()
        self._update_point_count()
        self._refresh_instrument_indicator()
        return True

    def _apply_settings_dict(self, data: dict):
        mapping = {
            "default_mode": self.mode,
            "default_start": self.start,
            "default_stop": self.stop,
            "default_step": self.step,
            "default_sweep_kind": self.sweep_kind,
            "default_constant_value": self.constant_value,
            "default_duration_s": self.duration_s,
            "default_constant_until_stop": self.constant_until_stop,
            "default_interval_s": self.interval_s,
            "default_compliance": self.compliance,
            "default_nplc": self.nplc,
            "default_delay_s": self.delay_s,
            "default_port": self.port,
            "default_baud_rate": self.baud_rate,
            "default_terminal": self.terminal,
            "default_sense_mode": self.sense_mode,
            "default_debug": self.debug,
            "default_debug_model": self.debug_model,
            "default_device_name": self.device_name,
            "default_operator": self.operator,
            "default_plot_layout": self.arrangement,
            "cache_enabled": self.cache_enabled,
            "cache_interval_points": self.cache_interval_points,
            "default_autorange": self.autorange,
            "auto_source_range": self.auto_source_range,
            "auto_measure_range": self.auto_measure_range,
            "default_source_range": self.source_range,
            "default_measure_range": self.measure_range,
            "default_adaptive_logic": self.adaptive_logic,
            "default_adaptive_segments": self.adaptive_segments,
            "default_adaptive_remove_duplicates": self.adaptive_remove_duplicates,
            "log_max_bytes": self.log_max_bytes,
            "log_max_kb": self.log_max_kb,
            "ui_font_family": self.ui_font_family,
            "ui_font_size": self.ui_font_size,
            "ui_theme": self.ui_theme,
            "show_front_panel_on_start": self.show_front_panel_on_start,
        }
        for k, var in mapping.items():
            if k in data:
                try:
                    value = data[k]
                    if k == "default_terminal":
                        value = self._display_terminal(value)
                    if k == "default_sense_mode":
                        value = self._display_sense(value)
                    if k == "log_max_bytes":
                        self.log_max_kb.set(max(10, int((int(value) + 1023) // 1024)))
                    elif k == "log_max_kb":
                        self.log_max_bytes.set(int(float(value)) * 1024)
                    var.set(value)
                except Exception as e:
                    # Log setting restoration errors but continue with other settings
                    import logging

                    logger = logging.getLogger("keith_ivt.ui.settings")
                    logger.warning(f"Failed to restore setting '{k}': {e}")
        self._capture_numeric_entry_defaults()
        try:
            if hasattr(self, "adaptive_text") and self.adaptive_text.winfo_exists():
                self.adaptive_text.delete("1.0", END)
                self.adaptive_text.insert("1.0", self.adaptive_segments.get())
        except Exception:
            pass
        self._update_units_for_mode()
        self._update_dynamic_sweep_fields()
        self._update_range_state()
        self._update_point_count()
        self._refresh_instrument_indicator()
        self._redraw_all_plots()
