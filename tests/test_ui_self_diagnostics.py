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
