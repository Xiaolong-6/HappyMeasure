from __future__ import annotations

import tkinter as tk
from dataclasses import replace
from tkinter import END, filedialog, messagebox, simpledialog, ttk

from keith_ivt.data.exporters import save_combined_csv, save_csv
from keith_ivt.data.dataset_store import DeviceTrace
from keith_ivt.models import SweepKind, SweepMode, SweepResult
from keith_ivt.ui.export_naming import suggested_all_csv_name, suggested_single_csv_name
from keith_ivt.ui.menu_utils import make_touch_menu, popup_menu


class TracePanelMixin:
    def _trace_start_label(self, trace: DeviceTrace) -> str:
        first_ts = ""
        if trace.result.points:
            first_ts = getattr(trace.result.points[0], "timestamp", "") or ""
        if first_ts:
            return first_ts.replace("T", " ")
        return trace.created_at.isoformat(timespec="seconds").replace("T", " ")

    def _apply_trace_column_visibility(self) -> None:
        if not hasattr(self, "trace_tree") or not hasattr(self, "_trace_columns"):
            return
        for col_name, (_title, width) in self._trace_columns.items():
            shown = self.trace_column_vars.get(col_name).get() if col_name in self.trace_column_vars else True
            self.trace_tree.column(col_name, width=width if shown else 0, minwidth=0, stretch=(shown and col_name in {"name", "start"}))

    def _toggle_trace_column(self, col_name: str) -> None:
        if col_name in {"show", "name"}:
            self.trace_column_vars[col_name].set(True)
        self._apply_trace_column_visibility()

    def _selected_trace_ids(self) -> list[int]:
        if not hasattr(self, "trace_tree"):
            return []
        ids: list[int] = []
        for item in self.trace_tree.selection():
            trace_id = self._tree_item_to_trace.get(item)
            if trace_id is not None and self._datasets.get(trace_id) is not None:
                ids.append(trace_id)
        return ids

    def _clear_trace_selection_state(self) -> None:
        """Clear stale trace selection when the trace registry becomes empty."""
        self._selected_trace_id = None
        if hasattr(self, "trace_tree"):
            try:
                self.trace_tree.selection_set(())
            except Exception:
                pass

    def _ensure_trace_selection(self) -> None:
        """Trace list must always have at least one selected item when data exists."""
        if not hasattr(self, "trace_tree"):
            return
        items = list(self.trace_tree.get_children())
        if not items:
            self._clear_trace_selection_state()
            return
        valid_selection = [item for item in self.trace_tree.selection() if item in items]
        if not valid_selection:
            # Default to the first item (which is now the latest trace)
            self.trace_tree.selection_set(items[0])
            valid_selection = [items[0]]
        self._selected_trace_id = self._tree_item_to_trace.get(valid_selection[0])

    def _on_trace_selection_changed(self, _event=None) -> None:
        self._ensure_trace_selection()
        try:
            self._redraw_all_plots()
        except Exception:
            pass

    def _refresh_trace_list(self) -> None:
        previous_selection = set(self._selected_trace_ids())
        if not previous_selection and getattr(self, "_selected_trace_id", None):
            previous_selection = {self._selected_trace_id}
        previous_count = len(previous_selection)
        self.trace_tree.delete(*self.trace_tree.get_children())
        self._tree_item_to_trace.clear()
        trace_to_item: dict[int, str] = {}
        traces_all = self._datasets.all()
        valid_trace_ids = {trace.trace_id for trace in traces_all}
        previous_selection = {tid for tid in previous_selection if tid in valid_trace_ids}
        if not traces_all:
            self._clear_trace_selection_state()
        if hasattr(self, "trace_title_text"):
            try:
                self.trace_title_text.set(f"Traces ({len(traces_all)})")
            except Exception:
                pass
        for trace in traces_all:
            cfg = trace.result.config
            tag = f"trace_color_{trace.trace_id}"
            try:
                self.trace_tree.tag_configure(tag, foreground=trace.color)
            except Exception:
                pass
            item = self.trace_tree.insert("", END, values=(
                "" if trace.visible else "☐",
                "■",
                trace.name,
                cfg.operator or "--",
                "V-src" if cfg.mode is SweepMode.VOLTAGE_SOURCE else "I-src",
                "Step" if cfg.sweep_kind is SweepKind.STEP else ("Time" if cfg.sweep_kind is SweepKind.CONSTANT_TIME else "Adaptive"),
                trace.point_count,
                self._trace_start_label(trace),
            ), tags=(tag,))
            self._tree_item_to_trace[item] = trace.trace_id
            trace_to_item[trace.trace_id] = item
        self._apply_trace_column_visibility()
        
        items = list(self.trace_tree.get_children())
        if items:
            restored_items = [trace_to_item[tid] for tid in previous_selection if tid in trace_to_item]
            if restored_items:
                self.trace_tree.selection_set(restored_items)
            elif len(traces_all) > previous_count:
                # New live data should surface the latest trace when there was no surviving selection.
                self.trace_tree.selection_set(items[0])
        self._ensure_trace_selection()

    def _selected_trace(self) -> DeviceTrace | None:
        ids = self._selected_trace_ids()
        if not ids:
            self._ensure_trace_selection()
            ids = self._selected_trace_ids()
        return self._datasets.get(ids[0]) if ids else None

    def _on_tree_click(self, event) -> None:
        """Handle trace list clicks while preserving Ctrl/Cmd multi-select."""
        item = self.trace_tree.identify_row(event.y)
        col = self.trace_tree.identify_column(event.x)
        if not item:
            self._ensure_trace_selection()
            return
        trace_id = self._tree_item_to_trace.get(item)
        
        # Column 1 (show/hide checkbox): toggle visibility
        if trace_id and col == "#1":
            self._datasets.toggle_visibility(trace_id)
            self._refresh_trace_list()
            self._redraw_all_plots()
            return
        
        # Column 2 (color square): choose color
        if trace_id and col == "#2":
            # Only select this item if it's not already in the selection
            if trace_id not in self._selected_trace_ids():
                self.trace_tree.selection_set(item)
            self.choose_trace_color(trace_id)
            return
        
        # Other columns: let Treeview handle native selection (Ctrl/Cmd multi-select)
        # Don't override the selection - just ensure at least one is selected if none are
        if not self.trace_tree.selection():
            self._ensure_trace_selection()

    def _show_trace_column_menu_from_button(self) -> None:
        menu = make_touch_menu(self.root, self.ui_font_family.get(), int(self.ui_font_size.get()))
        for col_name, (title, _width) in getattr(self, "_trace_columns", {}).items():
            state = "disabled" if col_name in {"show", "name"} else "normal"
            label = "Show" if col_name == "show" else title
            menu.add_checkbutton(label=label, variable=self.trace_column_vars[col_name], command=lambda c=col_name: self._toggle_trace_column(c), state=state)
        x = self.root.winfo_pointerx(); y = self.root.winfo_pointery()
        popup_menu(menu, x, y)

    def rename_selected_trace(self, _event=None) -> None:
        trace = self._selected_trace()
        if trace is None: return
        new_name = simpledialog.askstring("Rename device", "New device name:", initialvalue=trace.name)
        if new_name:
            self._datasets.rename(trace.trace_id, new_name)
            self._refresh_trace_list(); self._redraw_all_plots()

    def delete_selected_trace(self, _event=None) -> str | None:
        ids = list(dict.fromkeys(self._selected_trace_ids()))
        if not ids:
            trace = self._selected_trace()
            ids = [trace.trace_id] if trace is not None else []
        if not ids:
            return "break" if _event is not None else None
        for trace_id in ids:
            self._datasets.remove(trace_id)
        if hasattr(self, "log_event"):
            noun = "trace" if len(ids) == 1 else "traces"
            self.log_event(f"Deleted {len(ids)} selected {noun}.")
        self._refresh_trace_list(); self._redraw_all_plots()
        return "break" if _event is not None else None

    def view_selected_trace_data(self) -> None:
        trace = self._selected_trace()
        if trace is None:
            messagebox.showinfo("No selection", "Select a device trace first."); return
        import tkinter as tk
        win = tk.Toplevel(self.root)
        win.title(f"Data table - {trace.name}")
        win.geometry("620x420")
        win.transient(self.root)
        headers = trace.result.config.csv_headers
        frame = ttk.Frame(win, padding=8)
        frame.pack(fill="both", expand=True)
        frame.rowconfigure(0, weight=1); frame.columnconfigure(0, weight=1)
        tree = ttk.Treeview(frame, columns=("index", "elapsed", headers[0], headers[1]), show="headings")
        for col, title, width in [("index", "#", 50), ("elapsed", "Elapsed_s", 90), (headers[0], headers[0], 150), (headers[1], headers[1], 150)]:
            tree.heading(col, text=title); tree.column(col, width=width, stretch=True)
        tree.grid(row=0, column=0, sticky="nsew")
        y = ttk.Scrollbar(frame, orient="vertical", command=tree.yview); y.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=y.set)
        for i, pt in enumerate(trace.result.points, start=1):
            tree.insert("", END, values=(i, f"{getattr(pt, 'elapsed_s', 0.0):.12g}", f"{pt.source_value:.12g}", f"{pt.measured_value:.12g}"))
        ttk.Button(frame, text="Close", command=win.destroy).grid(row=1, column=0, sticky="ew", pady=(8,0))

    def _result_with_trace_name(self, trace: DeviceTrace) -> SweepResult:
        """Return a result whose metadata follows the editable trace name."""
        cfg = replace(trace.result.config, device_name=trace.name)
        return SweepResult(cfg, trace.result.points)

    def save_last_csv(self):
        if not self._last_result:
            messagebox.showinfo("No data", "No last result to save."); return False
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=suggested_single_csv_name(self._last_result), filetypes=[("CSV", "*.csv")])
        if not path: return False
        save_csv(self._last_result, path); self._mark_last_save("last CSV"); self.log_event(f"Saved last CSV: {path}"); return True

    def save_selected_trace(self):
        trace = self._selected_trace()
        if trace is None:
            messagebox.showinfo("No selection", "Select a device trace first."); return False
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=suggested_single_csv_name(trace.result, trace.name), filetypes=[("CSV", "*.csv")])
        if not path: return False
        save_csv(self._result_with_trace_name(trace), path); self._mark_last_save("selected CSV"); self.log_event(f"Saved selected trace: {path}"); return True

    def save_all_traces(self):
        """Export every trace, including hidden traces. Visibility is display-only."""
        traces = self._datasets.all()
        if not traces:
            messagebox.showinfo("No traces", "No device traces to save."); return False
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=suggested_all_csv_name([self._result_with_trace_name(t) for t in traces]), filetypes=[("CSV", "*.csv")])
        if not path: return False
        save_combined_csv([self._result_with_trace_name(t) for t in traces], path); self._mark_last_save("all CSV"); self.log_event(f"Saved all traces with metadata: {path}"); return True



    def save_checked_traces(self):
        """Export only visible traces to a combined CSV file."""
        traces = [t for t in self._datasets.all() if t.visible]
        if not traces:
            messagebox.showinfo("No visible traces", "No visible (ticked) traces to export."); return False
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=suggested_all_csv_name([self._result_with_trace_name(t) for t in traces]), filetypes=[("CSV", "*.csv")])
        if not path: return False
        save_combined_csv([self._result_with_trace_name(t) for t in traces], path)
        self._mark_last_save("visible CSV")
        self.log_event(f"Saved visible traces with metadata: {path}")
        return True
