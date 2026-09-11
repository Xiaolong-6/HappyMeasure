from __future__ import annotations

from tkinter import BooleanVar, messagebox, ttk

from keith_ivt.ui.mixin_typing import UiMixinTyping
from keith_ivt.ui.widgets import add_tip


class SettingsPanelMixin(UiMixinTyping):
    """Build the user-facing Settings page and its developer-only section."""

    def _settings_heading(self, parent, text: str, row: int = 0) -> None:
        ttk.Label(
            parent,
            text=text,
            style="Card.TLabel",
            font=(
                getattr(self.settings, "ui_font_family", "Verdana"),
                int(getattr(self.settings, "ui_font_size", 10)),
                "bold",
            ),
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 6))

    def _settings_checkbutton(
        self,
        parent,
        text: str,
        variable,
        row: int,
        tip: str,
        *,
        command=None,
    ):
        """Use a conventional checkbox for persistent/configuration booleans.

        Sweep controls intentionally keep their touch-friendly toggle buttons;
        Settings uses native checkbox semantics so options do not look like
        immediate command buttons.
        """
        check = ttk.Checkbutton(
            parent,
            text=text,
            variable=variable,
            command=command,
            takefocus=True,
        )
        check.grid(row=row, column=0, columnspan=2, sticky="w", pady=3)
        add_tip(check, tip)
        return check

    def _ensure_developer_tools_var(self):
        var = getattr(self, "developer_tools_visible", None)
        if var is None:
            # Session-only on purpose. The simulator backend itself keeps its
            # existing persisted default; this flag only controls visibility of
            # developer-facing tools.
            var = BooleanVar(master=self.root, value=bool(self.debug.get()))
            self.developer_tools_visible = var
        return var

    def _developer_tools_visibility_changed(self) -> None:
        var = self._ensure_developer_tools_var()
        if not bool(var.get()) and bool(self.debug.get()):
            var.set(True)
            messagebox.showinfo(
                "Developer tools",
                "Turn off the debug simulator before hiding Developer Tools.",
                parent=self.root,
            )
            return
        if getattr(self, "_active_nav", None) == "Settings":
            self._show_nav("Settings")

    def _update_settings_cache_interval_state(self) -> None:
        row = getattr(self, "settings_cache_interval_row", None)
        if not row:
            return
        try:
            row[1].configure(state="normal" if self.cache_enabled.get() else "disabled")
        except Exception:
            pass

    def _build_settings_panel(self, parent) -> None:
        self._section_title(parent, "Settings")
        developer_tools = self._ensure_developer_tools_var()

        appearance = ttk.Frame(parent, style="Card.TFrame", padding=(10, 8))
        appearance.pack(fill="x", padx=10, pady=(4, 4))
        appearance.columnconfigure(1, weight=1)
        self._settings_heading(appearance, "Appearance")

        self.ui_font_combo = self._combo(
            appearance,
            "UI font",
            self.ui_font_family,
            self._available_ui_fonts(),
            1,
            "Application UI font family. The list is read from fonts installed on this system.",
        )
        self.ui_font_combo.bind(
            "<<ComboboxSelected>>", lambda _e: self.apply_ui_appearance(), add="+"
        )
        self.ui_scale_choice.set(f"{int(self.ui_font_size.get())} pt")
        self.ui_scale_combo = self._combo(
            appearance,
            "UI scale",
            self.ui_scale_choice,
            [f"{n} pt" for n in range(8, 19)],
            2,
            "Application UI scale / font size.",
        )
        self.ui_scale_combo.bind(
            "<<ComboboxSelected>>", lambda _e: self._on_ui_scale_menu(), add="+"
        )
        self.ui_theme_combo = self._combo(
            appearance,
            "UI theme",
            self.ui_theme,
            ["Light", "Dark", "Debug"],
            3,
            "Light is the normal theme. Dark uses integrated dark backgrounds. Debug keeps strong borders for layout inspection.",
        )
        self.ui_theme_combo.bind(
            "<<ComboboxSelected>>", lambda _e: self.apply_ui_appearance(), add="+"
        )

        data_box = ttk.Frame(parent, style="Card.TFrame", padding=(10, 8))
        data_box.pack(fill="x", padx=10, pady=4)
        data_box.columnconfigure(1, weight=1)
        self._settings_heading(data_box, "Data & Logging")
        self._entry(
            data_box,
            "Log size limit (KB)",
            self.log_max_kb,
            1,
            "Rotating log size limit in KB. A new log file is created when logs/log.txt reaches this size.",
        )
        if not getattr(self, "_settings_log_trace_bound", False):
            try:
                self.log_max_kb.trace_add("write", lambda *_args: self._on_log_max_kb_changed())
                self._settings_log_trace_bound = True
            except Exception:
                pass

        self._settings_checkbutton(
            data_box,
            "Temporary cache",
            self.cache_enabled,
            2,
            "Optional temporary cache during long sweeps. Default OFF.",
            command=self._update_settings_cache_interval_state,
        )
        self.settings_cache_interval_row = self._entry(
            data_box,
            "Cache interval points",
            self.cache_interval_points,
            3,
            "Write the temporary cache every N points when caching is enabled.",
        )
        self._update_settings_cache_interval_state()

        app_box = ttk.Frame(parent, style="Card.TFrame", padding=(10, 8))
        app_box.pack(fill="x", padx=10, pady=4)
        app_box.columnconfigure(0, weight=1)
        app_box.columnconfigure(1, weight=1)
        self._settings_heading(app_box, "Application")
        self._settings_checkbutton(
            app_box,
            "Show developer tools",
            developer_tools,
            1,
            "Show developer-only diagnostics and simulator controls for this session. This is independent of the simulator backend.",
            command=self._developer_tools_visibility_changed,
        )
        ttk.Button(
            app_box,
            text="Review Default Settings...",
            command=self.review_and_save_settings,
        ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(
            app_box,
            text="Restart UI",
            command=self._restart_ui,
            style="Soft.TButton",
        ).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))

        if not bool(developer_tools.get()):
            return

        dev_box = ttk.Frame(parent, style="Card.TFrame", padding=(10, 8))
        dev_box.pack(fill="x", padx=10, pady=(4, 10))
        dev_box.columnconfigure(0, weight=1)
        self._settings_heading(dev_box, "Developer Tools")

        self._settings_checkbutton(
            dev_box,
            "Use debug simulator",
            self.debug,
            1,
            "Use the deterministic simulated source-meter backend instead of a physical instrument.",
        )
        ttk.Separator(dev_box, orient="horizontal").grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=(8, 8)
        )
        ttk.Label(
            dev_box,
            text="Diagnostics",
            style="Card.TLabel",
            font=(
                getattr(self.settings, "ui_font_family", "Verdana"),
                int(getattr(self.settings, "ui_font_size", 10)),
                "bold",
            ),
        ).grid(row=3, column=0, columnspan=2, sticky="w")
        ttk.Label(
            dev_box,
            text=(
                "UI Diagnostics exercises Tk navigation and callbacks without touching hardware. "
                "Hardware Diagnostics checks a real instrument with an explicit no-DUT safety gate "
                "and never enables source output."
            ),
            style="Muted.TLabel",
            wraplength=380,
            justify="left",
        ).grid(row=4, column=0, columnspan=2, sticky="ew", pady=(4, 8))

        ui_button = ttk.Button(
            dev_box,
            text="Run UI Diagnostics...",
            command=self._show_ui_diagnostics,
            style="Soft.TButton",
        )
        ui_button.grid(row=5, column=0, columnspan=2, sticky="ew")
        add_tip(
            ui_button,
            "Exercise real Tk navigation/control callbacks and create a shareable UI diagnostic report without connecting to hardware.",
        )

        hardware_button = ttk.Button(
            dev_box,
            text="Run Hardware Diagnostics...",
            command=self._show_hardware_diagnostics,
            style="Soft.TButton",
        )
        hardware_button.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        add_tip(
            hardware_button,
            "Run communication and output-off safety checks on the selected real Keithley. No measurement is started and source output is never enabled.",
        )


__all__ = ["SettingsPanelMixin"]
