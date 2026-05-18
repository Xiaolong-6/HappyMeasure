from __future__ import annotations

import pytest

from keith_ivt.core.sweep_runner import SweepRunner
from keith_ivt.drivers.command_plan import build_keithley2400_sweep_command_plan
from keith_ivt.models import SweepConfig, SweepKind, SweepMode, estimate_point_seconds, minimum_interval_seconds, serial_round_trip_seconds
from keith_ivt.sweeps.plan import SweepExecutionKind, make_plan, plan_from_config


class DelayRecordingMeter:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.value = 0.0

    def reset(self):
        self.calls.append("reset")

    def configure_for_sweep(self, config):
        self.calls.append(f"configure:{config.delay_s}")

    def output_on(self):
        self.calls.append("on")

    def output_off(self):
        self.calls.append("off")

    def set_source(self, source_cmd, value):
        self.calls.append(f"set:{value}")
        self.value = value

    def read_source_and_measure(self):
        self.calls.append("read")
        return self.value, self.value / 1000.0


def test_delay_is_in_command_plan_and_estimate() -> None:
    cfg = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0,
        stop=1,
        step=1,
        compliance=0.01,
        nplc=1.0,
        delay_s=0.25,
    )
    commands = build_keithley2400_sweep_command_plan(cfg, include_output=False)
    assert ":SENS:CURR:NPLC 1" in commands
    assert ":SOUR:DEL 0.25" in commands
    expected = 0.02 + 0.25 + serial_round_trip_seconds(9600)
    assert minimum_interval_seconds(1.0, delay_s=0.25, baud_rate=9600) == pytest.approx(expected)
    assert estimate_point_seconds(1.0, delay_s=0.25, baud_rate=9600) == pytest.approx(expected)


def test_delay_is_preserved_in_sweep_plan() -> None:
    cfg = SweepConfig(
        mode=SweepMode.CURRENT_SOURCE,
        start=0,
        stop=2,
        step=1,
        compliance=5.0,
        nplc=0.5,
        delay_s=0.1,
    )
    plan = plan_from_config(cfg)
    assert plan.delay_s == pytest.approx(0.1)
    assert plan.estimated_seconds == pytest.approx(3 * minimum_interval_seconds(0.5, delay_s=0.1, baud_rate=9600))

    direct = make_plan(
        source_mode=plan.source_mode,
        measure_mode=plan.measure_mode,
        values=[0, 1],
        compliance=1.0,
        nplc=0.5,
        delay_s=0.2,
        baud_rate=19200,
        execution_kind=SweepExecutionKind.STEP,
    )
    assert direct.delay_s == pytest.approx(0.2)


def test_sweep_runner_applies_delay_between_set_and_read(monkeypatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr("keith_ivt.core.sweep_runner._interruptible_sleep", lambda seconds, _stop=None: sleeps.append(seconds))
    meter = DelayRecordingMeter()
    cfg = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0,
        stop=1,
        step=1,
        compliance=0.01,
        nplc=0.1,
        delay_s=0.07,
    )
    result = SweepRunner(meter).run(cfg)
    assert len(result.points) == 2
    assert sleeps[:2] == [pytest.approx(0.07), pytest.approx(0.07)]
    assert meter.calls.index("set:0.0") < meter.calls.index("read")


def test_higher_baud_rate_reduces_estimated_overhead() -> None:
    slow = minimum_interval_seconds(1.0, delay_s=0.0, baud_rate=9600)
    fast = minimum_interval_seconds(1.0, delay_s=0.0, baud_rate=57600)
    assert fast < slow

