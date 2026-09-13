from __future__ import annotations

import threading

import pytest

from keith_ivt.instrument.serial_2400 import Keithley2400Serial
from keith_ivt.services.hardware_preflight import run_keithley_preflight
from keith_ivt.services.serial_safety import SerialRetryPolicy
from keith_ivt.ui.shutdown_safety import ShutdownSafetyMixin


def test_output_off_write_failure_propagates() -> None:
    meter = Keithley2400Serial("COM_FAKE")

    def fail_off(_command: str) -> None:
        raise RuntimeError("off failed")

    meter.write = fail_off  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="off failed"):
        meter.output_off()


def test_read_query_is_not_retried() -> None:
    meter = Keithley2400Serial(
        "COM_FAKE", retry_policy=SerialRetryPolicy(max_attempts=3, base_delay_s=0.0)
    )
    calls = 0

    def fail(_command: str) -> str:
        nonlocal calls
        calls += 1
        raise TimeoutError("read timeout")

    meter._query_once = fail  # type: ignore[method-assign]
    with pytest.raises(TimeoutError, match="read timeout"):
        meter.query(":READ?")
    assert calls == 1


def test_preflight_requires_reported_output_off(monkeypatch) -> None:
    class FakeInstrument:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def connect(self) -> None:
            pass

        def output_off(self) -> None:
            pass

        def query(self, command: str) -> str:
            assert command == ":OUTP?"
            return "1"

        def identify(self) -> str:
            return "KEITHLEY INSTRUMENTS INC.,MODEL 2401,123,B02"

        def close(self) -> None:
            pass

    monkeypatch.setattr("keith_ivt.services.hardware_preflight.Keithley2400Serial", FakeInstrument)
    with pytest.raises(RuntimeError, match="reported output state"):
        run_keithley_preflight("COM9")


def test_preflight_connect_failure_keeps_original_error(monkeypatch) -> None:
    class FakeInstrument:
        def __init__(self, *args, **kwargs) -> None:
            self.closed = False

        def connect(self) -> None:
            raise RuntimeError("port unavailable")

        def output_off(self) -> None:
            raise AssertionError("output_off must not run when connect failed")

        def close(self) -> None:
            self.closed = True

    monkeypatch.setattr("keith_ivt.services.hardware_preflight.Keithley2400Serial", FakeInstrument)
    with pytest.raises(RuntimeError, match="port unavailable"):
        run_keithley_preflight("COM9")


class _Root:
    def __init__(self) -> None:
        self.destroyed = False
        self.handler = None

    def protocol(self, _name: str, handler) -> None:
        self.handler = handler

    def destroy(self) -> None:
        self.destroyed = True


class _State:
    def __init__(self) -> None:
        self.stop_requested = False

    def request_stop(self) -> None:
        self.stop_requested = True


class _Base:
    def _bind_variables(self) -> None:
        self.bound = True

    def _handle_complete(self, _result) -> None:
        self.completed = True

    def _handle_error(self, _exc: Exception) -> None:
        self.errored = True


class _Harness(ShutdownSafetyMixin, _Base):
    def __init__(self) -> None:
        self.root = _Root()
        self.app_state = _State()
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._run_state = "running"
        self.logs: list[str] = []
        self.state_changes: list[str] = []

    def _set_run_state(self, state: str) -> None:
        self._run_state = state
        self.state_changes.append(state)

    def _update_run_button_states(self) -> None:
        pass

    def _reset_live_measurement_status(self) -> None:
        pass

    def _close_auto_front_panel_popup(self) -> None:
        pass

    def log_event(self, message: str) -> None:
        self.logs.append(message)


def test_shutdown_mixin_installs_main_window_handler() -> None:
    app = _Harness()
    app._bind_variables()
    assert app.bound is True
    assert app.root.handler == app._request_safe_close


def test_abort_is_cooperative_and_sets_stop_event() -> None:
    app = _Harness()
    app.abort_sweep()
    assert app._stop_event.is_set()
    assert app._run_state == "stopping"
    assert app.app_state.stop_requested is True
    assert "must return" in app.logs[-1]
