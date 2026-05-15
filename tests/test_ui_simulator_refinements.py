from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_boolean_options_are_colored_toggle_buttons_not_checkboxes():
    helpers = read("src/keith_ivt/ui/widget_helpers.py")
    panels = read("src/keith_ivt/ui/panels.py")
    assert "ttk.Checkbutton" not in helpers
    assert "def _check" in helpers
    assert "ToggleOn.TButton" in helpers and "ToggleOff.TButton" in helpers
    assert "✓ {label}" in helpers and "○ {label}" in helpers
    assert "Use debug simulator" in panels and "Temporary cache" in panels


def test_range_controls_are_label_entry_auto_button_rows():
    panels = read("src/keith_ivt/ui/panels.py")
    helpers = read("src/keith_ivt/ui/widget_helpers.py")
    sweep = read("src/keith_ivt/ui/sweep_config.py")
    assert "_range_control_row(self.common_box, \"Source range\"" in panels
    assert "_range_control_row(self.common_box, \"Measure range\"" in panels
    assert "auto_btn.grid(row=row, column=2" in helpers
    assert "self._sync_toggle_button(pair[2], \"Auto\", auto_var)" in sweep


def test_current_source_diode_inverts_voltage_source_curve():
    sim = read("src/keith_ivt/instrument/simulator.py")
    assert "def _diode_current_at_voltage" in sim
    assert "def _diode_voltage_search_bounds" in sim
    assert "Current-source diode simulation must invert the same I(V) curve" in sim
    assert "report the actual" in sim
    assert "return current * self.resistance_ohm + 0.08" not in sim


def test_plot_mousewheel_targets_single_axis_under_cursor():
    controls = read("src/keith_ivt/ui/plot_controls.py")
    assert "def _axis_under_mouse" in controls
    assert "ax.get_window_extent().contains(x, y)" in controls
    wheel = controls[controls.index("def _on_plot_mousewheel"):]
    assert "for ax in self._axes" not in wheel[:700]
    assert "ax = self._axis_under_mouse(event)" in wheel


def test_log_panel_fills_canvas_height_on_resize_and_preset_buttons_expand():
    scaffold = read("src/keith_ivt/ui/ui_scaffold.py")
    preset = read("src/keith_ivt/ui/preset_restore_panel.py")
    assert "self._update_content_window_height(getattr(self, \"_active_nav\", None))" in scaffold
    assert "uniform=\"preset_actions\"" in preset
    assert "sticky=\"ew\", padx=3" in preset


def test_current_source_diode_numeric_inverse_roundtrip():
    from keith_ivt.instrument.simulator import SimulatedKeithley

    sim = SimulatedKeithley(model_name="Diode-like nonlinear")
    for voltage in [-0.2, 0.0, 0.2, 0.45, 0.65]:
        current = sim._current_from_voltage(voltage)
        recovered = sim._voltage_from_current(current)
        assert abs(recovered - voltage) < 1e-3


def test_about_panel_does_not_use_global_mousewheel_binding():
    panels = read("src/keith_ivt/ui/panels.py")
    assert ".bind_all(\"<MouseWheel>\"" not in panels
    assert "invalid command name" in panels
    assert "_bind_about_mousewheel(scroll_frame)" in panels


def test_linear_plot_is_standard_iv_for_current_source():
    from keith_ivt.models import SweepConfig, SweepMode, SweepPoint, SweepResult
    from keith_ivt.ui.plot_views import PlotView, xy_for_view

    cfg = SweepConfig(mode=SweepMode.CURRENT_SOURCE, start=0.0, stop=0.0, step=1.0, compliance=10.0)
    result = SweepResult(cfg, [SweepPoint(source_value=1e-3, measured_value=0.76)])
    x, y, xlabel, ylabel, title, y_is_log = xy_for_view(result, PlotView.LINEAR)
    assert x == [0.76]
    assert y == [1e-3]
    assert xlabel == "Voltage (V)"
    assert ylabel == "Current (A)"
    assert title == "I-V curve"
    assert y_is_log is False


def test_current_source_diode_reports_actual_current_when_compliance_limited():
    from keith_ivt.instrument.simulator import SimulatedKeithley
    from keith_ivt.models import SweepConfig, SweepMode

    sim = SimulatedKeithley(model_name="Diode-like nonlinear")
    sim.noise_fraction = 0.0
    sim.configure_for_sweep(SweepConfig(mode=SweepMode.CURRENT_SOURCE, start=-1e-3, stop=1e-3, step=1e-3, compliance=10.0))

    sim.set_source("CURR", -1e-3)
    actual_current, measured_voltage = sim.read_source_and_measure()
    assert measured_voltage <= -9.9
    assert abs(actual_current) < 2e-5
    assert abs(actual_current - sim._current_from_voltage(measured_voltage)) < 1e-12

    sim.set_source("CURR", 1e-3)
    actual_current, measured_voltage = sim.read_source_and_measure()
    assert 0.7 < measured_voltage < 0.85
    assert abs(actual_current - 1e-3) < 1e-6
