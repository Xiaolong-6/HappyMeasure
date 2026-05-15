from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_plot_context_menu_unit_choices_are_static_regression():
    plot_panel = read("src/keith_ivt/ui/plot_panel.py")
    plot_controls = read("src/keith_ivt/ui/plot_controls.py")
    assert "@staticmethod\n    def _unit_choices_for_label(label: str)" in plot_panel
    assert "self._unit_choices_for_label(ax.get_xlabel())" in plot_controls
    assert "self._unit_choices_for_label(ax.get_ylabel())" in plot_controls


def test_hardware_uses_single_connect_disconnect_button():
    panels = read("src/keith_ivt/ui/panels.py")
    hardware = read("src/keith_ivt/ui/hardware_controller.py")
    assert "command=self.connect_or_disconnect" in panels
    assert "self.disconnect_btn" not in panels
    assert "def connect_or_disconnect" in hardware
    assert "self.disconnect_hardware()" in hardware
    assert 'text="Disconnect" if self._connected else "Connect"' in hardware
    assert '"disconnect_btn"' not in hardware
