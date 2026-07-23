"""Desktop-only HappyMeasure user-flow smoke test.

Run from an interactive Windows session:
    python tests/run_ui_user_flow.py

The script uses the debug simulator, never opens a real instrument, and avoids
writing backups or showing modal dialogs.
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path
from tkinter import messagebox

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import keith_ivt.data.presets as preset_store  # noqa: E402
import keith_ivt.ui.data_actions as data_actions  # noqa: E402
import keith_ivt.ui.plot_panel as plot_panel  # noqa: E402
import keith_ivt.ui.preset_restore_panel as preset_restore_panel  # noqa: E402
import keith_ivt.ui.settings_preset_actions as preset_actions  # noqa: E402
import keith_ivt.ui.sweep_controller as sweep_controller  # noqa: E402
import keith_ivt.ui.trace_panel as trace_panel  # noqa: E402
import keith_ivt.ui.update_controller as update_controller  # noqa: E402
from keith_ivt.models import SweepKind  # noqa: E402
from keith_ivt.ui.simple_app import SimpleKeithIVtApp  # noqa: E402


def _wait_until(app: SimpleKeithIVtApp, predicate, timeout_s: float = 8.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        app.root.update()
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError(f"Timed out; run state={app._run_state}")


def _run_to_completion(app: SimpleKeithIVtApp) -> None:
    previous_result = app._last_result
    app.start_sweep()
    assert app._run_state in {"preparing", "running"}, app._run_state
    _wait_until(
        app,
        lambda: app._run_state in {"completed", "stopped", "error"},
    )
    assert app._run_state == "completed"
    assert app._last_result is not None
    assert app._last_result is not previous_result
    assert app._last_result.points


def main() -> None:
    scratch = tempfile.TemporaryDirectory(prefix="happymeasure-ui-smoke-")
    scratch_path = Path(scratch.name)
    backup_dir = scratch_path / "backups"
    preset_path = scratch_path / "presets.json"
    shown_errors: list[tuple[str, str]] = []
    messagebox.showinfo = lambda *_args, **_kwargs: None
    messagebox.showwarning = lambda *_args, **_kwargs: None
    messagebox.showerror = lambda title, message, **_kwargs: shown_errors.append(
        (str(title), str(message))
    )
    messagebox.askyesno = lambda *_args, **_kwargs: True
    messagebox.askyesnocancel = lambda *_args, **_kwargs: False
    update_controller.check_github_release = lambda *_args, **_kwargs: {
        "status": "current",
        "message": "Test update result",
        "latest_version": "test",
        "release_url": None,
        "asset_name": None,
        "asset_download_url": None,
        "asset_sha256": None,
    }
    sweep_controller.autosave_result = lambda _result: ROOT / "ui-smoke-backup.csv"
    preset_restore_panel.default_backup_dir = lambda: backup_dir
    data_actions.default_backup_dir = lambda: backup_dir
    preset_actions.save_preset = lambda name, snapshot: preset_store.save_preset(
        name, snapshot, preset_path
    )
    preset_actions.load_presets = lambda: preset_store.load_presets(preset_path)

    app = SimpleKeithIVtApp()
    callback_errors: list[str] = []
    app.root.report_callback_exception = lambda exc_type, exc, _tb: callback_errors.append(
        f"{exc_type.__name__}: {exc}"
    )
    try:
        for page in app.NAV_ITEMS:
            app._show_nav(page)
            app.root.update()
            assert app.current_content.winfo_children(), page
        for geometry in ("760x500", "1360x820", "1920x1080"):
            app.root.geometry(geometry)
            app.root.update()
            assert app.content_canvas.winfo_width() > 0
        for theme in ("Light", "Dark", "Debug", "Light"):
            app.ui_theme.set(theme)
            app.apply_ui_appearance()
            app.root.update()

        app._hide_drawer()
        app.root.update()
        assert not app._drawer_open
        app._show_drawer()
        app.root.update()
        assert app._drawer_open

        app.debug.set(True)
        app.show_front_panel_on_start.set(False)
        app._show_nav("Hardware")
        app.connect_or_check()
        assert app._connected

        app._show_nav("Sweep")
        app.nplc.set(0.01)
        app.delay_s.set(0.0)

        app.sweep_kind.set(SweepKind.STEP.value)
        app.start.set(-0.2)
        app.stop.set(0.2)
        app.step.set(0.1)
        _run_to_completion(app)

        app._datasets.clear()
        app.sweep_kind.set(SweepKind.CONSTANT_TIME.value)
        app.constant_value.set(0.1)
        app.constant_until_stop.set(False)
        app.duration_s.set(0.45)
        app.interval_s.set(0.01)
        app.start_sweep()
        assert app._run_state == "completed"
        assert shown_errors[-1][0] == "Interval too short"
        app.interval_s.set(0.2)
        _run_to_completion(app)

        app._datasets.clear()
        app.sweep_kind.set(SweepKind.ADAPTIVE.value)
        app.root.update()
        app.adaptive_text.delete("1.0", "end")
        app.adaptive_text.insert("1.0", "# smoke\n0, 0.2, 0.1\n0.2, 0, -0.1")
        app._adaptive_input_changed()
        app.root.update()
        app.adaptive_remove_duplicates.set(False)
        _run_to_completion(app)
        app.adaptive_text.delete("1.0", "end")
        app.adaptive_text.insert("1.0", "0, 1")
        app._adaptive_input_changed()
        app.root.update()
        assert app.adaptive_validation_text.get().startswith("Invalid:")

        app._datasets.clear()
        app.sweep_kind.set(SweepKind.CONSTANT_TIME.value)
        app.constant_until_stop.set(True)
        app.interval_s.set(0.2)
        app.start_sweep()
        assert app._run_state in {"preparing", "running"}, app._run_state
        _wait_until(app, lambda: app.app_state.point_count >= 2)
        app.toggle_pause()
        assert app._run_state == "paused", app._run_state
        app.toggle_pause()
        assert app._run_state == "running"
        app.abort_sweep()
        _wait_until(app, lambda: app._run_state in {"stopped", "error"})
        assert app._run_state == "stopped"

        app.disconnect_hardware()
        assert not app._connected

        csv_path = scratch_path / "roundtrip.csv"
        trace_panel.filedialog.asksaveasfilename = lambda **_kwargs: str(csv_path)
        assert app.save_all_traces()
        assert csv_path.exists() and csv_path.stat().st_size > 0
        app.clear_all_traces()
        assert not app._datasets.all()
        data_actions.filedialog.askopenfilename = lambda **_kwargs: str(csv_path)
        assert app.import_csv()
        assert app._datasets.all()

        png_path = scratch_path / "plot.png"
        plot_panel.filedialog.asksaveasfilename = lambda **_kwargs: str(png_path)
        app.save_figure()
        assert png_path.exists() and png_path.stat().st_size > 0

        app.clear_all_traces()
        saved_snapshot = app._current_preset_snapshot()
        preset_actions.simpledialog.askstring = lambda *_args, **_kwargs: "UI smoke"
        app._show_nav("Preset")
        app.save_named_preset_dialog()
        assert preset_path.exists()
        app.mode.set("CURR" if app.mode.get() == "VOLT" else "VOLT")
        app.port.set("COM99")
        app.refresh_preset_list()
        item = next(
            item
            for item in app.preset_list.get_children()
            if app.preset_list.item(item, "values")[0] == "UI smoke"
        )
        app.preset_list.selection_set(item)
        app.load_selected_preset()
        assert app._current_preset_snapshot() == saved_snapshot

        assert not callback_errors, callback_errors
        print("PASS desktop UI user-flow smoke")
    finally:
        try:
            if app._connected:
                app.disconnect_hardware()
        finally:
            app.root.destroy()
            scratch.cleanup()


if __name__ == "__main__":
    main()
