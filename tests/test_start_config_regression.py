from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def source_text(relative: str) -> str:
    return (SRC / "keith_ivt" / relative).read_text(encoding="utf-8")




def test_start_sweep_allows_completed_stopped_and_aborted_ready_states() -> None:
    sweep_controller = source_text("ui/sweep_controller.py")
    assert 'ready_states = {"idle", "stopped", "completed", "aborted"}' in sweep_controller
    assert 'if self._run_state not in ready_states:' in sweep_controller
    assert 'if self._run_state != "idle":' not in sweep_controller

def test_make_config_imports_model_enums_after_decomposition() -> None:
    """Start path must not lose model imports when simple_app is kept tiny."""
    app = source_text("ui/simple_app.py")
    sweep_config = source_text("ui/sweep_config.py")
    assert "from keith_ivt.models import SenseMode, SweepConfig, SweepKind, SweepMode, SweepResult, Terminal" in app
    assert "def _mode_from_ui" in sweep_config
    assert "def _sweep_kind_from_ui" in sweep_config
    make_config = app[app.index("def _make_config"):]
    assert "mode=self._mode_from_ui()" in make_config
    assert "sweep_kind=sweep_kind" in make_config
    assert "terminal=Terminal(self._terminal_scpi" in make_config
    assert "sense_mode=SenseMode(self._sense_scpi" in make_config


def test_plot_toolbar_fills_width_for_wrapping_without_residual_empty_column() -> None:
    plot = source_text("ui/plot_panel.py")
    assert 'toolbar.grid(row=0, column=0, sticky="ew"' in plot
    assert 'toolbar.columnconfigure(1, weight=1)' in plot
    assert 'view toolbar take the available width' in plot


def test_visual_polish_uses_explicit_scrollbar_and_status_styles() -> None:
    scaffold = source_text("ui/ui_scaffold.py")
    plot = source_text("ui/plot_panel.py")
    status = source_text("ui/status_bar.py")
    operator = source_text("ui/operator_bar.py")
    assert 'style="Vertical.TScrollbar"' in scaffold
    assert 'style="Vertical.TScrollbar"' in plot
    assert 'style="StatusCell.TLabel"' in status
    assert '[(2, 170), (2, 170), (3, 300)]' in operator


def test_make_config_smoke_with_tk_when_enabled() -> None:
    if os.environ.get("HAPPYMEASURE_RUN_TK_SMOKE") != "1":
        return
    from keith_ivt.models import SweepMode
    from keith_ivt.ui.simple_app import SimpleKeithIVtApp

    app = SimpleKeithIVtApp()
    try:
        cfg = app._make_config()
        assert cfg.mode is SweepMode.VOLTAGE_SOURCE
        assert cfg.device_name
    finally:
        app.root.destroy()


def test_make_config_accepts_display_sweep_kind_labels_when_tk_enabled() -> None:
    if os.environ.get("HAPPYMEASURE_RUN_TK_SMOKE") != "1":
        return
    from keith_ivt.models import SweepKind
    from keith_ivt.ui.simple_app import SimpleKeithIVtApp

    app = SimpleKeithIVtApp()
    try:
        app.sweep_kind.set("Time")
        cfg = app._make_config()
        assert cfg.sweep_kind is SweepKind.CONSTANT_TIME
        app.sweep_kind.set("Adaptive")
        cfg = app._make_config()
        assert cfg.sweep_kind is SweepKind.ADAPTIVE
    finally:
        app.root.destroy()


def test_sweep_worker_uses_config_snapshot_not_tk_variables() -> None:
    sweep_controller = source_text("ui/sweep_controller.py")
    hardware = source_text("ui/hardware_controller.py")
    simple = source_text("ui/simple_app.py")
    assert "self._pause_event = threading.Event()" in simple
    assert "self._stop_event = threading.Event()" in simple
    assert "with self._make_instrument(config) as inst" in sweep_controller
    assert "stop_event.is_set" in sweep_controller
    assert "pause_event.is_set" in sweep_controller
    assert "def _make_instrument(self, config=None):" in hardware
    assert "if config.debug:" in hardware
    assert "config.debug_model" in hardware
    assert "config.port" in hardware


def test_debug_pause_and_stop_buttons_drive_worker_events_when_tk_enabled() -> None:
    if os.environ.get("HAPPYMEASURE_RUN_TK_SMOKE") != "1":
        return
    import time
    from tkinter import messagebox

    from keith_ivt.ui.simple_app import SimpleKeithIVtApp

    messagebox.showerror = lambda *args, **kwargs: None
    messagebox.showinfo = lambda *args, **kwargs: None
    app = SimpleKeithIVtApp()
    try:
        app.debug.set(True)
        app.connect_or_check()
        app.sweep_kind.set("Time")
        app.constant_until_stop.set(True)
        app.interval_s.set(0.25)
        app.start_sweep()
        for _ in range(3):
            app.root.update()
            time.sleep(0.05)
        assert app._run_state == "running"
        assert str(app.pause_btn.cget("state")) == "normal"
        assert str(app.stop_btn.cget("state")) == "normal"
        app.pause_btn.invoke()
        app.root.update()
        assert app._run_state == "paused"
        assert app._pause_event.is_set()
        app.stop_btn.invoke()
        for _ in range(20):
            app.root.update()
            time.sleep(0.05)
            if app._run_state == "idle":
                break
        assert app._run_state == "idle"
        assert app.status.get() in {"Stopped", "Completed"}
    finally:
        app.root.destroy()
