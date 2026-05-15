from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from tkinter import END, filedialog, messagebox

from keith_ivt.data.backup import autosave_result, default_backup_dir
from keith_ivt.data.exporters import result_metadata, save_csv
from keith_ivt.data.importers import load_csv
from keith_ivt.models import SweepConfig, SweepKind, SweepMode, SweepPoint, SweepResult
from keith_ivt.ui.menu_utils import make_touch_menu, popup_menu


class DataActionMixin:
    def backup_now(self):
        if not self._last_result:
            messagebox.showinfo("No result", "No result available for backup."); return False
        self._last_backup_path = autosave_result(self._last_result)
        self.backup_text.set(f"Backup: {self._last_backup_path.name}")
        self._mark_last_save("backup")
        self.log_event(f"Manual backup saved: {self._last_backup_path}"); return True

    def _mark_last_save(self, action: str = "save") -> None:
        try:
            self.last_save_text.set(f"Last save: {datetime.now().strftime('%H:%M:%S')} · {action}")
        except Exception:
            pass

    @staticmethod
    def _import_signature(result: SweepResult) -> tuple:
        meta = result_metadata(result)
        return (meta.get("trace_uid"), meta.get("point_count"))

    @staticmethod
    def _partial_import_signature(result: SweepResult) -> tuple:
        cfg = result.config
        return (str(cfg.device_name).strip().lower(), str(cfg.operator).strip().lower(), cfg.mode.value, cfg.sweep_kind.value)

    def _resolve_import_overlap(self, results: list[SweepResult]) -> bool:
        existing = self._datasets.all()
        if not existing:
            return True
        exact_new = {self._import_signature(r) for r in results}
        partial_new = {self._partial_import_signature(r) for r in results}
        exact_ids = [t.trace_id for t in existing if self._import_signature(t.result) in exact_new]
        partial_ids = [t.trace_id for t in existing if self._partial_import_signature(t.result) in partial_new and t.trace_id not in exact_ids]
        overlap_ids = sorted(set(exact_ids + partial_ids))
        if not overlap_ids:
            return True
        exact_line = f"Exact duplicate(s): {len(exact_ids)}" if exact_ids else "Exact duplicate(s): 0"
        partial_line = f"Same device/operator/mode/type but different data: {len(partial_ids)}" if partial_ids else "Same device/operator/mode/type but different data: 0"
        msg = (
            f"The import matches {len(overlap_ids)} existing trace(s).\n"
            f"{exact_line}\n{partial_line}\n\n"
            "Yes = replace matching existing traces, then import\n"
            "No = keep existing traces and import with unique names\n"
            "Cancel = abort import"
        )
        answer = messagebox.askyesnocancel("Import overlap check", msg)
        if answer is None:
            return False
        if answer is True:
            for trace_id in overlap_ids:
                self._datasets.remove(trace_id)
            self.log_event(f"Deleted {len(overlap_ids)} matching trace(s) before import.")
            return True
        self.log_event("Import overlap kept existing traces; imported traces will receive unique names if needed.")
        return True

    def _add_imported_results(self, results: list[SweepResult], source_label: str) -> int:
        if not self._resolve_import_overlap(results):
            return 0
        count = 0
        for result in results:
            self._datasets.add_result(result, result.config.device_name)
            self._last_result = result
            count += 1
        self._refresh_trace_list(); self._redraw_all_plots()
        self.log_event(f"Imported {count} trace(s) from {source_label}")
        return count

    def import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("All files", "*.*")])
        if not path: return False
        results = load_csv(path)
        count = self._add_imported_results(results, str(path))
        return count > 0

    def clear_plot_only(self):
        self._x_data.clear(); self._y_data.clear(); self._live_points.clear(); self._redraw_all_plots(); self.log_event("Live plot cleared.")

    def clear_all_traces(self):
        if self._datasets.all() and not messagebox.askyesno("Clear all", "Remove all device traces from legend?"):
            return
        self._datasets.clear(); self._x_data.clear(); self._y_data.clear(); self._live_points.clear(); self._live_config = None
        self._refresh_trace_list(); self._redraw_all_plots(); self.log_event("All traces and live plot cleared.")

    def import_backup_csv(self):
        path = filedialog.askopenfilename(initialdir=str(self._backup_dir_from_ui() if hasattr(self, "backup_folder_var") else default_backup_dir()), filetypes=[("CSV", "*.csv"), ("All files", "*.*")])
        if not path:
            return False
        return self._import_backup_path(Path(path))

    def choose_backup_folder(self):
        path = filedialog.askdirectory(initialdir=str(default_backup_dir()))
        if path:
            self.backup_folder_var.set(path)
            self.refresh_backup_list()
        return bool(path)

    def _backup_dir_from_ui(self) -> Path:
        try:
            return Path(self.backup_folder_var.get())
        except Exception:
            return default_backup_dir()

    def ensure_sample_backups(self) -> None:
        directory = self._backup_dir_from_ui()
        directory.mkdir(parents=True, exist_ok=True)
        if any(directory.glob("*.csv")):
            return
        from keith_ivt.models import SweepConfig, SweepMode, SweepKind, SweepPoint, SweepResult
        samples = [
            ("Sample_resistor_10k", [(-1.0, -1e-4), (0.0, 0.0), (1.0, 1e-4)]),
            ("Sample_photodetector_noisy", [(0.0, 2e-9), (0.5, 4e-9), (1.0, 9e-9)]),
            ("Sample_time_trace", [(0.5, 3e-6), (0.5, 3.2e-6), (0.5, 2.9e-6)]),
        ]
        for idx, (name, pairs) in enumerate(samples, start=1):
            cfg = SweepConfig(mode=SweepMode.VOLTAGE_SOURCE, start=pairs[0][0], stop=pairs[-1][0], step=1.0, compliance=0.01, debug=True, device_name=name, sweep_kind=SweepKind.STEP)
            pts = [SweepPoint(v, i, elapsed_s=n*0.1) for n, (v, i) in enumerate(pairs)]
            save_csv(SweepResult(cfg, pts), directory / f"sample_backup_{idx}_{name}.csv")

    def refresh_backup_list(self):
        if not hasattr(self, "backup_tree"):
            return
        for item in self.backup_tree.get_children():
            self.backup_tree.delete(item)
        directory = self._backup_dir_from_ui()
        directory.mkdir(parents=True, exist_ok=True)
        for path in sorted(directory.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True):
            stat = path.stat()
            modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            size = f"{stat.st_size/1024:.1f} KB"
            self.backup_tree.insert("", "end", iid=str(path), values=(path.name, size, modified))

    def import_selected_backup(self):
        if not hasattr(self, "backup_tree"):
            return False
        selection = self.backup_tree.selection()
        if not selection:
            messagebox.showinfo("No backup selected", "Select a backup file from the list first."); return False
        return self._import_backup_path(Path(selection[0]))

    def _import_backup_path(self, path: Path):
        results = load_csv(path)
        count = self._add_imported_results(results, f"autosave backup: {path}")
        return count > 0

    def _show_backup_context_menu(self, event) -> None:
        item = self.backup_tree.identify_row(event.y)
        if item:
            self.backup_tree.selection_set(item)
        menu = make_touch_menu(self.root, self.ui_font_family.get(), int(self.ui_font_size.get()))
        menu.add_command(label="Import selected", command=self.import_selected_backup)
        menu.add_command(label="Refresh list", command=self.refresh_backup_list)
        menu.add_command(label="Open folder", command=self.open_backup_folder)
        popup_menu(menu, event.x_root, event.y_root)

    def open_backup_folder(self):
        path = self._backup_dir_from_ui() if hasattr(self, "backup_folder_var") else default_backup_dir(); path.mkdir(parents=True, exist_ok=True); self._open_path(path)

    def open_log_folder(self):
        p = Path("logs"); p.mkdir(exist_ok=True); self._open_path(p)

    def _open_path(self, path: Path):
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin": subprocess.Popen(["open", str(path)])
        else: subprocess.Popen(["xdg-open", str(path)])
