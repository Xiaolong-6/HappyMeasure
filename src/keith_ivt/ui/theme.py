from __future__ import annotations

from tkinter import ttk

from keith_ivt.data.settings import load_settings


class ThemeMixin:
    def _init_style(self) -> None:
        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass
        try:
            import tkinter.font as tkfont
            family = getattr(self, "settings", load_settings()).ui_font_family
            size = int(getattr(self, "settings", load_settings()).ui_font_size)
            for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
                try:
                    tkfont.nametofont(name).configure(family=family, size=size)
                except Exception:
                    pass
        except Exception:
            pass

        theme = getattr(getattr(self, "settings", None), "ui_theme", "Light")
        if theme in {"Nordic Light"}:
            theme = "Light"
        elif theme in {"High contrast", "High Contrast"}:
            theme = "Debug"
        elif theme == "Nordic Dark":
            theme = "Dark"
        if theme not in {"Light", "Dark", "Debug"}:
            theme = "Light"

        dark = theme == "Dark"
        debug = theme == "Debug"
        self._theme_dark = dark
        self._theme_high_contrast = debug
        self._theme_debug = debug

        if debug:
            self._palette = {
                "bg": "#FFFFFF",
                "panel": "#FFFFFF",
                "card": "#FFFFFF",
                "nav": "#FFFFFF",
                "nav_active": "#FFE66D",
                "fg": "#000000",
                "muted": "#000000",
                "border": "#000000",
                "input": "#FFFFFF",
                "button": "#FFFFFF",
                "disabled": "#E0E0E0",
                "button_active": "#FFE66D",
                "accent": "#0057B8",
                "forest": "#008000",
                "danger": "#CC0000",
                "plot_bg": "#FFFFFF",
                "grid": "#555555",
                "splitter": "#9AB0B8",
            }
            frame_border = 2
            frame_relief = "solid"
            status_border = 1
        elif dark:
            self._palette = {
                "bg": "#151A1E",
                "panel": "#151A1E",
                "card": "#20262B",
                "nav": "#1B2126",
                "nav_active": "#27323A",
                "fg": "#EEF3F5",
                "muted": "#A7B1B8",
                "border": "#364149",
                "input": "#20262B",
                "button": "#242C32",
                "disabled": "#2A3035",
                "button_active": "#303A42",
                "accent": "#5AA9E6",
                "forest": "#4EC9A6",
                "danger": "#E66C66",
                "plot_bg": "#1B2025",
                "grid": "#364149",
                "splitter": "#303A42",
            }
            frame_border = 0
            frame_relief = "flat"
            status_border = 0
        else:
            self._palette = {
                "bg": "#F7F9FB",
                "panel": "#FFFFFF",
                "card": "#FFFFFF",
                "nav": "#FFFFFF",
                "nav_active": "#EAF5FF",
                "fg": "#1F2933",
                "muted": "#66788A",
                "border": "#D6E3EA",
                "input": "#FFFFFF",
                "button": "#FFFFFF",
                "disabled": "#EEF3F6",
                "button_active": "#EEF7FF",
                "accent": "#3498DB",
                "forest": "#1ABC9C",
                "danger": "#E74C3C",
                "plot_bg": "#FFFFFF",
                "grid": "#ECEFF2",
                "splitter": "#DDEAF1",
            }
            frame_border = 0
            frame_relief = "flat"
            status_border = 0

        bg = self._palette["bg"]
        panel = self._palette["panel"]
        nav = self._palette["nav"]
        active = self._palette["nav_active"]
        fg = self._palette["fg"]
        muted = self._palette["muted"]
        button_bg = self._palette["button"]
        button_active = self._palette["button_active"]
        border = self._palette["border"]
        input_bg = self._palette["input"]
        card = self._palette["card"]
        self.root.configure(bg=bg)

        self.style.configure("TFrame", background=panel, borderwidth=0)
        self.style.configure("App.TFrame", background=bg, borderwidth=0)
        self.style.configure("Card.TFrame", background=card, borderwidth=frame_border, relief=frame_relief, bordercolor=border)
        self.style.configure("Toolbar.TFrame", background=card, borderwidth=frame_border, relief=frame_relief, bordercolor=border)
        self.style.configure("ToolbarInner.TFrame", background=card, borderwidth=0, relief="flat")
        self.style.configure("Operator.TFrame", background=card, borderwidth=frame_border, relief=frame_relief, bordercolor=border)
        self.style.configure("Status.TFrame", background=bg, borderwidth=0)
        self.style.configure("StatusCell.TLabel", background=bg, foreground=muted, padding=(8, 5), relief="solid" if debug else "flat", borderwidth=status_border, bordercolor=border)
        self.style.configure("StatusPill.TLabel", background=bg if debug else panel, foreground=self._palette["forest"], padding=(8, 4), relief="solid", borderwidth=1, bordercolor=border)
        # Keep normal labels on the dominant content-card background.
        # The previous Light theme used a grey panel background for labels inside
        # white cards, which produced visible text-background patches.
        label_bg = card if not debug else panel
        self.style.configure("TLabel", background=label_bg, foreground=fg)
        self.style.configure("Card.TLabel", background=card, foreground=fg)
        self.style.configure("Muted.TLabel", background=label_bg, foreground=muted)
        self.style.configure("TCheckbutton", background=label_bg, foreground=fg)

        button_border = 2 if debug else 1
        self.style.configure("TButton", background=button_bg, foreground=fg, padding=(11, 7), relief="solid", borderwidth=button_border, bordercolor=border, focuscolor=button_bg, focusthickness=0)
        self.style.map("TButton", background=[("disabled", self._palette["disabled"]), ("active", button_active)], foreground=[("disabled", muted)], relief=[("pressed", "solid")])
        self.style.configure("Soft.TButton", background=button_bg, foreground=fg, padding=(9, 6), relief="solid", borderwidth=button_border, bordercolor=border, focuscolor=button_bg, focusthickness=0)
        self.style.map("Soft.TButton", background=[("disabled", self._palette["disabled"]), ("active", button_active)], foreground=[("disabled", muted)])
        self.style.configure("TEntry", fieldbackground=input_bg, foreground=fg, insertcolor=fg, padding=(7, 5), borderwidth=1, relief="solid", bordercolor=border)
        self.style.configure("TCombobox", fieldbackground=input_bg, background=input_bg, foreground=fg, selectbackground=input_bg, selectforeground=fg, padding=(7, 5), borderwidth=1, relief="solid", bordercolor=border, arrowcolor=muted)
        self.style.map("TEntry", bordercolor=[("focus", self._palette["accent"])], fieldbackground=[("disabled", self._palette["disabled"])], foreground=[("disabled", muted)])
        self.style.map("TCombobox", bordercolor=[("focus", self._palette["accent"])], fieldbackground=[("readonly", input_bg), ("disabled", self._palette["disabled"])], background=[("readonly", input_bg), ("disabled", self._palette["disabled"])], foreground=[("readonly", fg), ("disabled", muted)], arrowcolor=[("readonly", muted), ("disabled", muted)])
        self.style.configure("Treeview", background=card, fieldbackground=card, foreground=fg, rowheight=max(24, int(getattr(self.settings, "ui_font_size", 10)) + 15), borderwidth=1 if debug else 0, relief="solid" if debug else "flat", bordercolor=border)
        self.style.configure("Treeview.Heading", background=button_bg, foreground=fg, relief="solid" if debug else "flat", borderwidth=1 if debug else 0)

        scrollbar_bg = "#D6E5EA" if not dark else "#303941"
        scrollbar_active = self._palette["accent"]
        scrollbar_trough = bg
        for style_name in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
            self.style.configure(style_name, gripcount=0, background=scrollbar_bg, darkcolor=scrollbar_bg, lightcolor=scrollbar_bg, troughcolor=scrollbar_trough, bordercolor=scrollbar_trough, arrowcolor=muted, relief="flat", width=10, arrowsize=10)
            self.style.map(style_name, background=[("active", scrollbar_active), ("pressed", scrollbar_active)])

        self.style.configure("Nordic.TPanedwindow", background=self._palette["splitter"], borderwidth=0, relief="flat")
        self.style.configure("TPanedwindow", background=self._palette["splitter"], borderwidth=0, relief="flat")
        self.style.configure("Topbar.TFrame", background=card, borderwidth=0)
        self.style.configure("Topbar.TLabel", background=card, foreground=fg)
        self.style.configure("Help.TLabel", background=card, foreground=muted)
        self.style.configure("MenuIcon.TButton", background=button_bg, foreground=fg, padding=(9, 6), relief="solid", borderwidth=button_border, bordercolor=border, focuscolor=button_bg, focusthickness=0)
        self.style.map("MenuIcon.TButton", background=[("active", button_active), ("pressed", button_active)], relief=[("pressed", "solid")])
        self.style.configure("Drawer.TFrame", background=nav, borderwidth=frame_border, relief=frame_relief, bordercolor=border)
        self.style.configure("Drawer.TLabel", background=nav, foreground=fg)
        self.style.configure("DrawerTitle.TLabel", background=nav, foreground=fg, font=(getattr(self.settings, "ui_font_family", "Verdana"), int(getattr(self.settings, "ui_font_size", 10)) + 5, "bold"))
        self.style.configure("DrawerSubtitle.TLabel", background=nav, foreground=muted, font=(getattr(self.settings, "ui_font_family", "Verdana"), int(getattr(self.settings, "ui_font_size", 10)) + 1))
        self.style.configure("DrawerMuted.TLabel", background=nav, foreground=muted)
        self.style.configure("Drawer.TButton", background=nav, foreground=fg, anchor="w", padding=(14, 11), relief="solid" if debug else "flat", borderwidth=button_border if debug else 0, bordercolor=border, focuscolor=nav, focusthickness=0, font=(getattr(self.settings, "ui_font_family", "Verdana"), int(getattr(self.settings, "ui_font_size", 10)) + 1))
        self.style.map("Drawer.TButton", background=[("active", active), ("pressed", active)], relief=[("pressed", "solid")])
        self.style.configure("Active.Drawer.TButton", background=active, foreground=self._palette["accent"] if not debug else fg, anchor="w", padding=(14, 11), relief="solid" if debug else "flat", borderwidth=button_border if debug else 0, bordercolor=border, focuscolor=panel, focusthickness=0, font=(getattr(self.settings, "ui_font_family", "Verdana"), int(getattr(self.settings, "ui_font_size", 10)) + 1, "bold"))
        self.style.map("Active.Drawer.TButton", background=[("active", active), ("pressed", active)])
        self.style.configure("ViewOn.TButton", background=self._palette["accent"], foreground="#FFFFFF" if not dark else "#101418", padding=(10, 5), relief="solid", borderwidth=button_border, bordercolor=border, focuscolor=self._palette["accent"], focusthickness=0)
        self.style.configure("ViewOff.TButton", background=button_bg, foreground=fg, padding=(10, 5), relief="solid", borderwidth=button_border, bordercolor=border, focuscolor=button_bg, focusthickness=0)
        self.style.map("ViewOn.TButton", background=[("active", self._palette["accent"]), ("pressed", self._palette["accent"])])
        self.style.map("ViewOff.TButton", background=[("active", button_active), ("pressed", button_active)])
        self.style.configure("ToggleOn.TButton", background=self._palette["accent"], foreground="#FFFFFF" if not dark else "#101418", padding=(9, 6), relief="solid", borderwidth=button_border, bordercolor=border, focuscolor=self._palette["accent"], focusthickness=0)
        self.style.configure("ToggleOff.TButton", background=button_bg, foreground=fg, padding=(9, 6), relief="solid", borderwidth=button_border, bordercolor=border, focuscolor=button_bg, focusthickness=0)
        self.style.map("ToggleOn.TButton", background=[("active", self._palette["accent"]), ("pressed", self._palette["accent"])])
        self.style.map("ToggleOff.TButton", background=[("active", button_active), ("pressed", button_active)])
        self.style.configure("Start.TButton", background=self._palette["forest"], foreground="#FFFFFF", padding=(10, 7), relief="solid", borderwidth=button_border, bordercolor=border)
        self.style.map("Start.TButton", background=[("active", self._palette["forest"]), ("disabled", self._palette["disabled"])] , foreground=[("disabled", muted)])
        self.style.configure("Pause.TButton", background=button_bg, foreground=fg, padding=(10, 7), relief="solid", borderwidth=button_border, bordercolor=border)
        self.style.map("Pause.TButton", background=[("active", button_active), ("disabled", self._palette["disabled"])] , foreground=[("disabled", muted)])
        self.style.configure("Stop.TButton", background=self._palette["danger"], foreground="#FFFFFF", padding=(10, 7), relief="solid", borderwidth=button_border, bordercolor=border)
        self.style.map("Stop.TButton", background=[("active", "#FFE1E0" if not dark else "#4A2A2A"), ("disabled", self._palette["disabled"])] , foreground=[("disabled", muted)])
        self.style.configure("OperatorGroup.TFrame", background=card, borderwidth=0)
        self.style.configure("TraceTitle.TLabel", background=card, foreground=fg, font=(getattr(self.settings, "ui_font_family", "Verdana"), int(getattr(self.settings, "ui_font_size", 10)) + 1, "bold"))
        self.style.configure("TinyIcon.TButton", background=button_bg, foreground=fg, padding=(8, 6), relief="solid", borderwidth=button_border, bordercolor=border, focuscolor=button_bg, focusthickness=0, font=(getattr(self.settings, "ui_font_family", "Verdana"), int(getattr(self.settings, "ui_font_size", 10)) + 3))
        self.style.map("TinyIcon.TButton", background=[("active", button_active), ("pressed", button_active)], relief=[("pressed", "solid")])
        self.style.configure("Section.TLabelframe", padding=8, borderwidth=frame_border, relief="solid", background=card, bordercolor=border)
        self.style.configure("Section.TLabelframe.Label", background=card, foreground=muted, font=(getattr(self.settings, "ui_font_family", "Verdana"), int(getattr(self.settings, "ui_font_size", 10)), "bold"))

    def apply_ui_appearance(self) -> None:
        """Apply font/theme variables to the current session without writing settings.json."""
        self.settings.ui_font_family = self.ui_font_family.get()
        self.settings.ui_font_size = int(self.ui_font_size.get())
        self.settings.ui_theme = self.ui_theme.get()
        self._init_style()
        try:
            if hasattr(self, "content_canvas"):
                self.content_canvas.configure(background=self._palette["bg"])
            if hasattr(self, "canvas_widget"):
                self.canvas_widget.configure(background=self._palette["plot_bg"])
            if hasattr(self, "log_text") and self.log_text.winfo_exists():
                self.log_text.configure(background=self._palette["input"], foreground=self._palette["fg"], insertbackground=self._palette["fg"])
        except Exception:
            pass
        try:
            self._refresh_nav_scaling()
        except Exception:
            pass
        self._redraw_all_plots()
        self.log_event(f"Applied UI appearance: {self.settings.ui_theme}, {self.settings.ui_font_family} {self.settings.ui_font_size} pt")

    def preview_ui_appearance(self) -> None:
        """Backward-compatible alias for older tests/scripts."""
        self.apply_ui_appearance()

