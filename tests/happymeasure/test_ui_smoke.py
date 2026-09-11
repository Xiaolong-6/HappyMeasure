from __future__ import annotations

import os

import pytest


def _sweep_dynamic_child_count(app) -> int:
    return len(app.dynamic_box.winfo_children())


pytestmark = pytest.mark.skipif(
    os.environ.get("HAPPYMEASURE_RUN_TK_SMOKE") != "1",
    reason="Set HAPPYMEASURE_RUN_TK_SMOKE=1 on a desktop session to run Tk smoke tests",
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
    finally:
        app.root.destroy()


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
        app.debug.set(False)
        app._connected = True
        app._active_capabilities = DriverCapabilities(
            name="Keithley 2450 SMU", vendor="Keithley", model_family="2450-smu"
        )
        app._refresh_acquisition_availability()
        assert list(app.acquisition_profile_combo.cget("values")) == ["Standard"]

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
    finally:
        app.root.destroy()


def test_tk_app_instantiates_expected_workspace_structure() -> None:
    from keith_ivt.ui.simple_app import SimpleKeithIVtApp

    app = SimpleKeithIVtApp()
    try:
        app.root.update_idletasks()
        assert app._active_nav == "Hardware"
        assert app.page_title.cget("text") == "Hardware"
        expected_status = "Sim off" if bool(app.debug.get()) else "No instr"
        assert app.status_connection_text.get() == expected_status
        assert app.action_bar.master is app.root
        assert app.status_bar.master is app.root
        assert int(app.action_bar.grid_info()["row"]) == 1
        assert int(app.status_bar.grid_info()["row"]) == 2
        assert hasattr(app, "drawer_frame")
    finally:
        app.root.destroy()
