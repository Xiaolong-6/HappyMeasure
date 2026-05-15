from __future__ import annotations

from tkinter import ttk
from keith_ivt.ui.widgets import add_tip


class WidgetHelperMixin:
    @staticmethod
    def _display_terminal(value: str) -> str:
        return "FRONT" if str(value).upper() in {"FRON", "FRONT"} else "REAR"

    @staticmethod
    def _terminal_scpi(value: str) -> str:
        return "FRON" if str(value).upper() in {"FRON", "FRONT"} else "REAR"

    @staticmethod
    def _display_sense(value: str) -> str:
        return "4-wire" if str(value).upper() in {"4W", "4-WIRE", "4WIRE"} else "2-wire"

    @staticmethod
    def _sense_scpi(value: str) -> str:
        return "4W" if str(value).lower().startswith("4") else "2W"

    def _wrap_label(self, parent, text: str, **kwargs):
        kwargs.setdefault("style", "Muted.TLabel")
        lab = ttk.Label(parent, text=text, wraplength=360, justify="left", **kwargs)
        lab.bind("<Configure>", lambda e, l=lab: l.configure(wraplength=max(180, e.width)))
        return lab

    def _section_title(self, parent, title: str) -> None:
        # The page title lives in the fixed top bar next to the hamburger icon;
        # individual panels start directly with their content cards.
        if hasattr(self, "page_title") and self.page_title.winfo_exists():
            self.page_title.configure(text=title)

    def _entry(self, parent, label, var, row: int, tip: str = ""):
        lab_text = label.get() if hasattr(label, "get") else str(label)
        lab = ttk.Label(parent, text=lab_text, style="Card.TLabel")
        lab.grid(row=row, column=0, sticky="w", padx=(0, 8), pady=3)
        if hasattr(label, "trace_add"):
            label.trace_add("write", lambda *_args, lab=lab, label=label: lab.winfo_exists() and lab.configure(text=label.get()))
        ent = ttk.Entry(parent, textvariable=var)
        ent.grid(row=row, column=1, sticky="ew", pady=3)
        add_tip(ent, tip)
        return (lab, ent)

    def _combo(self, parent, label: str, var, values, row: int, tip: str = ""):
        ttk.Label(parent, text=label, style="Card.TLabel").grid(row=row, column=0, sticky="w", padx=(0, 8), pady=3)
        cb = ttk.Combobox(parent, textvariable=var, values=list(values), state="readonly")
        cb.grid(row=row, column=1, sticky="ew", pady=3)
        cb.bind("<MouseWheel>", self._on_content_mousewheel, add="+")
        cb.bind("<Button-4>", self._on_content_mousewheel, add="+")
        cb.bind("<Button-5>", self._on_content_mousewheel, add="+")
        add_tip(cb, tip)
        return cb

    def _toggle_button_text(self, label: str, value: bool) -> str:
        return f"✓ {label}" if value else f"○ {label}"

    def _sync_toggle_button(self, button, label: str, var) -> None:
        try:
            selected = bool(var.get())
            button.configure(
                text=self._toggle_button_text(label, selected),
                style="ToggleOn.TButton" if selected else "ToggleOff.TButton",
            )
        except Exception:
            pass

    def _check(self, parent, label: str, var, row: int, tip: str = "", command=None):
        """Render boolean options as touch-friendly colored toggle buttons.

        The old native check control looked inconsistent in high-contrast/debug
        layouts.  Use a normal Button so all sweep/settings boolean options
        share the same border language as Connect and view toggles.
        """
        def on_click() -> None:
            try:
                var.set(not bool(var.get()))
                self._sync_toggle_button(btn, label, var)
                if command is not None:
                    command()
            except Exception:
                pass

        btn = ttk.Button(
            parent,
            text=self._toggle_button_text(label, bool(var.get())),
            style="ToggleOn.TButton" if bool(var.get()) else "ToggleOff.TButton",
            command=on_click,
            takefocus=False,
        )
        btn.grid(row=row, column=0, columnspan=2, sticky="ew", pady=3)
        btn.bind("<MouseWheel>", self._on_content_mousewheel, add="+")
        btn.bind("<Button-4>", self._on_content_mousewheel, add="+")
        btn.bind("<Button-5>", self._on_content_mousewheel, add="+")
        try:
            var.trace_add("write", lambda *_: btn.winfo_exists() and self._sync_toggle_button(btn, label, var))
        except Exception:
            pass
        add_tip(btn, tip)
        return btn

    def _range_control_row(self, parent, label: str, value_var, auto_var, row: int, tip: str = ""):
        lab = ttk.Label(parent, text=label, style="Card.TLabel")
        lab.grid(row=row, column=0, sticky="w", padx=(0, 8), pady=3)
        ent = ttk.Entry(parent, textvariable=value_var)
        ent.grid(row=row, column=1, sticky="ew", pady=3)

        def on_auto() -> None:
            auto_var.set(not bool(auto_var.get()))
            self._sync_toggle_button(auto_btn, "Auto", auto_var)
            self._update_range_state()

        auto_btn = ttk.Button(
            parent,
            text=self._toggle_button_text("Auto", bool(auto_var.get())),
            style="ToggleOn.TButton" if bool(auto_var.get()) else "ToggleOff.TButton",
            command=on_auto,
            takefocus=False,
            width=8,
        )
        auto_btn.grid(row=row, column=2, sticky="ew", padx=(6, 0), pady=3)
        try:
            auto_var.trace_add("write", lambda *_: auto_btn.winfo_exists() and self._sync_toggle_button(auto_btn, "Auto", auto_var))
        except Exception:
            pass
        add_tip(ent, tip)
        add_tip(auto_btn, f"Toggle automatic {label.lower()} selection.")
        return (lab, ent, auto_btn)

    # ------------------------------------------------------------------
    # Dynamic sweep UI and variables
    # ------------------------------------------------------------------
