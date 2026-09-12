from __future__ import annotations

import pytest

from keith_ivt.diagnostics.ui_self_test import PASS, run_ui_self_test


def _make_tk_app():  # type: ignore[no-untyped-def]
    from keith_ivt.ui.simple_app import SimpleKeithIVtApp

    app = SimpleKeithIVtApp()
    app.root.update_idletasks()
    app._show_nav("Sweep")
    app.sweep_kind.set("TIME")
    app.root.update_idletasks()
    app.root.update()
    return app


def _descendants(widget):  # type: ignore[no-untyped-def]
    for child in widget.winfo_children():
        yield child
        yield from _descendants(child)


def _bottom_relative_to(widget, ancestor) -> int:
    bottom = widget.winfo_y() + widget.winfo_reqheight()
    current = widget
    while current.master is not ancestor:
        current = current.master
        bottom += current.winfo_y()
    return bottom


def test_settings_diagnostics_rebuild_keeps_bottom_buttons_scrollable() -> None:
    try:
        app = _make_tk_app()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Tk not available: {exc}")
    try:
        app.root.minsize(760, 1)
        app.root.geometry("900x220")
        app._ensure_developer_tools_var().set(True)
        app._show_nav("Settings")
        app.root.update_idletasks()
        report = run_ui_self_test(app)
        app.root.update_idletasks()

        buttons = {
            str(widget.cget("text")): widget
            for widget in _descendants(app.current_content)
            if str(widget.winfo_class()) == "TButton"
        }
        ui_button = buttons["Run UI Diagnostics..."]
        hardware_button = buttons["Run Hardware Diagnostics..."]
        scrollregion = tuple(
            float(value) for value in app.content_canvas.cget("scrollregion").split()
        )
        bottom = _bottom_relative_to(hardware_button, app.current_content)

        assert report.overall == PASS
        assert scrollregion[3] >= bottom
        assert scrollregion[3] > app.content_canvas.winfo_height()
        assert hardware_button.bind("<MouseWheel>")
        assert ui_button.winfo_exists()
    finally:
        app.root.destroy()


def test_advanced_acquisition_filter_count_follows_custom_filter_state() -> None:
    try:
        app = _make_tk_app()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Tk not available: {exc}")
    try:
        app.sweep_kind.set("TIME")
        app._show_nav("Sweep")
        app.root.update_idletasks()
        app.acquisition_profile.set("Custom")
        app._apply_acquisition_profile_state()
        app._toggle_advanced_acquisition()
        app.root.update_idletasks()

        labels = {
            str(widget.cget("text"))
            for widget in _descendants(app.advanced_acquisition_frame)
            if str(widget.winfo_class()) == "TCheckbutton"
        }
        assert "Digital filter" in labels
        assert "Live range telemetry" in labels

        app.digital_filter.set(False)
        app._update_filter_count_state()
        assert app.digital_filter_count_entry.instate(["disabled"])

        app.digital_filter.set(True)
        app._update_filter_count_state()
        assert app.digital_filter_count_entry.instate(["!disabled"])

        app.acquisition_profile.set("Standard")
        app._apply_acquisition_profile_state()
        assert app.digital_filter_count_entry.instate(["disabled"])
    finally:
        app.root.destroy()


def test_preset_apply_ignores_destroyed_constant_time_filter_entry() -> None:
    """Applying a preset must not touch a stale widget from a previous page."""

    try:
        app = _make_tk_app()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Tk not available: {exc}")
    try:
        app._ensure_acquisition_vars()
        app.acquisition_profile.set("Custom")
        app.digital_filter.set(True)
        app.digital_filter_count.set(7)
        app.trigger_delay_s.set(0.004)
        app.source_write_each_sample.set(True)
        app.range_telemetry.set(True)
        app._apply_acquisition_profile_state()
        snapshot = app._current_preset_snapshot()

        stale_entry = app.digital_filter_count_entry
        app._show_nav("Preset")
        app.root.update_idletasks()
        assert not stale_entry.winfo_exists()
        assert app.digital_filter_count_entry is stale_entry

        assert app._apply_preset_snapshot(snapshot) is True
        assert app.acquisition_profile.get() == "Custom"
        assert app.digital_filter.get() is True
        assert app.digital_filter_count.get() == 7
        assert app.trigger_delay_s.get() == 0.004
        assert app.source_write_each_sample.get() is True
        assert app.range_telemetry.get() is True

        app._show_nav("Sweep")
        app.root.update_idletasks()
        assert app.digital_filter_count_entry is not stale_entry
        assert app.digital_filter_count_entry.winfo_exists()
        assert app.digital_filter_count_entry.instate(["!disabled"])
    finally:
        app.root.destroy()
