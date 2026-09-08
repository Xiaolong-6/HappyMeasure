from __future__ import annotations

from pathlib import Path

import pytest

import keith_ivt.services.power_guard as power_guard
from keith_ivt.services.power_guard import (
    ES_CONTINUOUS,
    ES_SYSTEM_REQUIRED,
    prevent_system_sleep,
)
from keith_ivt.ui import hardware_controller
from keith_ivt.ui.app_state import AppState, ConnectionState
from keith_ivt.ui.hardware_controller import HardwareControllerMixin


class _Var:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value) -> None:
        self.value = value


class _Probe:
    def __init__(self, idn: str, *, beep_error: Exception | None = None) -> None:
        self.idn = idn
        self.beep_error = beep_error
        self.identify_calls = 0
        self.beep_calls = 0
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.closed = True

    def identify(self) -> str:
        self.identify_calls += 1
        if isinstance(self.idn, Exception):
            raise self.idn
        return self.idn

    def beep(self) -> None:
        self.beep_calls += 1
        if self.beep_error is not None:
            raise self.beep_error


class _HardwareHarness(HardwareControllerMixin):
    def __init__(self, probe: _Probe, *, debug: bool = False) -> None:
        self.app_state = AppState()
        self.debug = _Var(debug)
        self.port = _Var("COM_FAKE")
        self._probe = probe
        self.logs: list[str] = []
        self._active_capabilities = self._default_capabilities()
        self._connected_idn = ""

    def _make_instrument(self, config=None):
        return self._probe

    def log_event(self, message: str) -> None:
        self.logs.append(message)

    def _refresh_connection_status_from_state(self) -> None:
        pass

    def _refresh_run_status_from_state(self) -> None:
        pass

    def _refresh_port_choices(self) -> list[str]:
        return [self.port.get()]

    def _refresh_instrument_indicator(self) -> None:
        pass

    def _refresh_capability_widgets(self) -> None:
        pass

    def _update_run_button_states(self) -> None:
        pass


def test_real_2400_connection_beeps_after_idn_and_remains_connected() -> None:
    probe = _Probe("KEITHLEY INSTRUMENTS INC.,MODEL 2400,123,1.0")
    harness = _HardwareHarness(probe)

    harness.connect_or_check()

    assert probe.identify_calls == 1
    assert probe.beep_calls == 1
    assert probe.closed is True
    assert harness._connected_idn == probe.idn
    assert harness.app_state.connection_state is ConnectionState.CONNECTED
    assert harness._active_capabilities.model_family == "2400-series-smu"


def test_beep_failure_does_not_invalidate_connection(monkeypatch) -> None:
    probe = _Probe(
        "KEITHLEY,MODEL 2400,123,1.0",
        beep_error=RuntimeError("beeper unavailable"),
    )
    harness = _HardwareHarness(probe)
    monkeypatch.setattr(hardware_controller.messagebox, "showerror", lambda *args: pytest.fail())

    harness.connect_or_check()

    assert harness.app_state.connection_state is ConnectionState.CONNECTED
    assert harness._connected_idn == probe.idn
    assert any("instrument beep unavailable" in message for message in harness.logs)


def test_identify_failure_keeps_original_connection_error_path(monkeypatch) -> None:
    probe = _Probe(RuntimeError("IDN timeout"))
    harness = _HardwareHarness(probe)
    errors: list[str] = []
    monkeypatch.setattr(
        hardware_controller.messagebox, "showerror", lambda title, text: errors.append(text)
    )

    harness.connect_or_check()

    assert harness.app_state.connection_state is ConnectionState.ERROR
    assert harness._connected_idn == ""
    assert errors == ["IDN timeout"]


def test_simulator_connection_skips_instrument_beep() -> None:
    probe = _Probe("SIMULATED,Debug simulator,1,0")
    harness = _HardwareHarness(probe, debug=True)

    harness.connect_or_check()

    assert harness.app_state.connection_state is ConnectionState.SIMULATED
    assert probe.beep_calls == 0


