from __future__ import annotations

from pathlib import Path
from tkinter import END, Text, StringVar
from tkinter import font as tkfont, ttk

from keith_ivt.instrument.simulator import debug_model_names
from keith_ivt.ui.widgets import add_tip
from keith_ivt.version import APP_NAME, __release_stage__, __version__


class PanelBuilderMixin:

    def _available_ui_fonts(self) -> list[str]:
        """Return installed UI fonts with Verdana preferred when available."""
        try:
            fonts = sorted({str(f) for f in tkfont.families(self.root) if str(f).strip()}, key=str.lower)
        except Exception:
            fonts = ["Verdana"]
        if "Verdana" in fonts:
            fonts.remove("Verdana")
            return ["Verdana"] + fonts
        return fonts or ["Verdana"]

    def _build_hardware_panel(self, parent) -> None:
        self._section_title(parent, "Hardware")
        box = ttk.Frame(parent, style="Card.TFrame", padding=(14, 12))
        box.pack(fill="x", padx=12, pady=6)
        box.columnconfigure(1, weight=1)
        self.port_combo = self._combo(box, "COM port", self.port, self._refresh_port_choices(), 0, "Detected serial ports. Debug mode exposes a simulated COM3.")
        self.baud_combo = self._combo(box, "Baud", self.baud_rate, [9600, 19200, 38400, 57600], 1, "Default RS-232 baud rate for Keithley 2400-class instruments.")
        self.terminal_combo = self._combo(box, "Terminal", self.terminal, ["FRONT", "REAR"], 2, "Front or rear terminal selection. Hidden/disabled later for devices without front/rear routing.")
        self.sense_combo = self._combo(box, "Sense", self.sense_mode, ["2-wire", "4-wire"], 3, "2-wire or 4-wire remote sense. Future drivers advertise whether 4-wire is available.")
        row = ttk.Frame(box, style="Card.TFrame")
        row.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        row.columnconfigure(0, weight=1)
        self.connect_btn = ttk.Button(row, text="Connect", command=self.connect_or_disconnect)
        self.connect_btn.grid(row=0, column=0, sticky="ew")
        add_tip(self.connect_btn, "Connect to the selected instrument, or disconnect the active connection when already connected.")

        cap_box = ttk.Frame(parent, style="Card.TFrame", padding=(14, 12))
        cap_box.pack(fill="x", padx=12, pady=(6, 10))
        cap_box.columnconfigure(0, weight=1)
        ttk.Label(cap_box, text="Detected device model", style="Card.TLabel", font=(getattr(self.settings, "ui_font_family", "Verdana"), int(getattr(self.settings, "ui_font_size", 10)), "bold")).grid(row=0, column=0, sticky="w")
        self.hardware_profile_text = StringVar(value=self._capability_summary())
        ttk.Label(cap_box, textvariable=self.hardware_profile_text, style="Card.TLabel", wraplength=380, justify="left").grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self._refresh_instrument_indicator()

    def _build_sweep_panel(self, parent) -> None:
        self._section_title(parent, "Sweep")
        top = ttk.Frame(parent, style="Card.TFrame", padding=(10, 6))
        top.pack(fill="x", padx=10, pady=4)
        top.columnconfigure(1, weight=1)
        self.mode_combo = self._combo(top, "1. Mode", self.mode, self._available_modes(), 0, "Capability-aware source mode. Current-source or voltage-source IV mode.")
        self.sweep_kind_combo = self._combo(top, "2. Sweep type", self.sweep_kind, self._available_sweep_kinds(), 1, "Sweep algorithm for IV testing. Use Time for fixed-value time traces.")
        self.hysteresis_check = self._check(
            top,
            "Forward/reverse hysteresis",
            self.hysteresis,
            2,
            "For Step and Adaptive sweeps, measure the forward source sequence and then sweep back through the same values. Default OFF.",
            command=lambda: self._update_point_count(),
        )
        self.debug_model_row = None
        if self.debug.get():
            self.debug_model_row = self._combo(top, "3. Debug load model", self.debug_model, debug_model_names(), 3, "Simulator-only load/response model. In voltage-source mode it returns current; in current-source mode it returns voltage.")
        # Common safety/range controls stay above the sweep-specific editor so
        # Adaptive mode cannot push range/compliance fields out of view.
        self.common_box = ttk.Frame(parent, style="Card.TFrame", padding=(10, 8))
        self.common_box.pack(fill="x", padx=10, pady=(8, 4))
        self.common_box.columnconfigure(1, weight=1)
        self.common_box.columnconfigure(2, weight=0, minsize=84)
        self._entry(self.common_box, self.compliance_label, self.compliance, 0, "Compliance limit. Units depend on source mode.")
        self._entry(self.common_box, "NPLC", self.nplc, 1, "Power-line cycles per integration. Higher NPLC improves noise but increases minimum interval.")
        self._entry(self.common_box, "Delay (s)", self.delay_s, 2, "Per-point source-settling delay before readback. Default 0 s. Included in the time estimate and Keithley 2400 source delay command.")
        self.source_range_row = self._range_control_row(self.common_box, "Source range", self.source_range, self.auto_source_range, 3, "Fixed source range when Auto source range is disabled.")
        self.measure_range_row = self._range_control_row(self.common_box, "Measure range", self.measure_range, self.auto_measure_range, 4, "Fixed measure range when Auto measure range is disabled.")
        self.dynamic_box = ttk.Frame(parent, style="Card.TFrame", padding=(10, 8))
        self.dynamic_box.pack(fill="x", padx=10, pady=(4, 8))
        self._update_hysteresis_state()
        self._update_dynamic_sweep_fields()
        self._update_range_state()

    def _build_settings_panel(self, parent) -> None:
        self._section_title(parent, "Settings")
        box = ttk.Frame(parent, style="Card.TFrame", padding=(10, 8))
        box.pack(fill="x", padx=10, pady=4)
        box.columnconfigure(1, weight=1)
        self._check(box, "Use debug simulator", self.debug, 0, "Keep enabled until simulator, UI, export, and import paths are stable.")
        self._entry(box, "Log max KB", self.log_max_kb, 1, "Rotating log size limit in KB. When logs/log.txt would exceed this limit, a new log file is created.")
        try:
            self.log_max_kb.trace_add("write", lambda *_args: self._on_log_max_kb_changed())
        except Exception:
            pass
        self._check(box, "Temporary cache", self.cache_enabled, 2, "Optional alpha cache during long sweeps. Default OFF.")
        self._entry(box, "Cache interval points", self.cache_interval_points, 3, "Write temporary cache every N points when enabled.")
        if self.debug.get():
            ttk.Label(box, text="Debug UI appearance", style="Muted.TLabel").grid(row=4, column=0, columnspan=2, sticky="w", pady=(12, 4))
            self.ui_font_combo = self._combo(box, "UI font", self.ui_font_family, self._available_ui_fonts(), 5, "Application UI font family. This list is read from fonts installed on this system.")
            self.ui_font_combo.bind("<<ComboboxSelected>>", lambda _e: self.apply_ui_appearance(), add="+")
            self.ui_scale_choice.set(f"{int(self.ui_font_size.get())} pt")
            self.ui_scale_combo = self._combo(box, "UI scale", self.ui_scale_choice, [f"{n} pt" for n in range(8, 19)], 6, "Application UI scale / font size.")
            self.ui_scale_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_ui_scale_menu(), add="+")
            self.ui_theme_combo = self._combo(box, "UI theme", self.ui_theme, ["Light", "Dark", "Debug"], 7, "Light is the default clean theme. Debug keeps strong borders for layout inspection; Dark uses integrated dark backgrounds.")
            self.ui_theme_combo.bind("<<ComboboxSelected>>", lambda _e: self.apply_ui_appearance(), add="+")
            save_row = 8
        else:
            ttk.Label(box, text="UI appearance controls are shown only in debug mode.", style="Muted.TLabel", wraplength=360, justify="left").grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 0))
            save_row = 5
        ttk.Button(box, text="Default Settings...", command=self.review_and_save_settings).grid(row=save_row, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        restart_row = save_row + 1
        ttk.Button(box, text="Restart UI", command=self._restart_ui, style="Soft.TButton").grid(row=restart_row, column=0, columnspan=2, sticky="ew", pady=(6, 0))

    def _on_ui_scale_menu(self) -> None:
        try:
            text = self.ui_scale_choice.get().replace("pt", "").strip()
            size = int(text)
            self.ui_font_size.set(size)
            self.apply_ui_appearance()
        except Exception:
            pass

    def _on_log_max_kb_changed(self) -> None:
        try:
            kb_value = int(self.log_max_kb.get())
            if kb_value < 1:
                return
            new_max_bytes = kb_value * 1024
            if hasattr(self, 'app_log'):
                self.app_log.set_max_bytes(new_max_bytes)
            if hasattr(self, 'log_max_bytes'):
                self.log_max_bytes.set(new_max_bytes)
        except Exception:
            pass

    def _restart_ui(self) -> None:
        from tkinter import messagebox
        import sys
        import os
        import subprocess
        if not messagebox.askyesno("Restart UI", "Restart the HappyMeasure UI?\n\nAny unsaved changes will be lost."):
            return
        try:
            executable = sys.executable
            script_path = os.path.abspath(sys.argv[0])
            if script_path.endswith('.py'):
                args = [executable, script_path] + sys.argv[1:]
            else:
                args = [script_path] + sys.argv[1:]
            if sys.platform == "win32":
                subprocess.Popen(args, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP, close_fds=True)
            else:
                subprocess.Popen(args, start_new_session=True, close_fds=True)
            self.root.quit()
            self.root.destroy()
        except Exception as e:
            messagebox.showerror("Restart Failed", f"Failed to restart UI:\n{e}\n\nPlease restart manually.")

    def _build_log_panel(self, parent) -> None:
        self._section_title(parent, "Log")
        try:
            parent.rowconfigure(0, weight=1)
            parent.columnconfigure(0, weight=1)
        except Exception:
            pass
        box = ttk.Frame(parent, style="Card.TFrame", padding=(10, 8))
        box.grid(row=0, column=0, sticky="nsew", padx=10, pady=4)
        box.rowconfigure(1, weight=1)
        box.columnconfigure(0, weight=1)
        parent.bind("<Configure>", lambda _e: self._update_content_window_height("Log"), add="+")
        btns = ttk.Frame(box, style="Card.TFrame")
        btns.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        btns.columnconfigure(0, weight=1)
        ttk.Button(btns, text="Open log folder", command=self.open_log_folder).grid(row=0, column=0, sticky="w")
        self.log_text = Text(box, height=10, wrap="word", background=self._palette["input"], foreground=self._palette["fg"], insertbackground=self._palette["fg"], relief="solid" if getattr(self, "_theme_high_contrast", False) else "flat", borderwidth=1)
        self.log_text.grid(row=1, column=0, sticky="nsew")
        y = ttk.Scrollbar(box, orient="vertical", command=self.log_text.yview)
        y.grid(row=1, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=y.set)
        self._log_font_size = int(getattr(self.settings, "ui_font_size", 10))
        self._update_log_font()
        self.log_text.bind("<Control-MouseWheel>", self._on_log_font_zoom, add="+")
        from keith_ivt.ui.widgets import add_tip
        add_tip(self.log_text, "Ctrl+Scroll to adjust font size")
        try:
            p = Path("logs") / "log.txt"
            if p.exists():
                self.log_text.insert(END, p.read_text(encoding="utf-8")[-6000:])
        except Exception:
            pass

    def _on_log_font_zoom(self, event) -> str:
        delta = int(event.delta / 120)
        new_size = max(8, min(self._log_font_size + delta, 18))
        if new_size != self._log_font_size:
            self._log_font_size = new_size
            self._update_log_font()
        return "break"

    def _update_log_font(self) -> None:
        try:
            font_family = getattr(self.settings, "ui_font_family", "Verdana")
            self.log_text.configure(font=(font_family, self._log_font_size))
        except Exception:
            pass

    def _build_about_panel(self, parent) -> None:
        self._section_title(parent, "About")
        self._set_update_check_message(self.update_notice_text.get())
        if not self._show_cached_update_check_result():
            self._check_for_updates_async()
        import tkinter as tk
        try:
            parent.rowconfigure(0, weight=1)
            parent.columnconfigure(0, weight=1)
        except Exception:
            pass
        about_bg = self._palette.get("card", self._palette.get("panel", "#FFFFFF"))
        canvas = tk.Canvas(parent, highlightthickness=0, background=about_bg, bd=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas, padding=(16, 14), style="Card.TFrame")
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<Configure>", lambda event: canvas.itemconfig("all", width=event.width))

        def _on_mousewheel(event):
            try:
                if not canvas.winfo_exists():
                    return "break"
                delta = getattr(event, "delta", 0)
                if delta:
                    canvas.yview_scroll(int(-1 * (delta / 120)), "units")
                return "break"
            except Exception:
                return "break"

        def _bind_about_mousewheel(widget):
            try:
                widget.bind("<MouseWheel>", _on_mousewheel, add="+")
                widget.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"), add="+")
                widget.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"), add="+")
                for child in widget.winfo_children():
                    _bind_about_mousewheel(child)
            except Exception:
                pass

        canvas.bind("<MouseWheel>", _on_mousewheel, add="+")
        scroll_frame.bind("<MouseWheel>", _on_mousewheel, add="+")
        canvas.pack(side="left", fill="both", expand=True, padx=(0, 4))
        scrollbar.pack(side="right", fill="y")
        box = scroll_frame
        box.columnconfigure(0, weight=1)
        row = 0
        app_header = f"{APP_NAME} v{__version__}"
        ttk.Label(box, text=app_header, style="AboutTitle.TLabel", font=(getattr(self.settings, "ui_font_family", "Verdana"), int(getattr(self.settings, "ui_font_size", 10)) + 2, "bold")).grid(row=row, column=0, sticky="w", pady=(0, 4))
        row += 1
        ttk.Label(box, textvariable=self.update_notice_text, style="AboutStatus.TLabel", wraplength=450, justify="left").grid(row=row, column=0, sticky="w", pady=(0, 6))
        row += 1
        update_btn = ttk.Button(box, text="Open Latest Release Download Page", command=self._open_update_release_page, style="Soft.TButton")
        update_btn.grid(row=row, column=0, sticky="ew", pady=(0, 16))
        add_tip(update_btn, "Open the latest HappyMeasure release page if known; otherwise open the project repository.")
        row += 1
        ttk.Label(box, text="What is HappyMeasure?", style="AboutTitle.TLabel", font=(getattr(self.settings, "ui_font_family", "Verdana"), int(getattr(self.settings, "ui_font_size", 10)), "bold")).grid(row=row, column=0, sticky="w", pady=(8, 4))
        row += 1
        description = (
            f"Release stage: {__release_stage__}.\n\n"
            "HappyMeasure is a professional measurement UI for characterizing electronic devices "
            "using Keithley 2400/2450 series SourceMeter instruments. It provides an intuitive "
            "interface for performing IV (current-voltage) sweeps, time-based measurements, "
            "and adaptive testing with real-time visualization and data export."
        )
        ttk.Label(box, text=description, style="AboutBody.TLabel", wraplength=450, justify="left").grid(row=row, column=0, sticky="w", pady=(0, 12))
        row += 1
        ttk.Label(box, text="Key Features", style="AboutTitle.TLabel", font=(getattr(self.settings, "ui_font_family", "Verdana"), int(getattr(self.settings, "ui_font_size", 10)), "bold")).grid(row=row, column=0, sticky="w", pady=(8, 4))
        row += 1
        features = [
            "• Multiple sweep modes: Step, Time (constant), and Adaptive",
            "• Optional forward/reverse hysteresis for Step and Adaptive sweeps",
            "• Voltage or current source operation",
            "• Real-time plotting with multiple view options",
            "• Automatic data backup and recovery",
            "• Import/export in CSV format with metadata",
            "• Device preset management for quick setup",
            "• Simulator mode for safe testing without hardware",
            "• Multi-trace comparison and analysis",
        ]
        for feature in features:
            ttk.Label(box, text=feature, style="AboutBody.TLabel", wraplength=450).grid(row=row, column=0, sticky="w", pady=1)
            row += 1
        row += 1
        ttk.Label(box, text="Supported Hardware", style="AboutTitle.TLabel", font=(getattr(self.settings, "ui_font_family", "Verdana"), int(getattr(self.settings, "ui_font_size", 10)), "bold")).grid(row=row, column=0, sticky="w", pady=(8, 4))
        row += 1
        hardware = "• Keithley 2400 Series SourceMeter (via RS-232)\n• Keithley 2450 Series SourceMeter (via RS-232)\n• Built-in simulator for offline testing"
        ttk.Label(box, text=hardware, style="AboutBody.TLabel", wraplength=450, justify="left").grid(row=row, column=0, sticky="w", pady=(0, 12))
        row += 1
        ttk.Label(box, text="Safety Notice", style="AboutTitle.TLabel", font=(getattr(self.settings, "ui_font_family", "Verdana"), int(getattr(self.settings, "ui_font_size", 10)), "bold")).grid(row=row, column=0, sticky="w", pady=(8, 4))
        row += 1
        safety = "⚠ Always use the debug simulator before connecting real hardware.\n⚠ Verify wiring and compliance limits externally.\n⚠ The Emergency Stop button requests output-off at the next safe point."
        ttk.Label(box, text=safety, style="AboutBody.TLabel", wraplength=450, justify="left", foreground=self._palette.get("danger", "#d9534f")).grid(row=row, column=0, sticky="w", pady=(0, 16))
        _bind_about_mousewheel(scroll_frame)
        parent.update_idletasks()
        max_height = min(parent.winfo_screenheight() * 0.7, 600)
        canvas.config(height=int(max_height))
        parent.bind("<Configure>", lambda e: self._update_about_wraplength(scroll_frame, canvas), add="+")

    def _update_about_wraplength(self, scroll_frame, canvas) -> None:
        try:
            canvas_width = canvas.winfo_width()
            new_wraplength = max(280, canvas_width - 60)
            for child in scroll_frame.winfo_children():
                if isinstance(child, ttk.Label):
                    try:
                        child.configure(wraplength=new_wraplength)
                    except Exception:
                        pass
        except Exception:
            pass

    def _check_for_updates(self) -> None:
        """Compatibility hook for app classes that provide async update checks."""
        if hasattr(self, "_check_for_updates_async"):
            self._check_for_updates_async()
