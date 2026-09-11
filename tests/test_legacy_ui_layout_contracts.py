"""Small source-level UI contracts that complement behavior-oriented UI tests.

The former version of this module accumulated alpha/post-N layout-string checks
for widgets that had already moved or been replaced. Those checks made harmless
UI refactors look like release regressions. Keep only stable composition,
safety-copy and responsive-page contracts here; interactive behavior belongs in
the focused Tk/plot/settings tests.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "keith_ivt"


def source_text(relative: str) -> str:
    return (SRC / relative).read_text(encoding="utf-8")


def test_version_and_release_contract() -> None:
    from keith_ivt import version

    assert version.VERSION == "1.1b6"
    assert "1.1b6" in version.BUILD_NOTE.lower()
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "1.1b6"' in pyproject


def test_simple_app_remains_a_small_composition_root() -> None:
    app = source_text("ui/simple_app.py")
    mixins = source_text("ui/app_mixins.py")
    assert "class SimpleKeithIVtApp(AppChromeMixin, AppWorkflowMixin, AppPlotTraceMixin)" in app
    for name in (
        "HardwareControllerMixin",
        "SweepControllerMixin",
        "SettingsPresetMixin",
        "PlotPanelMixin",
        "TracePanelMixin",
    ):
        assert name in mixins


def test_pause_copy_keeps_output_on_warning_visible_in_source() -> None:
    operator = source_text("ui/operator_bar.py")
    assert "Pause holds the current source state" in operator
    assert "does not turn output off" in operator
    assert "Use STOP for output off" in operator


def test_navigation_rebuild_refreshes_short_viewport_scrollregion() -> None:
    navigation = source_text("ui/navigation.py")
    assert "builders[name](self.current_content)" in navigation
    assert "self.current_content.update_idletasks()" in navigation
    assert "self._refresh_content_scrollregion()" in navigation
    assert "self._refresh_content_scrollregion_later()" in navigation
    assert "self.content_canvas.yview_moveto(0.0)" in navigation


def test_plot_and_trace_actions_keep_separate_ownership() -> None:
    plot = source_text("ui/plot_panel.py")
    trace = source_text("ui/trace_panel.py")
    controls = source_text("ui/plot_controls.py")
    assert 'text="Views"' in plot
    assert "_show_trace_column_menu_from_button" in plot
    assert "suggested_single_csv_name" in trace
    assert 'label="Save plot image..."' in controls


def test_status_bar_owns_connection_and_live_measurement_summary() -> None:
    status = source_text("ui/status_bar.py")
    assert "textvariable=self.status_connection_text" in status
    assert "textvariable=self.status" in status
    assert "textvariable=self.measurement_status_text" in status
    assert "self.connection_light_canvas = tk.Canvas" in status
