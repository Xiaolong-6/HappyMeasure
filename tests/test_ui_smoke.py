from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def source_text(relative: str) -> str:
    return (SRC / "keith_ivt" / relative).read_text(encoding="utf-8")


def test_ui_split_modules_exist_and_are_wired() -> None:
    app = source_text("ui/simple_app.py")
    nav = source_text("ui/navigation.py")
    status = source_text("ui/status_bar.py")
    mixins = source_text("ui/app_mixins.py")
    assert "from keith_ivt.ui.navigation import NavigationMixin" in mixins
    assert "from keith_ivt.ui.status_bar import StatusBarMixin" in mixins
    assert "from keith_ivt.ui.operator_bar import OperatorBarMixin" in mixins
    assert "class SimpleKeithIVtApp(AppChromeMixin, AppWorkflowMixin, AppPlotTraceMixin)" in app
    assert "UiScaffoldMixin" in mixins and "HardwareControllerMixin" in mixins
    assert "class NavigationMixin" in nav and "def _build_navigation_drawer" in nav
    assert "class StatusBarMixin" in status and "def _build_status_bar" in status


def test_default_page_and_header_status_separation_contract() -> None:
    app = source_text("ui/simple_app.py")
    nav = source_text("ui/navigation.py")
    status = source_text("ui/status_bar.py")
    assert 'self._active_nav = "Hardware"' in app
    assert 'self._show_nav("Hardware")' in app
    assert "self.page_title" in source_text("ui/ui_scaffold.py")
    assert "self.header_status" not in app
    scaffold = source_text("ui/ui_scaffold.py")
    assert "textvariable=self.status_connection_text" not in scaffold
    assert "textvariable=self.status_connection_text" in status
    assert "no longer auto-hides" in nav


def test_live_only_plot_and_trace_list_contract() -> None:
    source_text("ui/simple_app.py")
    assert "self.plot_trace_pane.forget(self.trace_panel)" in source_text("ui/plot_panel.py")
    compact_plot = "".join(source_text("ui/plot_panel.py").split())
    assert 'traces=([]ifgetattr(self,"_plot_live_only",False)' in compact_plot
    assert (
        'getattr(self, "_run_state", "idle") in {"running", "paused", "stopping"}'
        in source_text("ui/plot_panel.py")
    )


def _sweep_dynamic_child_count(app) -> int:
    return len(app.dynamic_box.winfo_children())


@pytest.mark.skipif(
    os.environ.get("HAPPYMEASURE_RUN_TK_SMOKE") != "1",
    reason="Set HAPPYMEASURE_RUN_TK_SMOKE=1 on a desktop session to run Tk navigation smoke test",
)
def test_tk_navigation_sweep_lifecycle_has_no_crash_or_duplicate_frames() -> None:
    from keith_ivt.ui.simple_app import SimpleKeithIVtApp

    app = SimpleKeithIVtApp()
    try:
        app.root.update_idletasks()
        app.sweep_kind.set("TIME")
        app._show_nav("Sweep")
        app.root.update_idletasks()
        baseline = _sweep_dynamic_child_count(app)
        assert app.fast_acquisition_frame.winfo_exists()

        for page in ("Hardware", "Settings", "Preset", "Restore", "Log", "About"):
            app._show_nav("Sweep")
            app.root.update_idletasks()
            app._show_nav(page)
            app.root.update_idletasks()
            app._show_nav("Sweep")
            app.root.update_idletasks()
            assert app.dynamic_box.winfo_exists()
            assert _sweep_dynamic_child_count(app) == baseline

        for profile, away in (("Fast", "Hardware"), ("Fast", "Settings"), ("Custom", "Log")):
            app._ensure_acquisition_vars()
            app.acquisition_profile.set(profile)
            app._show_nav(away)
            app.root.update_idletasks()
            app._show_nav("Sweep")
            app.root.update_idletasks()
            assert app.dynamic_box.winfo_exists()
            assert _sweep_dynamic_child_count(app) == baseline
            assert app.fast_acquisition_frame.winfo_exists()
    finally:
        app.root.destroy()


