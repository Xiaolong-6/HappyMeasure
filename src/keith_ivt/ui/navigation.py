from __future__ import annotations

from tkinter import ttk

from keith_ivt.ui.widgets import add_tip
from keith_ivt.version import APP_NAME


NAV_ITEMS = {
    "Hardware": ("🔌", "Hardware"),
    "Sweep": ("📈", "Sweep"),
    "Preset": ("💾", "Preset"),
    "Restore": ("🧰", "Restore"),
    "Settings": ("⚙️", "Settings"),
    "Log": ("📋", "Log"),
    "About": ("ℹ️", "About"),
}


class NavigationMixin:
    """Persistent push-side navigation rail.

    Contract: navigation changes only the page body and title; connection
    status remains owned by StatusBarMixin.  The rail reserves a real grid
    column when open, so it pushes the workspace instead of floating over it.
    It is hidden only by the hamburger button or Escape, not by outside clicks.
    """

    NAV_ITEMS = NAV_ITEMS

    def _build_navigation_drawer(self) -> None:
        """Build a persistent Outlook-style side rail."""
        self._drawer_open = True
        self._drawer_animating = False
        self._drawer_width = self._nav_drawer_width()
        self.drawer_frame = ttk.Frame(self.root, style="Drawer.TFrame", width=self._drawer_width)
        self.drawer_frame.grid(row=0, column=0, rowspan=3, sticky="nsw")
        self.drawer_frame.grid_propagate(False)
        self.drawer_frame.bind("<Escape>", lambda _e: self._hide_drawer(), add="+")

        self.drawer_title = ttk.Label(self.drawer_frame, text=APP_NAME, style="DrawerTitle.TLabel")
        self.drawer_title.pack(anchor="w", padx=16, pady=(18, 4))
        self.drawer_subtitle = ttk.Label(
            self.drawer_frame,
            text="Measurement workspace",
            style="DrawerSubtitle.TLabel",
        )
        self.drawer_subtitle.pack(anchor="w", padx=16, pady=(0, 14))

        self.nav_buttons: dict[str, ttk.Button] = {}
        for name, (icon, label) in self.NAV_ITEMS.items():
            btn = ttk.Button(
                self.drawer_frame,
                text=f"{icon}  {label}",
                style="Drawer.TButton",
                command=lambda n=name: self._show_nav(n),
            )
            btn.pack(fill="x", padx=(8, 10), pady=2)
            add_tip(btn, f"Open {label} panel")
            self.nav_buttons[name] = btn
        self.nav_version_label = ttk.Label(
            self.drawer_frame,
            textvariable=self.version_text,
            style="DrawerSubtitle.TLabel",
        )
        self.nav_version_label.pack(side="bottom", anchor="w", padx=16, pady=14)

        self.root.bind("<Escape>", lambda _e: self._hide_drawer(), add="+")

    def _nav_drawer_width(self) -> int:
        try:
            size = int(self.ui_font_size.get()) if hasattr(self, "ui_font_size") else int(getattr(self.settings, "ui_font_size", 10))
        except Exception:
            size = 10
        # Wider only when the font actually needs it.  The side rail stays
        # compact on laboratory 1080p screens but avoids clipping at high UI
        # scales on 4K displays.
        return max(190, min(300, 132 + size * 9))

    def _refresh_nav_scaling(self) -> None:
        self._drawer_width = self._nav_drawer_width()
        try:
            if getattr(self, "drawer_frame", None) is not None and self.drawer_frame.winfo_exists():
                if getattr(self, "_drawer_open", False):
                    self.drawer_frame.configure(width=self._drawer_width)
                    self.drawer_frame.grid(row=0, column=0, rowspan=3, sticky="nsw")
                else:
                    self.drawer_frame.configure(width=0)
        except Exception:
            pass

    def _toggle_drawer(self) -> None:
        if getattr(self, "_drawer_open", False):
            self._hide_drawer()
        else:
            self._show_drawer()

    def _animate_drawer_width(self, start_w: int, end_w: int, final_open: bool) -> None:
        """Compatibility wrapper for the old animated drawer API.

        The push rail used to resize itself over several Tk ``after`` ticks. On
        4K displays that forced a full workspace reflow on every animation
        frame, which made the drawer feel laggy and occasionally delayed UI
        input.  The rail is now committed in one layout transaction: it still
        pushes the workspace, but the click response is immediate and reliable.
        """
        self._commit_drawer_width(end_w, final_open)

    def _commit_drawer_width(self, width: int, final_open: bool) -> None:
        """Open or close the push navigation rail with one Tk layout commit."""
        if not hasattr(self, "drawer_frame"):
            return
        self._drawer_animating = False
        self._drawer_open = final_open
        try:
            if final_open:
                self._drawer_width = max(1, int(width or self._nav_drawer_width()))
                self.drawer_frame.configure(width=self._drawer_width)
                self.drawer_frame.grid(row=0, column=0, rowspan=3, sticky="nsw")
                self.drawer_frame.focus_set()
            else:
                self.drawer_frame.configure(width=0)
                self.drawer_frame.grid_remove()
        except Exception:
            if not final_open:
                try:
                    self.drawer_frame.grid_remove()
                except Exception:
                    pass

    def _show_drawer(self) -> None:
        self._drawer_width = self._nav_drawer_width()
        self._commit_drawer_width(int(self._drawer_width), True)

    def _hide_drawer(self) -> None:
        self._commit_drawer_width(0, False)

    def _close_drawer_on_outside_click(self, event) -> None:
        """Legacy hook retained as a no-op: the rail no longer auto-hides."""
        return

    def _show_nav(self, name: str) -> None:
        self._active_nav = name
        if hasattr(self, "page_title") and self.page_title.winfo_exists():
            self.page_title.configure(text=name)
        for n, btn in self.nav_buttons.items():
            btn.configure(style="Active.Drawer.TButton" if n == name else "Drawer.TButton")
        for child in self.current_content.winfo_children():
            child.destroy()
        builders = {
            "Hardware": self._build_hardware_panel,
            "Sweep": self._build_sweep_panel,
            "Preset": self._build_preset_panel,
            "Restore": self._build_restore_panel,
            "Settings": self._build_settings_panel,
            "Log": self._build_log_panel,
            "About": self._build_about_panel,
        }
        builders[name](self.current_content)
        self._bind_content_mousewheel_recursive(self.current_content)
        self._update_content_window_height(name)
        self._update_dynamic_sweep_fields()
        self._update_range_state()
        self._set_sweep_fields_state()

    def _update_content_window_height(self, name: str | None = None) -> None:
        """Let full-page panels such as Log/About occupy the visible canvas height."""
        try:
            fill_height = name in {"Log", "About"}
            height = self.content_canvas.winfo_height() if fill_height else 1
            self.content_canvas.itemconfigure(self._content_window_id, height=height if fill_height else "")
        except Exception:
            pass
