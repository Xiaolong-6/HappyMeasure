from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

from keith_ivt.diagnostics.ui_self_test import (
    FAIL,
    PASS,
    UiDiagnosticCheck,
    UiDiagnosticReport,
    run_ui_self_test,
    write_ui_diagnostic_bundle,
)


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
    assert zip_path.exists()
    with ZipFile(zip_path) as archive:
        assert set(archive.namelist()) == {
            "app_log_tail.txt",
            "summary.json",
            "summary.txt",
        }
        payload = json.loads(archive.read("summary.json").decode("utf-8"))
        assert payload["overall"] == PASS
        assert payload["checks"][0]["name"] == "example"
        assert "line two" in archive.read("app_log_tail.txt").decode("utf-8")


def test_diagnostics_ui_is_wired_without_growing_simple_app() -> None:
    root = Path(__file__).resolve().parents[1]
    mixins = (root / "src" / "keith_ivt" / "ui" / "app_mixins.py").read_text(encoding="utf-8")
    panel = (root / "src" / "keith_ivt" / "ui" / "diagnostics_panel.py").read_text(
        encoding="utf-8"
    )
    assert "DiagnosticsUiMixin" in mixins
    assert "Run UI Diagnostics..." in panel
    assert "does not Connect, Start, Pause, Stop" in panel


def _make_tk_app():  # type: ignore[no-untyped-def]
    from keith_ivt.ui.simple_app import SimpleKeithIVtApp

    app = SimpleKeithIVtApp()
    app.root.update_idletasks()
    app._show_nav("Sweep")
    app.sweep_kind.set("TIME")
    app.root.update_idletasks()
    app.root.update()
    return app


def test_advanced_controls_disconnected_disabled_is_expected_and_callback_passes() -> None:
    try:
        app = _make_tk_app()
    except Exception as exc:  # noqa: BLE001
        import pytest

        pytest.skip(f"Tk not available: {exc}")
    try:
        # Disconnected state: Sweep controls are read-only, button disabled.
        assert app.app_state.connection_state.value == "disconnected"
        btn = getattr(app, "advanced_acquisition_button", None)
        assert btn is not None
        # Ensure visible starts False for deterministic toggle.
        app.acquisition_advanced_visible.set(False)
        app.root.update_idletasks()
        report = run_ui_self_test(app)
        avail = next(c for c in report.checks if c.name == "advanced_controls_availability")
        callback = next(c for c in report.checks if c.name == "advanced_controls_callback")
        assert avail.status == PASS
        assert "disabled" in avail.detail
        assert "disconnected" in avail.detail
        assert callback.status == PASS
        assert "False -> True -> False" in callback.detail
        assert report.overall == PASS
    finally:
        try:
            app.root.destroy()
        except Exception:
            pass


def test_advanced_controls_connected_editable_uses_invoke() -> None:
    try:
        app = _make_tk_app()
    except Exception as exc:  # noqa: BLE001
        import pytest

        pytest.skip(f"Tk not available: {exc}")
    try:
        # Simulate connected simulator: should enable Fast/Custom and button.
        from keith_ivt.ui.app_state import AppAction

        app.app_state.dispatch(AppAction.CONNECT_SIMULATED, device_id="SIM", device_model="sim")
        app._refresh_capability_widgets()
        app._show_nav("Sweep")
        app.root.update_idletasks()
        btn = getattr(app, "advanced_acquisition_button", None)
        assert btn is not None
        # In connected simulated state, button should be enabled.
        try:
            is_disabled = bool(btn.instate(["disabled"]))  # type: ignore[attr-defined]
        except Exception:
            is_disabled = str(btn.cget("state")) == "disabled"  # type: ignore[attr-defined]
        assert not is_disabled, "expected enabled button when connected"
        app.acquisition_advanced_visible.set(False)
        report = run_ui_self_test(app)
        avail = next(c for c in report.checks if c.name == "advanced_controls_availability")
        callback = next(c for c in report.checks if c.name == "advanced_controls_callback")
        assert avail.status == PASS
        assert "enabled" in avail.detail
        assert callback.status == PASS
    finally:
        try:
            app.root.destroy()
        except Exception:
            pass


def test_advanced_controls_callback_failure_is_reported() -> None:
    try:
        app = _make_tk_app()
    except Exception as exc:  # noqa: BLE001
        import pytest

        pytest.skip(f"Tk not available: {exc}")
    try:
        app.acquisition_advanced_visible.set(False)
        original_toggle = app._toggle_advanced_acquisition

        def broken_toggle() -> None:
            raise RuntimeError("toggle broken")

        app._toggle_advanced_acquisition = broken_toggle  # type: ignore[method-assign]
        report = run_ui_self_test(app)
        callback = next(c for c in report.checks if c.name == "advanced_controls_callback")
        assert callback.status == FAIL
        assert "visible" in callback.detail
        assert "button_state" in callback.detail
        # Restore for cleanup
        app._toggle_advanced_acquisition = original_toggle  # type: ignore[method-assign]
    finally:
        try:
            app.root.destroy()
        except Exception:
            pass
