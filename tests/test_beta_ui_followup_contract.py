from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_update_controller_has_about_message_api_and_about_never_starts_blank() -> None:
    updates = read("src/keith_ivt/ui/update_controller.py")
    panels = read("src/keith_ivt/ui/panels.py")
    assert "def _set_update_check_message" in updates
    assert "def _default_update_status_message" in updates
    assert "Manual upgrade remains available" in updates
    assert "self._set_update_check_message(self.update_notice_text.get())" in panels


def test_status_bar_is_compact_and_uses_live_vi_readout() -> None:
    status = read("src/keith_ivt/ui/status_bar.py")
    app_state = read("src/keith_ivt/ui/app_state.py")
    simple = read("src/keith_ivt/ui/simple_app.py")
    controller = read("src/keith_ivt/ui/sweep_controller.py")
    assert "textvariable=self.status_connection_text" in status
    assert "textvariable=self.status" in status
    assert "textvariable=self.live_readout_text" in status
    assert "textvariable=self.last_save_text" not in status
    assert "Running {self.point_count}" not in app_state
    assert "Paused ({self.point_count} points)" not in app_state
    assert 'StringVar(value="V -- · I --")' in simple
    assert "format_voltage" in controller and "format_current" in controller


def test_range_auto_buttons_remain_clickable_outside_active_runs() -> None:
    sweep_config = read("src/keith_ivt/ui/sweep_config.py")
    assert '{"preparing", "running", "sweeping", "paused", "stopping"}' in sweep_config
    assert "editable = not busy" in sweep_config
    assert 'state="normal" if editable else "disabled"' in sweep_config


def test_trace_visible_column_shows_checked_and_latest_trace_selection_hook_exists() -> None:
    trace_panel = read("src/keith_ivt/ui/trace_panel.py")
    sweep_controller = read("src/keith_ivt/ui/sweep_controller.py")
    assert '"☑" if trace.visible else "☐"' in trace_panel
    assert "def _select_trace_id" in trace_panel
    assert "new_trace = self._datasets.add_result" in sweep_controller
    assert "self._select_trace_id(new_trace.trace_id)" in sweep_controller


def test_plot_context_menu_supports_xy_axis_swap() -> None:
    controls = read("src/keith_ivt/ui/plot_controls.py")
    panel = read("src/keith_ivt/ui/plot_panel.py")
    simple = read("src/keith_ivt/ui/simple_app.py")
    assert "plot_swap_xy" in simple
    assert "Swap X/Y axes" in controls
    assert "def _apply_plot_xy_swap" in panel
    assert "ax.set_xscale(\"log\")" in panel
