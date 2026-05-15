from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def source_text(rel: str) -> str:
    return (SRC / "keith_ivt" / rel).read_text(encoding="utf-8")


def test_adaptive_table_imports_tooltip_helper_regression():
    src = source_text("ui/sweep_config.py")
    assert "from keith_ivt.ui.widgets import add_tip" in src
    assert "add_tip(ent" in src


def test_simple_app_uses_appstate_backed_compatibility_properties():
    app = source_text("ui/simple_app.py")
    bridge = source_text("ui/app_state_bridge.py")
    assert "AppStateBridgeMixin" in app
    assert "def _run_state(self) -> str" in bridge
    assert "return self.app_state.run_state_text" in bridge
    assert "def _connected(self) -> bool" in bridge
    assert "return self.app_state.is_connected" in bridge
    assert "self._running = False" not in app
    assert "self._paused = False" not in app
    assert "self._connected = False" not in app


def test_log_event_has_single_persistent_writer():
    src = source_text("ui/simple_app.py")
    log_event = src[src.index("def log_event"):]
    assert "self.app_log.write(message)" in log_event
    assert "append_app_event(message)" not in log_event


def test_naming_guide_contract():
    naming = (ROOT / "docs" / "NAMING.md").read_text(encoding="utf-8")
    assert "HappyMeasure is the only user-facing product name" in naming
    assert "keith_ivt" in naming
    grep_targets = [ROOT / "README.md", ROOT / "docs" / "AGENT_HANDOFF.md", ROOT / "docs" / "NEW_THREAD_CONTEXT.md"]
    for path in grep_targets:
        assert "SMU-IVCV Studio" not in path.read_text(encoding="utf-8")


def test_serial_retry_policy_retries_then_succeeds(monkeypatch):
    from keith_ivt.services import serial_safety
    from keith_ivt.services.serial_safety import SerialRetryPolicy

    monkeypatch.setattr(serial_safety.time, "sleep", lambda _s: None)
    attempts = {"n": 0}

    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise TimeoutError("temporary")
        return "ok"

    assert SerialRetryPolicy(max_attempts=3, base_delay_s=0.01).run(flaky) == "ok"
    assert attempts["n"] == 3


def test_output_off_guard_reports_failure():
    from keith_ivt.services.serial_safety import OutputOffGuard

    messages: list[str] = []
    ok = OutputOffGuard(logger=messages.append).turn_off(lambda: (_ for _ in ()).throw(RuntimeError("boom")), context="test")
    assert ok is False
    assert messages and "Output OFF failed" in messages[0]


def test_hardware_preflight_uses_idn_and_output_off(monkeypatch):
    from keith_ivt.services import hardware_preflight

    calls: list[str] = []

    class FakeInstrument:
        def __init__(self, port, baud_rate):
            calls.append(f"init:{port}:{baud_rate}")
        def connect(self):
            calls.append("connect")
        def identify(self):
            calls.append("identify")
            return "KEITHLEY INSTRUMENTS INC.,MODEL 2400,123,1.0"
        def output_off(self):
            calls.append("output_off")
        def close(self):
            calls.append("close")

    monkeypatch.setattr(hardware_preflight, "Keithley2400Serial", FakeInstrument)
    result = hardware_preflight.run_keithley_preflight("COM9", 9600)
    assert result.port == "COM9"
    assert "MODEL 2400" in result.idn
    assert result.output_off_confirmed is True
    assert calls == ["init:COM9:9600", "connect", "identify", "output_off", "close"]


def test_app_state_additional_transitions_and_status_strings():
    from keith_ivt.ui.app_state import AppState, ConnectionState, RunState

    state = AppState()
    events = []
    state.on_state_change("run_state", events.append)
    assert state.set_run_state(RunState.PAUSED) is False
    assert state.set_run_state(RunState.RUNNING) is True
    state.point_count = 2; state.estimated_total = 5
    assert state.get_status_string() == "Running 2/5"
    assert state.can_pause_sweep() is True
    assert state.request_pause() is True
    assert state.set_run_state(RunState.PAUSED) is True
    assert state.can_resume_sweep() is True
    assert state.get_status_string() == "Paused (2 points)"
    assert state.request_stop() is True
    assert state.set_run_state(RunState.STOPPING) is True
    state.force_idle()
    assert state.run_state is RunState.IDLE
    assert state.stop_requested is False
    assert events

    assert state.set_connection_state(ConnectionState.CONNECTED, device_id="IDN", device_model="2400") is True
    assert state.is_connected is True
    assert state.connected_device_model == "2400"
    assert state.set_connection_state(ConnectionState.CONNECTED, device_model="2450") is True
    assert state.connected_device_model == "2450"
    state.force_disconnected()
    assert state.connection_state is ConnectionState.DISCONNECTED

    state.set_error("bad")
    assert state.get_status_string() == "Error: bad"
    state.clear_error()
    assert state.run_state is RunState.IDLE


def test_thread_safe_buffer_additional_paths():
    from keith_ivt.utils.thread_safe import ThreadSafeBuffer, ThreadSafeXYBuffer

    b = ThreadSafeBuffer[str](maxsize=2)
    assert b.is_empty() is True
    assert b.pop_front() is None
    b.append("a"); b.append("b"); b.append("c")
    assert len(b) == 2
    assert b.get_snapshot() == ["b", "c"]
    b.clear()
    assert b.is_empty() is True

    xy = ThreadSafeXYBuffer(maxsize=2)
    xy.append(1, 10); xy.append(2, 20); xy.append(3, 30)
    assert len(xy) == 2
    assert xy.get_snapshot() == ([2, 3], [20, 30])
    xy.clear()
    assert xy.get_snapshot() == ([], [])
