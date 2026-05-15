from __future__ import annotations

from tkinter import Toplevel, messagebox, simpledialog
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from keith_ivt.ui.menu_utils import make_touch_menu, popup_menu
from keith_ivt.ui.export_naming import suggested_figure_name


class PlotInteractionMixin:
    def _show_plot_context_menu_tk(self, event) -> None:
        """Tk-level fallback so right-click works even when Matplotlib hit-testing misses."""
        ax = self._axes[0] if getattr(self, "_axes", None) else None
        if ax is None:
            return
        class _Event:
            pass
        e = _Event()
        e.inaxes = ax
        e.guiEvent = event
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
        menu.add_command(label="Autorange this view", command=lambda: self._autoscale_axis(ax))
        menu.add_command(label="Open fullscreen", command=self.open_plot_fullscreen)
        menu.add_command(label="Save plot image...", command=self.save_figure)
        menu.add_separator()
        menu.add_command(label="Set X range...", command=lambda: self.set_axis_range_dialog(axis="x", ax=ax))
        menu.add_command(label="Set Y range...", command=lambda: self.set_axis_range_dialog(axis="y", ax=ax))
        menu.add_separator()
        arrangement_menu = make_touch_menu(self.root, self.ui_font_family.get(), int(self.ui_font_size.get()))
        for label in ["Auto", "Vertical", "Horizontal"]:
            arrangement_menu.add_radiobutton(label=label, variable=self.arrangement, value=label, command=self._redraw_all_plots)
        menu.add_cascade(label="Arrangement", menu=arrangement_menu)
        style_menu = make_touch_menu(self.root, self.ui_font_family.get(), int(self.ui_font_size.get()))
        for label in ["Lines", "Markers", "Lines + markers"]:
            style_menu.add_radiobutton(label=label, variable=self.plot_format, value=label, command=self._redraw_all_plots)
        menu.add_cascade(label="Plot style", menu=style_menu)
        fmt_menu = make_touch_menu(self.root, self.ui_font_family.get(), int(self.ui_font_size.get()))
        for label in ["Auto", "Scientific", "Engineering"]:
            fmt_menu.add_radiobutton(label=label, variable=self.plot_number_format, value=label, command=self._redraw_all_plots)
        menu.add_cascade(label="Number format", menu=fmt_menu)
        xunit_menu = make_touch_menu(self.root, self.ui_font_family.get(), int(self.ui_font_size.get()))
        for label in self._unit_choices_for_label(ax.get_xlabel()):
            xunit_menu.add_radiobutton(label=label, variable=self.plot_x_unit, value=label, command=self._redraw_all_plots)
        menu.add_cascade(label="X unit", menu=xunit_menu)
        yunit_menu = make_touch_menu(self.root, self.ui_font_family.get(), int(self.ui_font_size.get()))
        for label in self._unit_choices_for_label(ax.get_ylabel()):
            yunit_menu.add_radiobutton(label=label, variable=self.plot_y_unit, value=label, command=self._redraw_all_plots)
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

    def open_plot_fullscreen(self) -> None:
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
        ttk.Button(btns, text="Close", command=win.destroy).pack(side="right")

    def set_axis_range_dialog(self, axis: str | None = None, ax=None) -> None:
        if ax is None:
            if not self._axes:
                messagebox.showinfo("No plot", "No plot axis is available yet."); return
            ax = self._axes[0]
        x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
        if axis == "x":
            prompt = "Enter xmin,xmax"
            initial = f"{x0:.6g},{x1:.6g}"
        elif axis == "y":
            prompt = "Enter ymin,ymax"
            initial = f"{y0:.6g},{y1:.6g}"
        else:
            prompt = "Enter xmin,xmax,ymin,ymax"
            initial = f"{x0:.6g},{x1:.6g},{y0:.6g},{y1:.6g}"
        text = simpledialog.askstring("Set axis range", prompt, initialvalue=initial)
        if not text:
            return
        try:
            vals = [float(v.strip()) for v in text.replace(";", ",").split(",")]
            if axis == "x":
                if len(vals) != 2: raise ValueError("Need two numbers: xmin,xmax")
                ax.set_xlim(vals[0], vals[1])
            elif axis == "y":
                if len(vals) != 2: raise ValueError("Need two numbers: ymin,ymax")
                ax.set_ylim(vals[0], vals[1])
            else:
                if len(vals) != 4: raise ValueError("Need four numbers: xmin,xmax,ymin,ymax")
                ax.set_xlim(vals[0], vals[1]); ax.set_ylim(vals[2], vals[3])
            self.canvas.draw_idle()
        except Exception as exc:
            messagebox.showerror("Invalid axis range", str(exc))

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
        zoom_y = not zoom_x          # Default and Shift: Y range
        x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
        if zoom_x:
            cx = (x0 + x1) / 2; hx = (x1 - x0) * scale / 2
            ax.set_xlim(cx - hx, cx + hx)
        if zoom_y:
            cy = (y0 + y1) / 2; hy = (y1 - y0) * scale / 2
            ax.set_ylim(cy - hy, cy + hy)
        self.canvas.draw_idle()