def test_power_guard_acquires_system_required_and_releases() -> None:
    calls: list[int] = []
    logs: list[str] = []

    def setter(flags: int) -> int:
        calls.append(flags)
        return 1

    with prevent_system_sleep(
        logs.append,
        platform="win32",
        set_thread_execution_state=setter,
    ) as guard:
        assert guard.active is True

    assert calls == [ES_CONTINUOUS | ES_SYSTEM_REQUIRED, ES_CONTINUOUS]
    assert logs == [
        "System sleep prevention enabled for active measurement.",
        "System sleep prevention released.",
    ]


def test_power_guard_releases_on_exception() -> None:
    calls: list[int] = []

    def setter(flags: int) -> int:
        calls.append(flags)
        return 1

    with pytest.raises(RuntimeError, match="measurement failed"):
        with prevent_system_sleep(platform="win32", set_thread_execution_state=setter):
            raise RuntimeError("measurement failed")

    assert calls[-1] == ES_CONTINUOUS


def test_power_guard_api_failure_is_degraded_and_body_runs() -> None:
    calls: list[int] = []
    logs: list[str] = []

    def setter(flags: int) -> int:
        calls.append(flags)
        return 0 if len(calls) == 1 else 1

    body_ran = False
    with prevent_system_sleep(
        logs.append,
        platform="win32",
        set_thread_execution_state=setter,
    ):
        body_ran = True

    assert body_ran is True
    assert calls == [ES_CONTINUOUS | ES_SYSTEM_REQUIRED, ES_CONTINUOUS]
    assert any("measurement continues" in message for message in logs)


def test_power_guard_is_noop_on_unsupported_platform() -> None:
    calls: list[int] = []
    logs: list[str] = []

    with prevent_system_sleep(
        logs.append,
        platform="linux",
        set_thread_execution_state=lambda flags: calls.append(flags) or 1,
    ) as guard:
        assert guard.active is False

    assert calls == []
    assert logs == ["System sleep prevention unavailable on this platform; measurement continues."]


def test_power_guard_logging_failure_is_ignored() -> None:
    def setter(_flags: int) -> int:
        return 1

    def broken_logger(_message: str) -> None:
        raise RuntimeError("logger unavailable")

    with prevent_system_sleep(
        broken_logger,
        platform="win32",
        set_thread_execution_state=setter,
    ):
        pass


def test_power_guard_release_failure_is_ignored() -> None:
    calls: list[int] = []

    def setter(flags: int) -> int:
        calls.append(flags)
        return 1 if len(calls) == 1 else 0

    logs: list[str] = []
    with prevent_system_sleep(
        logs.append,
        platform="win32",
        set_thread_execution_state=setter,
    ):
        pass

    assert any("release failed" in message for message in logs)


def test_power_guard_release_exception_is_ignored() -> None:
    calls: list[int] = []

    def setter(flags: int) -> int:
        calls.append(flags)
        if len(calls) > 1:
            raise OSError("release unavailable")
        return 1

    logs: list[str] = []
    with prevent_system_sleep(
        logs.append,
        platform="win32",
        set_thread_execution_state=setter,
    ):
        pass

    assert any("release failed" in message for message in logs)


def test_power_guard_resolves_injected_ctypes_style_windows_api(monkeypatch) -> None:
    calls: list[int] = []

    class _Setter:
        def __call__(self, flags: int) -> int:
            calls.append(flags)
            return 1

    class _Kernel32:
        SetThreadExecutionState = _Setter()

    class _Windll:
        kernel32 = _Kernel32()

    monkeypatch.setattr(power_guard.ctypes, "windll", _Windll())
    with power_guard.prevent_system_sleep(platform="win32"):
        pass

    assert calls == [ES_CONTINUOUS | ES_SYSTEM_REQUIRED, ES_CONTINUOUS]


def test_sweep_worker_holds_power_guard_around_instrument_lifecycle() -> None:
    source = Path("src/keith_ivt/ui/sweep_controller.py").read_text(encoding="utf-8")
    guard_start = source.index("with prevent_system_sleep(")
    instrument_start = source.index("with self._make_instrument(config) as inst")
    assert guard_start < instrument_start
    assert 'logger=lambda message: self._queue.put(("log", message))' in source
