from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_alpha3_status_theme_navigation_contracts():
    simple = read("src/keith_ivt/ui/simple_app.py")
    status = read("src/keith_ivt/ui/status_bar.py")
    theme = read("src/keith_ivt/ui/theme.py")
    nav = read("src/keith_ivt/ui/navigation.py")
    settings = read("src/keith_ivt/data/settings.py")
    assert "self.last_save_text" in simple
    assert "textvariable=self.last_save_text" in status
    assert '"Debug"' in theme and '"Light"' in settings
    assert '"Hardware": ("🔌", "Hardware")' in nav
    assert "_nav_drawer_width" in nav and "size * 9" in nav
    assert "😈" in read("src/keith_ivt/ui/hardware_controller.py")


def test_alpha3_import_export_and_plot_menu_contracts():
    data = read("src/keith_ivt/ui/data_actions.py")
    trace_controls = read("src/keith_ivt/ui/trace_controls.py")
    trace_panel = read("src/keith_ivt/ui/trace_panel.py")
    plot_controls = read("src/keith_ivt/ui/plot_controls.py")
    plot_panel = read("src/keith_ivt/ui/plot_panel.py")
    assert "_resolve_import_overlap" in data
    assert "askyesnocancel" in data
    assert "Export visible" in trace_controls
    assert "def save_checked_traces" in trace_panel
    assert "_show_plot_context_menu_tk" in plot_controls
    assert '<Button-3>' in plot_panel and '<Control-Button-1>' in plot_panel


def test_alpha3_hardware_log_stop_contracts():
    panels = read("src/keith_ivt/ui/panels.py")
    hardware = read("src/keith_ivt/ui/hardware_controller.py")
    runner = read("src/keith_ivt/core/sweep_runner.py")
    assert "self.port_combo = self._combo" in panels
    assert "_detect_serial_ports" in hardware and "list_ports.comports" in hardware
    assert "_interruptible_sleep" in runner
    assert "_interruptible_sleep(max(0.0, config.interval_s), should_stop)" in runner
    log = panels[panels.index('def _build_log_panel'):panels.index('def _build_about_panel')]
    assert 'box.grid(row=0, column=0, sticky="nsew"' in log
    assert 'self.log_text.grid(row=1, column=0, sticky="nsew")' in log
