from __future__ import annotations

import pytest

from keith_ivt.core.sweep_runner import SweepRunner
from keith_ivt.models import SweepConfig, SweepKind, SweepMode


class RecordingSourceMeter:
    def __init__(self, *, fail_on_read: bool = False, fail_output_off: bool = False) -> None:
        self.events: list[str] = []
        self.sources: list[float] = []
        self.fail_on_read = fail_on_read
        self.fail_output_off = fail_output_off
        self.output_enabled = False

    def connect(self) -> None:
        self.events.append("connect")

    def close(self) -> None:
        self.events.append("close")

    def identify(self) -> str:
        return "FAKE"

    def reset(self) -> None:
        self.events.append("reset")

    def configure_for_sweep(self, config: SweepConfig) -> None:
        self.events.append("configure")

    def set_source(self, source_cmd: str, value: float) -> None:
        self.sources.append(float(value))
        self.events.append(f"set:{value}")

    def read_source_and_measure(self) -> tuple[float, float]:
        self.events.append("read")
        if self.fail_on_read:
            raise RuntimeError("read failed")
        value = self.sources[-1] if self.sources else 0.0
        return value, value * 0.001

    def output_on(self) -> None:
        self.output_enabled = True
        self.events.append("output_on")

    def output_off(self) -> None:
        self.events.append("output_off")
        if self.fail_output_off:
            raise RuntimeError("output off failed")
        self.output_enabled = False


def _config(**kwargs) -> SweepConfig:
    params = dict(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0.0,
        stop=3.0,
        step=1.0,
        compliance=0.01,
        nplc=0.01,
        sweep_kind=SweepKind.STEP,
    )
    params.update(kwargs)
    return SweepConfig(**params)


def test_operator_stop_forces_output_off_even_when_config_would_leave_output_on():
    inst = RecordingSourceMeter()
    calls = {"count": 0}

    def should_stop() -> bool:
        calls["count"] += 1
        return calls["count"] >= 3

    result = SweepRunner(inst).run(
        _config(output_off_after_run=False),
        should_stop=should_stop,
    )

    assert len(result.points) < 4
    assert "output_on" in inst.events
    assert inst.events[-1] == "output_off"
    assert inst.output_enabled is False


def test_normal_completion_respects_output_off_after_run_false():
    inst = RecordingSourceMeter()

    result = SweepRunner(inst).run(_config(output_off_after_run=False))

    assert len(result.points) == 4
    assert "output_on" in inst.events
    assert "output_off" not in inst.events
    assert inst.output_enabled is True


def test_measurement_exception_still_attempts_output_off():
    inst = RecordingSourceMeter(fail_on_read=True)

    with pytest.raises(RuntimeError, match="read failed"):
        SweepRunner(inst).run(_config(output_off_after_run=True))

    assert "output_off" in inst.events
    assert inst.output_enabled is False


def test_output_off_failure_preserves_original_measurement_error_context():
    inst = RecordingSourceMeter(fail_on_read=True, fail_output_off=True)

    with pytest.raises(RuntimeError) as err:
        SweepRunner(inst).run(_config(output_off_after_run=True))

    message = str(err.value)
    assert "read failed" in message
    assert "output off failed" in message
    assert err.value.__cause__ is not None
