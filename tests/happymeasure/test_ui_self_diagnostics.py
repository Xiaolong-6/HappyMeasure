from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from keith_ivt.diagnostics.ui_self_test import FAIL, PASS, UiDiagnosticCheck, UiDiagnosticReport, run_ui_self_test, write_ui_diagnostic_bundle


class _FakeTk:
    @staticmethod
    def call(*_args):
        return "8.6-test"


class _FakeRoot:
    tk = _FakeTk()


class _RunningState:
    is_running = True
    run_state = "sweeping"
    connection_state = "connected"


class _RunningApp:
    root = _FakeRoot()
    app_state = _RunningState()
    _active_nav = "Sweep"
    _connected_idn = "KEITHLEY INSTRUMENTS INC.,MODEL 2401"


def test_ui_self_test_refuses_to_mutate_during_active_measurement() -> None:
    report = run_ui_self_test(_RunningApp())
    assert report.overall == FAIL
    assert report.checks[0].name == "precondition"
    assert "Stop the run" in report.checks[0].detail


def test_ui_diagnostic_bundle_contains_machine_readable_summary(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "log.txt").write_text("line one\nline two\n", encoding="utf-8")
    report = UiDiagnosticReport(
        created_at="2026-09-10T15:00:00",
        app_version="test",
        python="python-test",
        platform="platform-test",
        tk_patchlevel="8.6-test",
        original_page="Settings",
        run_state="idle",
        connection_state="disconnected",
        instrument_idn="",
        checks=(UiDiagnosticCheck("example", PASS, "ok"),),
    )

    zip_path = write_ui_diagnostic_bundle(report, root=tmp_path)
    with ZipFile(zip_path) as archive:
        assert set(archive.namelist()) == {"app_log_tail.txt", "summary.json", "summary.txt"}
        payload = json.loads(archive.read("summary.json").decode("utf-8"))
        assert payload["overall"] == PASS
        assert payload["checks"][0]["name"] == "example"
        assert "line two" in archive.read("app_log_tail.txt").decode("utf-8")


def _make_tk_app():
    from keith_ivt.ui.simple_app import SimpleKeithIVtApp

    app = SimpleKeithIVtApp()
    app.root.update_idletasks()
    app._show_nav("Sweep")
    app.sweep_kind.set("TIME")
    app.root.update_idletasks()
    app.root.update()
    return app


def test_advanced_controls_disconnected_state_and_callback_pass() -> None:
    try:
        app = _make_tk_app()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Tk not available: {exc}")
    try:
        app.acquisition_advanced_visible.set(False)
        report = run_ui_self_test(app)
        availability = next(c for c in report.checks if c.name == "advanced_controls_availability")
        callback = next(c for c in report.checks if c.name == "advanced_controls_callback")
        assert availability.status == PASS
        assert "disabled" in availability.detail
        assert "disconnected" in availability.detail
        assert callback.status == PASS
        assert "False -> True -> False" in callback.detail
        assert report.overall == PASS
    finally:
        app.root.destroy()


def test_advanced_controls_connected_state_is_editable() -> None:
    try:
        app = _make_tk_app()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Tk not available: {exc}")
    try:
        from keith_ivt.ui.app_state import AppAction

        app.app_state.dispatch(AppAction.CONNECT_SIMULATED, device_id="SIM", device_model="sim")
        app._refresh_capability_widgets()
        app._show_nav("Sweep")
        app.root.update_idletasks()
        button = app.advanced_acquisition_button
        try:
            disabled = bool(button.instate(["disabled"]))
        except Exception:
            disabled = str(button.cget("state")) == "disabled"
        assert not disabled
        app.acquisition_advanced_visible.set(False)
        report = run_ui_self_test(app)
        assert next(c for c in report.checks if c.name == "advanced_controls_availability").status == PASS
        assert next(c for c in report.checks if c.name == "advanced_controls_callback").status == PASS
    finally:
        app.root.destroy()


def test_advanced_controls_callback_failure_is_reported() -> None:
    try:
        app = _make_tk_app()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Tk not available: {exc}")
    try:
        app.acquisition_advanced_visible.set(False)
        original_toggle = app._toggle_advanced_acquisition

        def broken_toggle() -> None:
            raise RuntimeError("toggle broken")

        app._toggle_advanced_acquisition = broken_toggle
        report = run_ui_self_test(app)
        callback = next(c for c in report.checks if c.name == "advanced_controls_callback")
        assert callback.status == FAIL
        assert "visible" in callback.detail
        assert "button_state" in callback.detail
        app._toggle_advanced_acquisition = original_toggle
    finally:
        app.root.destroy()