@pytest.mark.skipif(
    os.environ.get("HAPPYMEASURE_RUN_TK_SMOKE") != "1",
    reason="Set HAPPYMEASURE_RUN_TK_SMOKE=1 on a desktop session to run Tk preset smoke test",
)
def test_tk_preset_apply_restores_acquisition_without_duplicate_controls() -> None:
    from keith_ivt.ui.simple_app import SimpleKeithIVtApp

    app = SimpleKeithIVtApp()
    try:
        app.root.update_idletasks()
        app.sweep_kind.set("TIME")
        app._show_nav("Sweep")
        app.root.update_idletasks()
        baseline = _sweep_dynamic_child_count(app)

        app._ensure_acquisition_vars()
        app.acquisition_profile.set("Fast")
        app._apply_acquisition_profile_state()
        fast_snapshot = app._current_preset_snapshot()
        assert fast_snapshot["sweep"]["acquisition"]["profile"] == "Fast"

        app.acquisition_profile.set("Standard")
        app._apply_acquisition_profile_state()
        assert app._apply_preset_snapshot(fast_snapshot) is True
        assert app.acquisition_profile.get() == "Fast"
        assert _sweep_dynamic_child_count(app) == baseline

        app.acquisition_profile.set("Custom")
        app.digital_filter.set(True)
        app.digital_filter_count.set(5)
        app.trigger_delay_s.set(0.004)
        app.source_write_each_sample.set(True)
        app.range_telemetry.set(True)
        custom_snapshot = app._current_preset_snapshot()
        app.digital_filter.set(False)
        app.digital_filter_count.set(2)
        app.trigger_delay_s.set(0.0)
        app.source_write_each_sample.set(False)
        app.range_telemetry.set(False)
        # Apply from a non-Sweep page: vars restore without touching dead widgets.
        app._show_nav("Preset")
        app.root.update_idletasks()
        assert app._apply_preset_snapshot(custom_snapshot) is True
        app._show_nav("Sweep")
        app.root.update_idletasks()
        assert app.acquisition_profile.get() == "Custom"
        assert app.digital_filter.get() is True
        assert app.digital_filter_count.get() == 5
        assert app.trigger_delay_s.get() == 0.004
        assert app.source_write_each_sample.get() is True
        assert app.range_telemetry.get() is True
        assert _sweep_dynamic_child_count(app) == baseline

        old = {"schema_version": 2, "hardware": {}, "sweep": {"kind": "TIME"}}
        assert app._apply_preset_snapshot(old) is True
        assert app.acquisition_profile.get() == "Standard"
    finally:
        app.root.destroy()


@pytest.mark.skipif(
    os.environ.get("HAPPYMEASURE_RUN_TK_SMOKE") != "1",
    reason="Set HAPPYMEASURE_RUN_TK_SMOKE=1 on a desktop session to run Tk capability smoke test",
)
def test_tk_acquisition_availability_follows_instrument_capability() -> None:
    from keith_ivt.drivers.base import DriverCapabilities
    from keith_ivt.ui.simple_app import SimpleKeithIVtApp

    app = SimpleKeithIVtApp()
    try:
        app.root.update_idletasks()
        app.sweep_kind.set("TIME")
        app._show_nav("Sweep")
        app.root.update_idletasks()
        app._ensure_acquisition_vars()

        # NOTE: set debug first: writing the debug var fires the
        # debug-change trace, which resets a live connection.
        app.debug.set(False)
        app._connected = True
        app._active_capabilities = DriverCapabilities(
            name="Keithley 2450 SMU", vendor="Keithley", model_family="2450-smu"
        )
        app._refresh_acquisition_availability()
        assert list(app.acquisition_profile_combo.cget("values")) == ["Standard"]
        assert app.acquisition_profile.get() == "Standard"

        app._active_capabilities = DriverCapabilities(
            name="Keithley 2400-series SMU",
            vendor="Keithley",
            model_family="2400-series-smu",
            supports_fast_acquisition=True,
        )
        app._refresh_acquisition_availability()
        assert list(app.acquisition_profile_combo.cget("values")) == [
            "Standard",
            "Fast",
            "Custom",
        ]

        app._connected = False
        app._refresh_acquisition_availability()
        assert list(app.acquisition_profile_combo.cget("values")) == [
            "Standard",
            "Fast",
            "Custom",
        ]
    finally:
        app.root.destroy()


@pytest.mark.skipif(
    os.environ.get("HAPPYMEASURE_RUN_TK_SMOKE") != "1",
    reason="Set HAPPYMEASURE_RUN_TK_SMOKE=1 on a desktop session to run Tk instantiation smoke test",
)
def test_tk_app_instantiates_default_hardware_page() -> None:
    from keith_ivt.ui.simple_app import SimpleKeithIVtApp

    app = SimpleKeithIVtApp()
    try:
        app.root.update_idletasks()
        assert app._active_nav == "Hardware"
        assert app.page_title.cget("text") == "Hardware"
        # Disconnected status text is intentionally short ("No instr"/"Sim off");
        # the longer "Instrument: ..." strings live in AppState for other consumers.
        expected_status = "Sim off" if bool(app.debug.get()) else "No instr"
        assert app.status_connection_text.get() == expected_status
        assert hasattr(app, "drawer_frame")
        assert hasattr(app, "status_bar")
    finally:
        app.root.destroy()
