from __future__ import annotations

from keith_ivt.ui.menu_utils import make_touch_menu, popup_menu


class TraceInteractionMixin:
    def _show_trace_context_menu(self, event) -> None:
        item = self.trace_tree.identify_row(event.y)
        if item:
            current_selection = set(self.trace_tree.selection())
            # Preserve an existing multi-selection when right-clicking one of the selected rows.
            # Right-clicking an unselected row intentionally pivots the context menu to that row.
            if item not in current_selection:
                self.trace_tree.selection_set(item)
        menu = make_touch_menu(self.root, self.ui_font_family.get(), int(self.ui_font_size.get()))
        menu.add_command(label="View data table", command=self.view_selected_trace_data)
        menu.add_command(label="Export selected...", command=self.save_selected_trace)
        menu.add_command(label="Export visible...", command=self.save_checked_traces)
        menu.add_command(label="Export all traces...", command=self.save_all_traces)
        menu.add_command(label="Import data...", command=self.import_csv)
        menu.add_separator()
        menu.add_command(label="Rename selected...", command=self.rename_selected_trace)
        menu.add_command(label="Choose color...", command=self.choose_selected_trace_color)
        menu.add_command(label="Hide / show selected", command=self.toggle_selected_trace_visibility)
        menu.add_separator()
        menu.add_command(label="Delete selected traces", command=self.delete_selected_trace)
        menu.add_command(label="Clear all traces", command=self.clear_all_traces)
        menu.add_separator()
        col_menu = make_touch_menu(self.root, self.ui_font_family.get(), int(self.ui_font_size.get()))
        for col_name, (title, _width) in getattr(self, "_trace_columns", {}).items():
            state = "disabled" if col_name in {"show", "name"} else "normal"
            label = "Show" if col_name == "show" else title
            col_menu.add_checkbutton(label=label, variable=self.trace_column_vars[col_name], command=lambda c=col_name: self._toggle_trace_column(c), state=state)
        menu.add_cascade(label="Visible columns", menu=col_menu)
        popup_menu(menu, event.x_root, event.y_root)

    def choose_trace_color(self, trace_id: int | None = None) -> None:
        from tkinter import colorchooser
        trace = self._datasets.get(trace_id) if trace_id is not None else self._selected_trace()
        if trace is None:
            return
        _rgb, color = colorchooser.askcolor(color=getattr(trace, "color", "#1f77b4"), title=f"Choose color - {trace.name}")
        if color:
            self._datasets.set_color(trace.trace_id, color)
            self._refresh_trace_list(); self._redraw_all_plots()

    def choose_selected_trace_color(self) -> None:
        self.choose_trace_color(None)

    def toggle_selected_trace_visibility(self) -> None:
        trace = self._selected_trace()
        if trace is None:
            return
        self._datasets.toggle_visibility(trace.trace_id)
        self._refresh_trace_list(); self._redraw_all_plots()

