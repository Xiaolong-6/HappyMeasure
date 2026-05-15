from __future__ import annotations

import pytest

from keith_ivt.core.sweep_runner import SweepRunner
from keith_ivt.models import SweepConfig, SweepMode
from keith_ivt.services.serial_safety import OutputOffGuard


class RecordingMeter:
    def __init__(self, fail_on_read: bool = False) -> None:
        self.calls: list[str] = []
        self.fail_on_read = fail_on_read
        self.value = 0.0

    def connect(self): self.calls.append("connect")
    def close(self): self.calls.append("close")
    def identify(self): return "FAKE"
    def reset(self): self.calls.append("reset")
    def configure_for_sweep(self, config): self.calls.append(f"configure:{config.mode.value}")
    def set_source(self, source_cmd, value):
        self.calls.append(f"set:{source_cmd}:{value:.12g}")
        self.value = value
    def read_source_and_measure(self):
        self.calls.append("read")
        if self.fail_on_read:
            raise TimeoutError("simulated read timeout")
        return self.value, self.value / 1000.0
    def output_on(self): self.calls.append("on")
    def output_off(self): self.calls.append("off")


def test_sweep_runner_turns_output_off_after_read_exception() -> None:
    meter = RecordingMeter(fail_on_read=True)
    runner = SweepRunner(meter)
    cfg = SweepConfig(mode=SweepMode.VOLTAGE_SOURCE, start=0, stop=1, step=1, compliance=0.01, nplc=0.1)
    with pytest.raises(TimeoutError):
        runner.run(cfg)
    assert meter.calls[-1] == "off"


def test_sweep_runner_turns_output_off_when_stop_requested_before_first_point() -> None:
    meter = RecordingMeter()
    runner = SweepRunner(meter)
    cfg = SweepConfig(mode=SweepMode.VOLTAGE_SOURCE, start=0, stop=1, step=1, compliance=0.01, nplc=0.1)
    result = runner.run(cfg, should_stop=lambda: True)
    assert result.points == []
    assert "on" in meter.calls
    assert meter.calls[-1] == "off"
    assert not any(call.startswith("set:") for call in meter.calls)


def test_output_off_guard_reports_failure_without_raising() -> None:
    messages: list[str] = []
    guard = OutputOffGuard(logger=messages.append)
    ok = guard.turn_off(lambda: (_ for _ in ()).throw(RuntimeError("relay failed")), context="test")
    assert ok is False
    assert messages and "relay failed" in messages[0]
