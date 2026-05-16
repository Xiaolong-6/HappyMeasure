from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def source_text(relative: str) -> str:
    return (SRC / "keith_ivt" / relative).read_text(encoding="utf-8")


def test_alpha4_engineering_modules_are_wired() -> None:
    app = source_text("ui/simple_app.py")
    mixins = source_text("ui/app_mixins.py")
    expected = [
        "UiScaffoldMixin",
        "PresetRestorePanelMixin",
        "WidgetHelperMixin",
        "SweepConfigMixin",
        "HardwareControllerMixin",
        "SweepControllerMixin",
        "DataActionMixin",
        "SettingsPresetMixin",
        "UpdateControllerMixin",
    ]
    for name in expected:
        assert name in mixins
    assert "class SimpleKeithIVtApp(AppChromeMixin, AppWorkflowMixin, AppPlotTraceMixin)" in app
    assert app.count("def ") <= 8


def test_simple_app_is_composition_root_size_control() -> None:
    app_path = SRC / "keith_ivt" / "ui" / "simple_app.py"
    lines = app_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) < 380
    assert "def connect_or_check" not in app_path.read_text(encoding="utf-8")
    assert "def start_sweep" not in app_path.read_text(encoding="utf-8")
    assert "def _build_restore_panel" not in app_path.read_text(encoding="utf-8")


def test_app_state_is_synchronized_but_legacy_safe() -> None:
    hw = source_text("ui/hardware_controller.py")
    sw = source_text("ui/sweep_controller.py")
    assert "AppAction.CONNECT_SUCCESS" in hw
    assert "AppAction.CONNECT_SIMULATED" in hw
    assert "self.app_state.dispatch(AppAction.DISCONNECT" in hw
    assert "self.app_state.dispatch(action)" in hw
    assert "self.app_state.request_stop()" in sw
    assert "self.app_state.request_pause()" in sw
    assert "self.app_state.clear_pause_request()" in sw
    assert "self._run_state = state" not in hw


def test_thread_safe_xy_buffer_is_populated_by_live_points() -> None:
    app = source_text("ui/simple_app.py")
    sw = source_text("ui/sweep_controller.py")
    assert "self._measurement_xy = ThreadSafeXYBuffer(maxsize=10000)" in app
    assert "self._measurement_xy.append(point.source_value, point.measured_value)" in sw
    assert "self._measurement_xy.clear()" in sw


def test_documentation_tracks_current_architecture() -> None:
    assert "0.7a1" in (ROOT / "docs" / "ARCHITECTURE_CURRENT.md").read_text(encoding="utf-8")
    assert "State migration strategy" in (ROOT / "docs" / "DESIGN_DECISIONS.md").read_text(encoding="utf-8")
    handoff = (ROOT / "docs" / "AGENT_HANDOFF.md").read_text(encoding="utf-8")
    assert "ui/hardware_controller.py" in handoff
    assert "ui/sweep_controller.py" in handoff
    assert "Known limitations" in handoff
