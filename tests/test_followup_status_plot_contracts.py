from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from keith_ivt.models import SweepConfig, SweepKind, SweepMode, SweepPoint, SweepResult
from keith_ivt.ui.plot_views import PlotView, xy_for_view


def source_text(relative: str) -> str:
    return (SRC / "keith_ivt" / relative).read_text(encoding="utf-8")


def test_controls_header_and_front_panel_hooks_exist() -> None:
    simple_app = source_text("ui/simple_app.py")
    operator_bar = source_text("ui/operator_bar.py")
    status_bar = source_text("ui/status_bar.py")
    update_controller = source_text("ui/update_controller.py")
    assert "controls_title_text" in simple_app
    assert "textvariable=self.controls_title_text" in operator_bar
    assert "measurement_status_text" in simple_app
    assert "_open_front_panel_popup" in status_bar
    assert "_set_update_check_message" in update_controller


def test_current_source_linear_plot_uses_current_on_x_axis() -> None:
    config = SweepConfig(
        mode=SweepMode.CURRENT_SOURCE,
        start=0.0,
        stop=1e-3,
        step=1e-3,
        compliance=10.0,
        debug=True,
        sweep_kind=SweepKind.STEP,
    )
    result = SweepResult(config, [SweepPoint(source_value=1e-3, measured_value=2.5, elapsed_s=0.1)])
    x, y, xlabel, ylabel, title, y_is_log = xy_for_view(result, PlotView.LINEAR)
    assert x == [1e-3]
    assert y == [2.5]
    assert xlabel == "Current (A)"
    assert ylabel == "Voltage (V)"
    assert title == "V-I curve"
    assert y_is_log is False


def test_plot_fullscreen_and_swap_contracts_exist() -> None:
    controls = source_text("ui/plot_controls.py")
    panel = source_text("ui/plot_panel.py")
    assert "Save screenshot..." in controls
    assert "Swap X/Y axes" in controls
    assert "_swap_xy_for_axis_view" in panel
    assert "figure.set_layout_engine(\"constrained\")" in panel or "warnings.catch_warnings" in panel


def test_no_duplicate_panel_titles_or_inline_info_rows() -> None:
    widgets = source_text("ui/widget_helpers.py")
    scaffold = source_text("ui/ui_scaffold.py")
    nav = source_text("ui/navigation.py")
    presets = source_text("ui/preset_restore_panel.py")
    panels = source_text("ui/panels.py")
    assert "heading.pack" not in widgets
    assert "add_tip(self.page_title" in scaffold
    assert "add_tip(self.page_title" in nav
    assert "Named presets" not in presets
    assert "Sweep settings presets" not in presets
    assert "Autosave backups" not in presets
    assert "text=__release_stage__" not in panels
    assert "Release stage:" in panels
