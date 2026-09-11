from __future__ import annotations

from types import SimpleNamespace
from tkinter import Toplevel, filedialog, messagebox
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from keith_ivt.ui.menu_utils import make_touch_menu, popup_menu
from keith_ivt.ui.export_naming import suggested_figure_name
from keith_ivt.ui.plot_views import PlotView


from keith_ivt.ui.mixin_typing import UiMixinTyping


class PlotInteractionMixin(UiMixinTyping):
    def _show_plot_context_menu_tk(self, event) -> None:
        """Tk-level fallback so right-click works even when Matplotlib hit-testing misses."""
        ax = self._axes[0] if getattr(self, "_axes", None) else None
        if ax is None:
            return

        e = SimpleNamespace(inaxes=ax, guiEvent=event)
        self._show_plot_context_menu(e)

    def _show_plot_context_menu(self, event) -> None:
        ax = getattr(event, "inaxes", None)
        if ax is None:
            ax = self._axes[0] if getattr(self, "_axes", None) else None
        if ax is None:
            return
        view = getattr(ax, "_happy_view", None)
        title = f"Plot image: {view.value}" if view is not None else "Plot image"
        menu = make_touch_menu(self.root, self.ui_font_family.get(), int(self.ui_font_size.get()))
        menu.add_command(label=title, state="disabled")
        menu.add_separator()
        if view is PlotView.SIGNAL_TIME and hasattr(self, "_show_time_plot_settings"):
            menu.add_command(label="Time plot settings...", command=self._show_time_plot_settings)
            menu.add_separator()
        menu.add_command(label="Autorange this view", command=lambda: self._autoscale_axis(ax))
        menu.add_command(
            label="Swap X/Y axes", command=lambda v=view: self._swap_xy_for_axis_view(v)
        )
        menu.add_command(label="Open fullscreen", command=lambda a=ax: self.open_plot_fullscreen(a))
        menu.add_command(label="Save plot image...", command=self.save_figure)
        menu.add_separator()
        menu.add_command(
            label="Set X range...",
            command=lambda a=ax: self._schedule_axis_range_dialog(axis="x", ax=a),
        )
        menu.add_command(
            label="Set Y range...",
            command=lambda a=ax: self._schedule_axis_range_dialog(axis="y", ax=a),
        )
        menu.add_separator()
        arrangement_menu = make_touch_menu(
            self.root, self.ui_font_family.get(), int(self.ui_font_size.get())
        )
        for label in ["Auto", "Vertical", "Horizontal"]:
            arrangement_menu.add_radiobutton(
                label=label, variable=self.arrangement, value=label, command=self._redraw_all_plots
            )
        menu.add_cascade(label="Arrangement", menu=arrangement_menu)
        style_menu = make_touch_menu(
            self.root, self.ui_font_family.get(), int(self.ui_font_size.get())
        )
        for label in ["Lines", "Markers", "Lines + markers"]:
            style_menu.add_radiobutton(
                label=label, variable=self.plot_format, value=label, command=self._redraw_all_plots
            )
        menu.add_cascade(label="Plot style", menu=style_menu)
        fmt_menu = make_touch_menu(
            self.root, self.ui_font_family.get(), int(self.ui_font_size.get())
        )
        for label in ["Auto", "Scientific", "Engineering"]:
            fmt_menu.add_radiobutton(
                label=label,
                variable=self.plot_number_format,
                value=label,
                command=self._redraw_all_plots,
            )
        menu.add_cascade(label="Number format", menu=fmt_menu)
        xunit_menu = make_touch_menu(
            self.root, self.ui_font_family.get(), int(self.ui_font_size.get())
        )
        for label in self._unit_choices_for_label(ax.get_xlabel()):
            xunit_menu.add_radiobutton(
                label=label, variable=self.plot_x_unit, value=label, command=self._redraw_all_plots
            )
        menu.add_cascade(label="X unit", menu=xunit_menu)
        yunit_menu = make_touch_menu(
            self.root, self.ui_font_family.get(), int(self.ui_font_size.get())
        )
        for label in self._unit_choices_for_label(ax.get_ylabel()):
            yunit_menu.add_radiobutton(
                label=label, variable=self.plot_y_unit, value=label, command=self._redraw_all_plots
            )
        menu.add_cascade(label="Y unit", menu=yunit_menu)
        gui_event = getattr(event, "guiEvent", None)
        x_root = getattr(gui_event, "x_root", self.root.winfo_pointerx())
        y_root = getattr(gui_event, "y_root", self.root.winfo_pointery())
        popup_menu(menu, int(x_root), int(y_root))

    def _autoscale_axis(self, ax) -> None:
        ax.relim()
        ax.autoscale(enable=True, axis="both", tight=False)
        ax.autoscale_view(scalex=True, scaley=True)
        self.canvas.draw_idle()

    def _on_plot_double_click(self, event) -> None:
        # Tk-level fallback: if Matplotlib did not receive a hit-tested event, open a large copy.
        self.open_plot_fullscreen()

    def open_plot_fullscreen(self, ax=None) -> None:
        win = Toplevel(self.root)
        win.title("Plot fullscreen")
        win.geometry("1100x760")
        win.rowconfigure(0, weight=1)
        win.columnconfigure(0, weight=1)
        fig = Figure(figsize=(10, 7), dpi=100, facecolor=self._palette["plot_bg"])
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        self._plot_data_on_figure(fig)
        canvas.draw()
        btns = ttk.Frame(win, padding=(8, 6))
        btns.grid(row=1, column=0, sticky="ew")

        def _save_fullscreen_snapshot() -> None:
            path = filedialog.asksaveasfilename(
                defaultextension=".png",
                initialfile=suggested_figure_name(),
                filetypes=[("PNG image", "*.png"), ("PDF", "*.pdf"), ("SVG", "*.svg")],
            )
            if not path:
                return
            fig.savefig(path, facecolor=fig.get_facecolor(), bbox_inches="tight")
            self.log_event(f"Saved fullscreen plot snapshot: {path}")

        ttk.Button(btns, text="Save screenshot...", command=_save_fullscreen_snapshot).pack(
            side="right", padx=(0, 6)
        )
        ttk.Button(btns, text="Close", command=win.destroy).pack(side="right")

    def _schedule_axis_range_dialog(self, axis: str | None = None, ax=None) -> None:
        """Open the axis range editor after the context menu command returns.

        Native Tk popup menus on Windows are only reliably unposted after the
        menu command callback has returned to the event loop.  Opening a modal
        dialog directly from the callback can leave the menu painted on top of
        the app until the window loses focus.  Do not force focus, destroy the
        menu, or call ``update()`` here; those actions interact badly with the
        hover-collapsible dock.
        """
        try:
            self.root.after(250, lambda: self.set_axis_range_dialog(axis=axis, ax=ax))
        except Exception:
            self.set_axis_range_dialog(axis=axis, ax=ax)

    def _axis_range_prompt_and_initial(self, axis: str | None, ax) -> tuple[str, str]:
        x0, x1 = ax.get_xlim()
        y0, y1 = ax.get_ylim()
        if axis == "x":
            return "Enter xmin,xmax", f"{x0:.6g},{x1:.6g}"
        if axis == "y":
            return "Enter ymin,ymax", f"{y0:.6g},{y1:.6g}"
        return "Enter xmin,xmax,ymin,ymax", f"{x0:.6g},{x1:.6g},{y0:.6g},{y1:.6g}"

    def _apply_axis_range_text(self, axis: str | None, ax, text: str) -> None:
        vals = [float(v.strip()) for v in text.replace(";", ",").split(",") if v.strip()]
        if axis == "x":
            if len(vals) != 2:
                raise ValueError("Need two numbers: xmin,xmax")
            ax.set_xlim(vals[0], vals[1])
        elif axis == "y":
            if len(vals) != 2:
                raise ValueError("Need two numbers: ymin,ymax")
            ax.set_ylim(vals[0], vals[1])
        else:
            if len(vals) != 4:
                raise ValueError("Need four numbers: xmin,xmax,ymin,ymax")
            ax.set_xlim(vals[0], vals[1])
            ax.set_ylim(vals[2], vals[3])
        self.canvas.draw_idle()

    def set_axis_range_dialog(self, axis: str | None = None, ax=None) -> None:
        if ax is None:
            if not self._axes:
                messagebox.showinfo("No plot", "No plot axis is available yet.")
                return
            ax = self._axes[0]
        prompt, initial = self._axis_range_prompt_and_initial(axis, ax)

        # Use a small non-modal Toplevel editor. The previous built-in modal
        # prompt waited on visibility/grab transitions internally; when launched
        # from a Tk popup menu in packaged Windows builds, that could leave the
        # context menu visible or raise wait_visibility TclError.
        win = Toplevel(self.root)
        win.title("Set axis range")
        win.resizable(False, False)
        try:
            win.transient(self.root)
        except Exception:
            pass

        frame = ttk.Frame(win, padding=(10, 8))
        frame.grid(row=0, column=0, sticky="nsew")
        ttk.Label(frame, text=prompt).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        value_var = getattr(self, "_axis_range_dialog_var", None)
        if value_var is None:
            import tkinter as tk

            value_var = tk.StringVar()
            self._axis_range_dialog_var = value_var
        value_var.set(initial)
        entry = ttk.Entry(frame, textvariable=value_var, width=max(28, len(initial) + 4))
        entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        frame.columnconfigure(0, weight=1)

        def _close() -> None:
            try:
                win.destroy()
            except Exception:
                pass

        def _ok() -> None:
            try:
                self._apply_axis_range_text(axis, ax, value_var.get())
            except Exception as exc:
                messagebox.showerror("Invalid axis range", str(exc), parent=win)
                return
            _close()

        ttk.Button(frame, text="OK", command=_ok).grid(row=2, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(frame, text="Cancel", command=_close).grid(row=2, column=1, sticky="ew")
        win.bind("<Return>", lambda _event: _ok())
        win.bind("<Escape>", lambda _event: _close())
        win.protocol("WM_DELETE_WINDOW", _close)
        try:
            entry.selection_range(0, "end")
            win.after(50, entry.focus_set)
        except Exception:
            pass

    def _axis_under_mouse(self, event):
        """Return the single Matplotlib axis under a Tk mouse event."""
        if not getattr(self, "_axes", None):
            return None
        try:
            x = float(getattr(event, "x", 0))
            height = float(self.canvas_widget.winfo_height())
            y = height - float(getattr(event, "y", 0))
            for ax in self._axes:
                if ax.get_window_extent().contains(x, y):
                    return ax
        except Exception:
            pass
        return self._axes[0] if self._axes else None

    def _on_plot_mousewheel(self, event) -> None:
        ax = self._axis_under_mouse(event)
        if ax is None:
            return
        scale = 0.9 if getattr(event, "delta", 0) > 0 or getattr(event, "num", None) == 4 else 1.1
        state = int(getattr(event, "state", 0) or 0)
        zoom_x = bool(state & 0x0004)  # Control: X range
        zoom_y = not zoom_x  # Default and Shift: Y range
        x0, x1 = ax.get_xlim()
        y0, y1 = ax.get_ylim()
        if zoom_x:
            cx = (x0 + x1) / 2
            hx = (x1 - x0) * scale / 2
            ax.set_xlim(cx - hx, cx + hx)
        if zoom_y:
            cy = (y0 + y1) / 2
            hy = (y1 - y0) * scale / 2
            ax.set_ylim(cy - hy, cy + hy)
        self.canvas.draw_idle()
