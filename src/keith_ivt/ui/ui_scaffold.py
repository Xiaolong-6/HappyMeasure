from __future__ import annotations

from tkinter import ttk
from keith_ivt.ui.widgets import add_tip


class UiScaffoldMixin:
    def _build_content_scaffold(self) -> None:
        self.content_frame.rowconfigure(0, weight=0)
        self.content_frame.rowconfigure(1, weight=1)
        self.content_frame.columnconfigure(0, weight=1)

        self.page_header = ttk.Frame(self.content_frame, style="Topbar.TFrame", padding=(12, 10, 12, 6))
        self.page_header.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.page_header.columnconfigure(1, weight=1)
        self.menu_button = ttk.Button(self.page_header, text="☰", width=3, style="MenuIcon.TButton", command=self._toggle_drawer)
        self.menu_button.grid(row=0, column=0, sticky="w", padx=(0, 8))
        add_tip(self.menu_button, "Open navigation menu")
        self.page_title = ttk.Label(self.page_header, text=self._active_nav, style="Topbar.TLabel", font=(getattr(self.settings, "ui_font_family", "Verdana"), int(getattr(self.settings, "ui_font_size", 10)) + 5, "bold"))
        self.page_title.grid(row=0, column=1, sticky="w")
        try:
            add_tip(self.page_title, getattr(self, "NAV_TIPS", {}).get(self._active_nav, "Current workspace panel"))
        except Exception:
            pass

        import tkinter as tk
        self.content_canvas = tk.Canvas(self.content_frame, highlightthickness=0, borderwidth=0, background=self._palette["bg"])
        self.content_scrollbar = ttk.Scrollbar(self.content_frame, orient="vertical", command=self.content_canvas.yview, style="Vertical.TScrollbar")
        self.content_canvas.configure(yscrollcommand=self.content_scrollbar.set)
        self.content_canvas.grid(row=1, column=0, sticky="nsew")
        self.content_scrollbar.grid(row=1, column=1, sticky="ns")
        self.current_content = ttk.Frame(self.content_canvas, style="App.TFrame")
        self._content_window_id = self.content_canvas.create_window((0, 0), window=self.current_content, anchor="nw")
        self.current_content.bind("<Configure>", lambda _e: self._refresh_content_scrollregion())
        self.content_canvas.bind("<Configure>", lambda e: (
            self.content_canvas.itemconfigure(self._content_window_id, width=e.width),
            self._update_content_window_height(getattr(self, "_active_nav", None)),
        ))
        self.content_canvas.bind("<MouseWheel>", self._on_content_mousewheel, add="+")
        self.current_content.bind("<MouseWheel>", self._on_content_mousewheel, add="+")
        self.current_content.bind("<Button-4>", self._on_content_mousewheel, add="+")
        self.current_content.bind("<Button-5>", self._on_content_mousewheel, add="+")

    def _refresh_content_scrollregion(self) -> None:
        """Refresh the page scrollregion after dynamic panel rebuilds.

        The Sweep panel can rebuild its adaptive table in response to combobox
        changes.  On Windows/Tk, the canvas sometimes keeps the old scrollregion
        until the next idle pass, which leaves a visible scrollbar that cannot
        actually move.  Refresh now and again after idle so the page-level
        scrollbar always tracks the real requested content height.
        """
        try:
            self.current_content.update_idletasks()
            bbox = self.content_canvas.bbox("all")
            self.content_canvas.configure(scrollregion=bbox if bbox is not None else (0, 0, 0, 0))
        except Exception:
            pass

    def _refresh_content_scrollregion_later(self) -> None:
        try:
            self.root.after_idle(self._refresh_content_scrollregion)
            self.root.after(60, self._refresh_content_scrollregion)
        except Exception:
            pass

    def _on_content_mousewheel(self, event) -> str | None:
        try:
            delta = -1 * int(event.delta / 120) if getattr(event, "delta", 0) else (1 if getattr(event, "num", None) == 5 else -1)
            self.content_canvas.yview_scroll(delta, "units")
            return "break"
        except Exception:
            return None

    def _bind_content_mousewheel_recursive(self, widget) -> None:
        """Bind content-page scrolling to all page descendants.

        Large UI scales can make the Sweep page taller than the viewport.
        Entries/comboboxes consume focus, so binding only the canvas is not
        enough on Windows.  Limit this to the left content page so plot-wheel
        zoom remains local to plots.
        """
        try:
            widget.bind("<MouseWheel>", self._on_content_mousewheel, add="+")
            widget.bind("<Button-4>", self._on_content_mousewheel, add="+")
            widget.bind("<Button-5>", self._on_content_mousewheel, add="+")
            for child in widget.winfo_children():
                self._bind_content_mousewheel_recursive(child)
        except Exception:
            pass
