from __future__ import annotations

import tkinter as tk
from tkinter import END, StringVar, filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import EngFormatter, ScalarFormatter

from keith_ivt.models import SweepKind, SweepResult
from keith_ivt.ui.export_naming import suggested_figure_name
from keith_ivt.ui.plot_views import PlotView, layout_grid, xy_for_view
from keith_ivt.ui.widgets import add_tip


class PlotPanelMixin:
    def _build_plot_panel(self) -> None:
        self.plot_frame.rowconfigure(1, weight=1)
        self.plot_frame.columnconfigure(0, weight=1)

        toolbar = ttk.Frame(self.plot_frame, style="Toolbar.TFrame", padding=(10, 8))
        # Let the view toolbar take the available width so buttons wrap with the
        # window instead of floating in a fixed-size island.
        toolbar.grid(row=0, column=0, sticky="ew", padx=(4, 8), pady=(0, 6))
        toolbar.columnconfigure(1, weight=1)

        ttk.Label(toolbar, text="Views", style="Card.TLabel").grid(row=0, column=0, padx=(0, 8), sticky="w")
        self.views_frame = ttk.Frame(toolbar, style="ToolbarInner.TFrame")
        self.views_frame.grid(row=0, column=1, sticky="ew")
        self.views_frame.bind("<Configure>", lambda _e: self._update_plot_view_layout(), add="+")
        toolbar.bind("<Configure>", lambda _e: self._update_plot_view_layout(), add="+")
        self.plot_view_buttons = {}
        short_names = {
            PlotView.LINEAR: "Linear",
            PlotView.LOG_ABS: "Log",
            PlotView.V_OVER_I: "V/I",
            PlotView.DV_DI: "dV/dI",
            PlotView.SIGNAL_TIME: "Time",
        }
        for col, view in enumerate([PlotView.LINEAR, PlotView.LOG_ABS, PlotView.V_OVER_I, PlotView.DV_DI, PlotView.SIGNAL_TIME]):
            btn = ttk.Button(self.views_frame, text=short_names[view], width=max(3, len(short_names[view])), style="ToggleOn.TButton" if self.plot_view_vars[view].get() else "ToggleOff.TButton", command=lambda v=view: self._toggle_plot_view(v), takefocus=False)
            btn.grid(row=0, column=col, padx=(0 if col == 0 else 5, 0), pady=(0, 0), sticky="w")
            self.plot_view_buttons[view] = btn
            add_tip(btn, f"Toggle the {view.value} plot view.")

        # Keep this toolbar view-only; plot image actions live in the plot context menu,
        # while data import/export actions live in the trace-list context menu.

        self.plot_trace_pane = ttk.PanedWindow(self.plot_frame, orient="vertical", style="Nordic.TPanedwindow")
        self.plot_trace_pane.grid(row=1, column=0, sticky="nsew", padx=(4, 8), pady=(0, 8))

        self.plot_body = ttk.Frame(self.plot_trace_pane, style="App.TFrame")
        self.plot_body.rowconfigure(0, weight=1)
        self.plot_body.columnconfigure(0, weight=1)
        self.plot_body.columnconfigure(1, weight=0)
        self.plot_body.bind("<Configure>", lambda _e: self._update_plot_body_layout(), add="+")

        self.figure = Figure(figsize=(7, 5), dpi=100, facecolor=self._palette["plot_bg"])
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.plot_body)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.configure(background=self._palette["plot_bg"], highlightthickness=0)
        self.canvas_widget.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)
        self.canvas_widget.bind("<MouseWheel>", self._on_plot_mousewheel, add="+")
        self.canvas_widget.bind("<Button-4>", self._on_plot_mousewheel, add="+")
        self.canvas_widget.bind("<Button-5>", self._on_plot_mousewheel, add="+")
        self.canvas_widget.bind("<Button-3>", self._show_plot_context_menu_tk, add="+")
        self.canvas_widget.bind("<Control-Button-1>", self._show_plot_context_menu_tk, add="+")
        self._mpl_double_click_cid = self.canvas.mpl_connect("button_press_event", self._on_mpl_plot_click)
        self._mpl_toolbar = None

        # Initialize plot performance optimizer
        from keith_ivt.ui.plot_optimizer import FastPlotRenderer
        self._plot_renderer = FastPlotRenderer(self.figure, max_points=2000)

        self.trace_panel = ttk.Frame(self.plot_trace_pane, style="Card.TFrame", padding=(10, 8))
        self.trace_panel.rowconfigure(1, weight=1)
        self.trace_panel.columnconfigure(0, weight=1)
        header = ttk.Frame(self.trace_panel, style="Card.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        header.columnconfigure(0, weight=1)
        self.trace_title_text = StringVar(value="Traces (0)")
        ttk.Label(header, textvariable=self.trace_title_text, style="TraceTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(header, text="⚙", width=3, style="TinyIcon.TButton", command=self._show_trace_column_menu_from_button).grid(row=0, column=1, sticky="e")

        legend_box = ttk.Frame(self.trace_panel, style="Card.TFrame")
        legend_box.grid(row=1, column=0, sticky="nsew")
        legend_box.rowconfigure(0, weight=1)
        legend_box.columnconfigure(0, weight=1)
        self.trace_tree = ttk.Treeview(legend_box, columns=("show", "color", "name", "operator", "mode", "sweep", "points", "start"), show="headings", selectmode="extended", height=7)
        self._trace_columns = {
            "show": ("Vis", 44),
            "color": ("Color", 78),
            "name": ("Name", 150),
            "operator": ("Operator", 90),
            "mode": ("Mode", 70),
            "sweep": ("Type", 78),
            "points": ("Pts", 58),
            "start": ("Start", 145),
        }
        for col_name, (title, width) in self._trace_columns.items():
            self.trace_tree.heading(col_name, text=title)
            self.trace_tree.column(col_name, width=width, minwidth=0, stretch=col_name in {"name", "start"})
        self._apply_trace_column_visibility()
        self.trace_tree.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(legend_box, orient="vertical", command=self.trace_tree.yview, style="Vertical.TScrollbar")
        yscroll.grid(row=0, column=1, sticky="ns")
        self.trace_tree.configure(yscrollcommand=yscroll.set)
        self.trace_tree.bind("<ButtonRelease-1>", self._on_tree_click, add="+")
        self.trace_tree.bind("<<TreeviewSelect>>", self._on_trace_selection_changed, add="+")
        self.trace_tree.bind("<Double-1>", self.rename_selected_trace, add="+")
        self.trace_tree.bind("<Button-3>", self._show_trace_context_menu, add="+")
        self.trace_tree.bind("<Delete>", self.delete_selected_trace, add="+")
        self.trace_tree.bind("<BackSpace>", self.delete_selected_trace, add="+")
        add_tip(self.trace_tree, "Click Vis (☑/☐) to show/hide. Ctrl/Cmd+click or Shift+click to multi-select. Delete removes selected traces. Double-click to rename. Right-click for menu.")
        self.trace_menu = None
        self._plot_trace_sash_initialized = False
        self._ensure_plot_trace_panes(show_plot=True, show_trace=True)

    def _pane_contains(self, widget) -> bool:
        if not hasattr(self, "plot_trace_pane"):
            return False
        try:
            return str(widget) in self.plot_trace_pane.panes()
        except Exception:
            return False

    def _safe_add_plot_trace_pane(self, widget, *, before_trace: bool = False) -> None:
        """Add a plot/trace pane without theme-specific options that can fail on Tcl variants."""
        if self._pane_contains(widget):
            return
        # Some Tcl/Tk builds reject ttk.PanedWindow add/insert options such as
        # weight.  The previous implementation swallowed that error, leaving the
        # whole plot area empty.  Add panes with no non-portable options first,
        # then set the sash position later.
        if before_trace and self._pane_contains(self.trace_panel):
            self.plot_trace_pane.insert(0, widget)
        else:
            self.plot_trace_pane.add(widget)

    def _initialize_plot_trace_sash(self) -> None:
        """Give the plot pane most of the height while keeping the trace pane visible."""
        if getattr(self, "_plot_trace_sash_initialized", False):
            return
        if not self._pane_contains(self.plot_body) or not self._pane_contains(self.trace_panel):
            return
        try:
            height = max(1, self.plot_trace_pane.winfo_height())
            if height > 80:
                self.plot_trace_pane.sashpos(0, max(220, int(height * 0.68)))
                self._plot_trace_sash_initialized = True
            else:
                self.root.after(80, self._initialize_plot_trace_sash)
        except Exception as exc:
            self.log_event(f"Plot/trace splitter init skipped: {exc}")
            self._plot_trace_sash_initialized = True

    def _ensure_plot_trace_panes(self, show_plot: bool = True, show_trace: bool = True) -> None:
        """Show plot and trace panels in a vertical, draggable splitter."""
        if not hasattr(self, "plot_trace_pane"):
            return
        try:
            # The plot pane is the primary display path and must never be removed;
            # removing it caused a blue empty background on some Windows/Tk builds.
            self._safe_add_plot_trace_pane(self.plot_body, before_trace=True)
            if show_trace:
                self._safe_add_plot_trace_pane(self.trace_panel)
                self.root.after_idle(self._initialize_plot_trace_sash)
            elif self._pane_contains(self.trace_panel):
                self.plot_trace_pane.forget(self.trace_panel)
        except Exception as exc:
            self.log_event(f"Plot/trace pane update failed: {exc}")

    def _update_plot_view_layout(self) -> None:
        """Wrap plot-view buttons so narrow windows do not clip the toolbar."""
        if not hasattr(self, "views_frame") or not hasattr(self, "plot_view_buttons"):
            return
        try:
            width = max(1, self.views_frame.winfo_width() or (self.plot_frame.winfo_width() - 120))
            per_row = 5 if width >= 420 else (3 if width >= 260 else 2)
            ordered = [PlotView.LINEAR, PlotView.LOG_ABS, PlotView.V_OVER_I, PlotView.DV_DI, PlotView.SIGNAL_TIME]
            for idx, view in enumerate(ordered):
                btn = self.plot_view_buttons.get(view)
                if btn is None:
                    continue
                row, col = divmod(idx, per_row)
                label = str(btn.cget("text"))
                btn.configure(width=max(3, len(label)))
                btn.grid_configure(row=row, column=col, padx=(0 if col == 0 else 5, 0), pady=(0 if row == 0 else 5, 0), sticky="ew")
            for col in range(5):
                self.views_frame.columnconfigure(col, weight=1 if col < per_row else 0, minsize=0, uniform="plot_view_buttons" if col < per_row else "")
        except Exception:
            pass

    def _update_plot_body_layout(self) -> None:
        """Keep plot and traces split by a draggable sash; never overlay traces on plots."""
        if not hasattr(self, "plot_body") or not hasattr(self, "trace_panel"):
            return
        views = self._selected_views() if hasattr(self, "plot_view_vars") else []
        live_only = bool(getattr(self, "_plot_live_only", False) or getattr(self, "_run_state", "idle") in {"running", "paused", "stopping"})
        try:
            self.canvas_widget.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
            self._ensure_plot_trace_panes(show_plot=True, show_trace=not live_only)
        except Exception:
            pass

    def _toggle_plot_view(self, view: PlotView) -> None:
        self.plot_view_vars[view].set(not self.plot_view_vars[view].get())
        self._on_plot_view_changed()

    def _refresh_plot_view_buttons(self) -> None:
        for view, btn in getattr(self, "plot_view_buttons", {}).items():
            try:
                btn.configure(style="ToggleOn.TButton" if self.plot_view_vars[view].get() else "ToggleOff.TButton")
            except Exception as e:
                # Silently ignore widget state errors (widget may be destroyed)
                import logging
                logger = logging.getLogger("keith_ivt.ui.plot_panel")
                logger.debug(f"Failed to update plot view button style: {e}")

    def _on_plot_view_changed(self) -> None:
        self._refresh_plot_view_buttons()
        self._redraw_all_plots()
        self.log_event("Plot views updated.")

    def _apply_default_views_for_sweep_kind(self, kind: str | None = None) -> None:
        kind = kind or self.sweep_kind.get()
        defaults = {v: False for v in self.plot_view_vars}
        if kind == SweepKind.CONSTANT_TIME.value:
            defaults[PlotView.SIGNAL_TIME] = True
        else:
            defaults[PlotView.LINEAR] = True
        for view, value in defaults.items():
            if view is PlotView.SPARE:
                value = False
            self.plot_view_vars[view].set(value)
        self._refresh_plot_view_buttons()
        self._redraw_all_plots()

    def _selected_views(self) -> list[PlotView]:
        return [v for v, var in self.plot_view_vars.items() if var.get() and v is not PlotView.SPARE]

    def _unit_family(label: str) -> str:
        lower = label.lower()
        if "current" in lower or "(a" in lower:
            return "current"
        if "voltage" in lower or "(v" in lower:
            return "voltage"
        if "ohm" in lower or "ω" in lower or "v/i" in lower or "dv/di" in lower:
            return "resistance"
        if "time" in lower or "elapsed" in lower or "(s" in lower:
            return "time"
        return "unknown"

    @staticmethod
    def _unit_choices_for_label(label: str) -> list[str]:
        family = PlotPanelMixin._unit_family(label)
        choices = {
            "current": ["Auto", "A", "mA", "µA", "nA"],
            "voltage": ["Auto", "V", "mV"],
            "resistance": ["Auto", "Ω", "kΩ", "MΩ"],
            "time": ["Auto", "s", "ms"],
        }
        return choices.get(family, ["Auto"])

    def _unit_scale_for_label(self, label: str, unit: str) -> tuple[float, str]:
        if unit == "Auto":
            return 1.0, label
        table = {
            "A": (1.0, "A"), "mA": (1e3, "mA"), "µA": (1e6, "µA"), "nA": (1e9, "nA"),
            "V": (1.0, "V"), "mV": (1e3, "mV"),
            "Ω": (1.0, "Ω"), "kΩ": (1e-3, "kΩ"), "MΩ": (1e-6, "MΩ"),
            "s": (1.0, "s"), "ms": (1e3, "ms"),
        }
        if unit not in table or unit not in self._unit_choices_for_label(label):
            return 1.0, label
        scale, label_unit = table[unit]
        base = label.split("(")[0].strip() or label
        return scale, f"{base} ({label_unit})"

    def _format_axis_numbers(self, ax) -> None:
        fmt = self.plot_number_format.get()
        if fmt == "Scientific":
            formatter = ScalarFormatter(useMathText=True)
            formatter.set_scientific(True)
            formatter.set_powerlimits((-3, 3))
            ax.yaxis.set_major_formatter(formatter)
        elif fmt == "Engineering":
            ax.yaxis.set_major_formatter(EngFormatter())

    def _plot_data_on_figure(self, figure: Figure) -> list:
        # Full redraw invalidates any Line2D objects cached by the live
        # incremental renderer.  Clear the renderer cache before wiping the
        # figure so the next live sweep cannot update a detached, invisible
        # line from a previous run/view/theme state.
        if figure is getattr(self, "figure", None) and hasattr(self, "_plot_renderer"):
            self._plot_renderer.optimizer.clear_cache()
        figure.clear()
        figure.set_facecolor(self._palette["plot_bg"])
        views = self._selected_views()
        if not views:
            figure.text(0.5, 0.5, "No plot views selected", ha="center", va="center", color=self._palette["muted"])
            return []
        rows, cols = layout_grid(len(views), self.arrangement.get())
        axes = []
        traces = [] if getattr(self, "_plot_live_only", False) else [t for t in self._datasets.all() if t.visible]
        selected_trace_ids = set(self._selected_trace_ids()) if hasattr(self, "_selected_trace_ids") else set()
        if traces and not selected_trace_ids:
            # Default to the first trace (which is now the latest due to reverse ordering)
            selected_trace_ids = {traces[0].trace_id}
        live_result = None
        if self._live_points:
            config = self._live_config
            if config is not None:
                live_result = SweepResult(config, list(self._live_points))
        fmt = self.plot_format.get().lower()
        marker = "." if "marker" in fmt else None
        linestyle = "-" if "line" in fmt else "None"
        for idx, view in enumerate(views, start=1):
            ax = figure.add_subplot(rows, cols, idx)
            ax._happy_view = view
            ax.set_facecolor(self._palette["plot_bg"])
            ax.set_title(view.value, color=self._palette["fg"])
            ax.tick_params(colors=self._palette["muted"])
            for spine in ax.spines.values():
                spine.set_color(self._palette["grid"])
            if live_result is not None:
                x, y, xlabel, ylabel, title, y_is_log = xy_for_view(live_result, view)
                xscale, xlabel = self._unit_scale_for_label(xlabel, self.plot_x_unit.get())
                yscale, ylabel = self._unit_scale_for_label(ylabel, self.plot_y_unit.get())
                x = [v * xscale for v in x]
                y = [v * yscale for v in y]
                ax.plot(x, y, marker=marker, linestyle=linestyle, linewidth=1.1, label="live")
                ax.set_title(title, color=self._palette["fg"])
                ax.set_xlabel(xlabel, color=self._palette["fg"]); ax.set_ylabel(ylabel, color=self._palette["fg"])
                if y_is_log:
                    ax.set_yscale("log")
            for trace in traces:
                x, y, xlabel, ylabel, title, y_is_log = xy_for_view(trace.result, view)
                xscale, xlabel = self._unit_scale_for_label(xlabel, self.plot_x_unit.get())
                yscale, ylabel = self._unit_scale_for_label(ylabel, self.plot_y_unit.get())
                x = [v * xscale for v in x]
                y = [v * yscale for v in y]
                is_selected = trace.trace_id in selected_trace_ids
                ax.plot(
                    x, y, marker=marker, linestyle=linestyle,
                    linewidth=2.4 if is_selected else 0.9,
                    alpha=1.0 if is_selected else 0.35,
                    zorder=4 if is_selected else 2,
                    label=trace.name, color=getattr(trace, "color", None),
                )
                ax.set_title(title, color=self._palette["fg"])
                ax.set_xlabel(xlabel, color=self._palette["fg"]); ax.set_ylabel(ylabel, color=self._palette["fg"])
                if y_is_log:
                    ax.set_yscale("log")
            if traces or live_result is not None:
                leg = ax.legend(fontsize=8, frameon=False)
                for text in leg.get_texts():
                    text.set_color(self._palette["fg"])
            self._format_axis_numbers(ax)
            ax.grid(True, alpha=0.35, color=self._palette["grid"])
            axes.append(ax)
        figure.tight_layout()
        return axes

    def _update_live_plot_incremental(self) -> None:
        """Update live plot using incremental rendering (much faster than full redraw).

        This method uses the PlotOptimizer to update only the data in existing
        Line2D objects instead of clearing and recreating the entire figure.
        This provides 5-10x performance improvement for real-time sweeps.
        """
        if not self._live_points:
            # No live data yet during a sweep - show empty plot, not historical traces.
            # Clearing the figure also detaches cached Line2D artists; clear the
            # renderer cache at the same time to avoid invisible first-point updates.
            if hasattr(self, "_plot_renderer"):
                self._plot_renderer.optimizer.clear_cache()
            self.figure.clear()
            self.figure.set_facecolor(self._palette["plot_bg"])
            views = self._selected_views()
            if views:
                rows, cols = layout_grid(len(views), self.arrangement.get())
                for idx, view in enumerate(views, start=1):
                    ax = self.figure.add_subplot(rows, cols, idx)
                    ax.set_facecolor(self._palette["plot_bg"])
                    ax.set_title(view.value, color=self._palette["fg"])
                    ax.tick_params(colors=self._palette["muted"])
                    for spine in ax.spines.values():
                        spine.set_color(self._palette["grid"])
                    ax.text(0.5, 0.5, "Waiting for data...", ha="center", va="center",
                           color=self._palette["muted"], fontsize=12)
                    ax.grid(True, alpha=0.35, color=self._palette["grid"])
            self._axes = []
            try:
                self.canvas.draw_idle()
                self.canvas.flush_events()
            except Exception:
                self.canvas.draw()
            return
        
        if not hasattr(self, "_plot_renderer"):
            # No optimizer available - just skip incremental update
            # The caller will handle fallback if needed
            return

        try:
            from keith_ivt.models import SweepResult
            from keith_ivt.ui.plot_views import xy_for_view

            # Create temporary result from live points
            config = self._live_config
            if config is None:
                return

            live_result = SweepResult(config, list(self._live_points))
            views = self._selected_views()
            if not views:
                return

            rows, cols = layout_grid(len(views), self.arrangement.get())

            # Prepare axes
            axes = self._plot_renderer.prepare_axes(len(views), rows, cols)

            # Build data series for incremental drawing
            data_series = []
            fmt = self.plot_format.get().lower()
            marker = "." if "marker" in fmt else None
            linestyle = "-" if "line" in fmt else "None"

            for idx, view in enumerate(views):
                x, y, xlabel, ylabel, title, y_is_log = xy_for_view(live_result, view)

                # Apply unit scaling
                xscale, xlabel_scaled = self._unit_scale_for_label(xlabel, self.plot_x_unit.get())
                yscale, ylabel_scaled = self._unit_scale_for_label(ylabel, self.plot_y_unit.get())
                x_scaled = [v * xscale for v in x]
                y_scaled = [v * yscale for v in y]

                # Downsample for display if needed
                key = f"live_{view.value}"
                style = {
                    "marker": marker,
                    "linestyle": linestyle,
                    "linewidth": 1.1,
                    "label": "live",
                    "color": self._palette.get("accent", None),
                }

                data_series.append({
                    "ax_index": idx,
                    "key": key,
                    "x": x_scaled,
                    "y": y_scaled,
                    "style": style,
                })

                # Configure axis
                ax = axes[idx]
                ax.set_title(title, color=self._palette["fg"])
                ax.set_xlabel(xlabel_scaled, color=self._palette["fg"])
                ax.set_ylabel(ylabel_scaled, color=self._palette["fg"])
                if y_is_log:
                    ax.set_yscale("log")
                ax.grid(True, alpha=0.35, color=self._palette["grid"])

            # Draw incrementally
            self._plot_renderer.draw_incremental(axes, data_series)

        except Exception as e:
            # On error, clear caches and show error (NO recursive retry!)
            import logging
            logger = logging.getLogger("keith_ivt.ui.plot_panel")
            logger.debug(f"Incremental plot update failed: {e}")
            try:
                if hasattr(self, "_plot_renderer"):
                    self._plot_renderer.reset()
                self.figure.clear()
                self.figure.set_facecolor(self._palette["plot_bg"])
                self.figure.text(0.5, 0.5, f"Plot error: {str(e)[:50]}", 
                                ha="center", va="center", color=self._palette["muted"])
                self.canvas.draw_idle()
                self.canvas.flush_events()
            except Exception:
                self.canvas.draw()
                try:
                    self.figure.clear()
                    self.figure.set_facecolor(self._palette["plot_bg"])
                    self.figure.text(0.5, 0.5, f"Plot error: {str(e)[:50]}", 
                                    ha="center", va="center", color=self._palette["muted"])
                    self.canvas.draw_idle()
                    self.canvas.flush_events()
                except Exception:
                    self.canvas.draw()

    def _redraw_all_plots(self, live_only: bool = False) -> None:
        self._plot_live_only = bool(live_only)

        # Use incremental update for live-only plots (much faster)
        if live_only and hasattr(self, "_plot_renderer"):
            self._update_live_plot_incremental()
            return

        # Full redraw for non-live plots
        self._update_plot_body_layout()
        self._axes = self._plot_data_on_figure(self.figure)
        try:
            self.canvas.draw_idle()
            self.canvas.flush_events()
        except Exception:
            self.canvas.draw()

    def _on_mpl_plot_click(self, event) -> None:
        button = getattr(event, "button", None)
        if str(button).lower().endswith("right") or button == 3:
            self._show_plot_context_menu(event)
            return
        if not getattr(event, "dblclick", False):
            return
        if event.inaxes is None:
            self.open_plot_fullscreen()
            return
        ax = event.inaxes
        bbox = ax.get_window_extent()
        # Double-click close to the bottom/left axis areas for axis-specific input.
        if event.y is not None and event.y < bbox.y0 + 35:
            self.set_axis_range_dialog(axis="x", ax=ax)
        elif event.x is not None and event.x < bbox.x0 + 45:
            self.set_axis_range_dialog(axis="y", ax=ax)
        else:
            self.open_plot_fullscreen()

    def autoscale_plots(self) -> None:
        self._redraw_all_plots()
        self.log_event("Plots autoscaled.")

    def save_figure(self) -> bool:
        path = filedialog.asksaveasfilename(defaultextension=".png", initialfile=suggested_figure_name(), filetypes=[("PNG image", "*.png"), ("PDF", "*.pdf"), ("SVG", "*.svg")])
        if not path:
            return False
        self.figure.savefig(path, facecolor=self.figure.get_facecolor(), bbox_inches="tight")
        self.log_event(f"Saved figure: {path}")
        return True

