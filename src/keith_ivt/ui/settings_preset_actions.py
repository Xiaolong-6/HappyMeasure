from __future__ import annotations

from pathlib import Path
from tkinter import BooleanVar, StringVar, IntVar, END, messagebox, simpledialog
from tkinter import ttk

from keith_ivt.data.presets import delete_preset, load_presets, save_preset
from keith_ivt.data.settings import AppSettings, load_settings, save_settings
from keith_ivt.instrument.simulator import debug_model_names
from keith_ivt.models import SweepKind, SweepMode


class SettingsPresetMixin:
    def _current_settings(self) -> AppSettings:
        return AppSettings(
            log_max_bytes=int(self.log_max_kb.get()) * 1024, default_mode=self.mode.get(), default_start=float(self.start.get()), default_stop=float(self.stop.get()), default_step=float(self.step.get()),
            default_compliance=float(self.compliance.get()), default_nplc=float(self.nplc.get()), default_port=self.port.get(), default_baud_rate=int(self.baud_rate.get()),
            default_terminal=self._terminal_scpi(self.terminal.get()), default_sense_mode=self._sense_scpi(self.sense_mode.get()), default_debug=bool(self.debug.get()), default_debug_model=self.debug_model.get(), default_device_name=self.device_name.get(), default_operator=self.operator.get(),
            default_plot_layout=self.arrangement.get(), cache_enabled=bool(self.cache_enabled.get()), cache_interval_points=int(self.cache_interval_points.get()), default_autorange=bool(self.auto_source_range.get() and self.auto_measure_range.get()),
            auto_source_range=bool(self.auto_source_range.get()),
            auto_measure_range=bool(self.auto_measure_range.get()),
            default_source_range=float(self.source_range.get()), default_measure_range=float(self.measure_range.get()), default_sweep_kind=self.sweep_kind.get(), default_constant_value=float(self.constant_value.get()),
            default_duration_s=float(self.duration_s.get()), default_constant_until_stop=bool(self.constant_until_stop.get()), default_interval_s=float(self.interval_s.get()), default_adaptive_logic=self._adaptive_logic_from_table(),
            ui_font_family=self.ui_font_family.get(), ui_font_size=int(self.ui_font_size.get()), ui_theme=self.ui_theme.get(),
        )

    def _review_dict_dialog(self, title: str, fields: dict, choices: dict | None = None) -> dict | None:
        """Review and edit settings dialog with categorized sections and themed styling."""
        import tkinter as tk
        
        # Create themed Toplevel window
        win = tk.Toplevel(self.root)
        win.title(title)
        win.transient(self.root)
        win.grab_set()
        
        # Apply current UI font settings for consistency
        ui_font = getattr(self, "ui_font_family", StringVar(value="Verdana")).get() if hasattr(self, "ui_font_family") else "Verdana"
        ui_size = int(getattr(self, "ui_font_size", IntVar(value=10)).get()) if hasattr(self, "ui_font_size") else 10
        
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
        
        ttk.Button(btns, text="Save Selected", command=save).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side="left")
        
        # Separator
        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=(0, 8))
        
        # Scrollable canvas for settings
        canvas = tk.Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)
        
        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
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
            cat_label = ttk.Label(scroll_frame, text=category, style="Card.TLabel", 
                                 font=(ui_font, ui_size, "bold"))
            cat_label.grid(row=row_offset, column=0, columnspan=3, sticky="w", pady=(12, 6), padx=(4, 0))
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
                if isinstance(value, bool):
                    vals = ["Yes", "No"]
                    var = StringVar(value="Yes" if value else "No")
                    widget = ttk.Combobox(scroll_frame, textvariable=var, values=vals, 
                                         state="readonly", width=28)
                elif key in choices:
                    var = StringVar(value=str(value))
                    widget = ttk.Combobox(scroll_frame, textvariable=var, 
                                         values=list(choices[key]), state="readonly", width=28)
                else:
                    var = StringVar(value=str(value))
                    widget = ttk.Entry(scroll_frame, textvariable=var, width=30)
                
                widget.grid(row=row_offset, column=2, sticky="ew", padx=(4, 8), pady=2)
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
        categories = {
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
            elif key in ("default_port", "default_baud_rate", "default_terminal", "default_sense_mode"):
                categories["Hardware Connection"][key] = value
            elif key in ("default_plot_layout",):
                categories["Plot & Display"][key] = value
            elif key in ("ui_font_family", "ui_font_size", "ui_theme"):
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
            "default_mode": "Source Mode",
            "default_start": "Start",
            "default_stop": "Stop",
            "default_step": "Step",
            "default_compliance": "Compliance",
            "default_nplc": "NPLC",
            "default_sweep_kind": "Sweep Type",
            "default_constant_value": "Constant Value",
            "default_duration_s": "Duration (s)",
            "default_interval_s": "Interval (s)",
            "auto_source_range": "Auto Source Range",
            "auto_measure_range": "Auto Measure Range",
            "default_source_range": "Source Range",
            "default_measure_range": "Measure Range",
            "default_adaptive_logic": "Adaptive Logic",
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
            
            # Debug Settings
            "default_debug": settings.default_debug,
            "default_debug_model": settings.default_debug_model,
        }
        
        chosen = self._review_dict_dialog("Default Settings", fields, choices={
            "default_terminal": ["FRON", "REAR"],
            "default_sense_mode": ["2W", "4W"],
            "default_plot_layout": ["Auto", "Horizontal", "Vertical"],
            "ui_font_family": self._available_ui_fonts() if hasattr(self, "_available_ui_fonts") else ["Verdana"],
            "ui_theme": ["Light", "Dark", "Debug"],
            "default_debug_model": debug_model_names(),
        })
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
        """Apply non-destructive settings feedback after a review-save action."""
        self.app_log.set_max_bytes(int(data.get("log_max_bytes", self.app_log.max_bytes)))
        try:
            self.log_max_kb.set(max(10, int((int(data.get("log_max_bytes", self.app_log.max_bytes)) + 1023) // 1024)))
            self.log_max_bytes.set(int(data.get("log_max_bytes", self.app_log.max_bytes)))
        except Exception:
            pass
        self.settings = AppSettings(**data)
        self._init_style()
        self._refresh_instrument_indicator()
        self.log_event(f"Settings saved: {path}; keys={', '.join(sorted(chosen))}")
        messagebox.showinfo("Settings saved", "Saved settings:\n" + "\n".join(sorted(chosen)))

    def refresh_preset_list(self):
        if not hasattr(self, "preset_list"): return
        self.preset_list.delete(*self.preset_list.get_children())
        for name in sorted(load_presets().keys(), key=lambda n: (n != "Default", n.lower())): self.preset_list.insert("", END, values=(name,))


    def _fast_preset_review(self, name: str, data: dict) -> dict | None:
        """Fast preset review path with clear, mode-aware preview."""
        # Map internal keys to user-friendly labels
        label_map = {
            "default_mode": "Mode",
            "default_sweep_kind": "Sweep Type",
            "default_start": "Start",
            "default_stop": "Stop",
            "default_step": "Step",
            "default_constant_value": "Constant Value",
            "default_duration_s": "Duration (s)",
            "default_constant_until_stop": "Until Stop",
            "default_interval_s": "Interval (s)",
            "default_compliance": "Compliance",
            "default_nplc": "NPLC",
            "default_autorange": "Auto Range",
            "default_source_range": "Source Range",
            "default_measure_range": "Measure Range",
            "default_adaptive_logic": "Adaptive Logic",
            "default_debug_model": "Debug Model",
        }
        
        # Determine which fields are relevant based on sweep type
        sweep_kind = data.get("default_sweep_kind", "STEP")
        
        # Always show these base fields
        base_keys = ["default_mode", "default_sweep_kind", "default_compliance", "default_nplc"]
        
        # Show sweep-type-specific fields
        if sweep_kind == "STEP":
            type_keys = ["default_start", "default_stop", "default_step"]
        elif sweep_kind == "CONSTANT_TIME":
            type_keys = ["default_constant_value", "default_duration_s", "default_constant_until_stop", "default_interval_s"]
        elif sweep_kind == "ADAPTIVE":
            type_keys = ["default_start", "default_stop", "default_adaptive_logic"]
        else:
            type_keys = []
        
        # Show range settings if autorange is off
        range_keys = []
        if not data.get("default_autorange", True):
            range_keys = ["default_source_range", "default_measure_range"]
        
        # Show debug model only in debug mode
        extra_keys = ["default_debug_model"] if data.get("default_debug_model") else []
        
        # Build the preview lines with friendly labels
        all_keys = base_keys + type_keys + range_keys + extra_keys
        lines = []
        for key in all_keys:
            if key in data:
                label = label_map.get(key, key)
                value = data[key]
                # Format boolean values nicely
                if isinstance(value, bool):
                    value = "Yes" if value else "No"
                lines.append(f"{label}: {value}")
        
        message = f"Save preset '{name}' with these settings?\n\n" + "\n".join(lines)
        if messagebox.askyesno("Review Sweep Preset", message):
            return data
        return None

    def save_named_preset_dialog(self):
        name = simpledialog.askstring("Save preset", "Preset name:")
        if not name: return
        data = self._current_sweep_preset_dict()
        chosen = self._fast_preset_review(name, data)
        if chosen is not None:
            save_preset(name, chosen); self.refresh_preset_list(); self.log_event(f"Sweep preset saved: {name}")

    def load_selected_preset(self):
        sel = self.preset_list.selection() if hasattr(self, "preset_list") else []
        if not sel: return
        name = self.preset_list.item(sel[0], "values")[0]
        data = load_presets().get(name, {})
        if not data: return
        self._apply_settings_dict(data)
        self.log_event(f"Preset loaded: {name}")

    def delete_selected_preset(self):
        sel = self.preset_list.selection() if hasattr(self, "preset_list") else []
        if not sel: return
        name = self.preset_list.item(sel[0], "values")[0]
        if name == "Default":
            messagebox.showinfo("Built-in preset", "The built-in Default preset cannot be deleted."); return
        if messagebox.askyesno("Delete preset", f"Delete preset '{name}'?"):
            delete_preset(name); self.refresh_preset_list(); self.log_event(f"Preset deleted: {name}")

    def _current_sweep_preset_dict(self) -> dict:
        self._sync_adaptive_logic_text()
        return {
            "default_mode": self.mode.get(),
            "default_sweep_kind": self.sweep_kind.get(),
            "default_start": float(self.start.get()),
            "default_stop": float(self.stop.get()),
            "default_step": float(self.step.get()),
            "default_constant_value": float(self.constant_value.get()),
            "default_duration_s": float(self.duration_s.get()),
            "default_constant_until_stop": bool(self.constant_until_stop.get()),
            "default_interval_s": float(self.interval_s.get()),
            "default_compliance": float(self.compliance.get()),
            "default_nplc": float(self.nplc.get()),
            "default_autorange": bool(self.auto_source_range.get() and self.auto_measure_range.get()),
            "default_source_range": float(self.source_range.get()),
            "default_measure_range": float(self.measure_range.get()),
            "default_adaptive_logic": self.adaptive_logic.get() or self._adaptive_logic_from_table(),
            "default_debug_model": self.debug_model.get(),
        }

    def _apply_settings_dict(self, data: dict):
        mapping = {
            "default_mode": self.mode, "default_start": self.start, "default_stop": self.stop, "default_step": self.step, "default_sweep_kind": self.sweep_kind, "default_constant_value": self.constant_value,
            "default_duration_s": self.duration_s, "default_constant_until_stop": self.constant_until_stop, "default_interval_s": self.interval_s, "default_compliance": self.compliance, "default_nplc": self.nplc, "default_port": self.port,
            "default_baud_rate": self.baud_rate, "default_terminal": self.terminal, "default_sense_mode": self.sense_mode, "default_debug": self.debug, "default_debug_model": self.debug_model, "default_device_name": self.device_name,
            "default_operator": self.operator, "default_plot_layout": self.arrangement, "cache_enabled": self.cache_enabled, "cache_interval_points": self.cache_interval_points,
            "default_autorange": self.autorange, "auto_source_range": self.auto_source_range, "auto_measure_range": self.auto_measure_range, "default_source_range": self.source_range, "default_measure_range": self.measure_range, "default_adaptive_logic": self.adaptive_logic,
            "log_max_bytes": self.log_max_bytes, "log_max_kb": self.log_max_kb, "ui_font_family": self.ui_font_family, "ui_font_size": self.ui_font_size, "ui_theme": self.ui_theme,
        }
        for k, var in mapping.items():
            if k in data:
                try:
                    value = data[k]
                    if k == "default_terminal": value = self._display_terminal(value)
                    if k == "default_sense_mode": value = self._display_sense(value)
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
        try:
            if hasattr(self, "adaptive_text") and self.adaptive_text.winfo_exists():
                self.adaptive_text.delete("1.0", END); self.adaptive_text.insert("1.0", self.adaptive_logic.get())
        except Exception:
            pass
        self._update_units_for_mode(); self._update_dynamic_sweep_fields(); self._update_range_state(); self._update_point_count(); self._refresh_instrument_indicator(); self._redraw_all_plots()
