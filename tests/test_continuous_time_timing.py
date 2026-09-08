from __future__ import annotations

import pytest

import keith_ivt.core.sweep_runner as sweep_runner
from keith_ivt.core.current_range import CurrentRangeControl
from keith_ivt.core.sweep_runner import SweepRunner
from keith_ivt.models import SweepConfig, SweepKind, SweepMode


class _FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += max(0.0, float(seconds))


class _TimedMeter:
    def __init__(self, clock: _FakeClock, read_duration_s: float) -> None:
        self.clock = clock
        self.read_duration_s = read_duration_s
        self.read_starts: list[float] = []
        self.read_count = 0
        self.source_value = 0.0
        self.events: list[str] = []

    def reset(self) -> None:
        self.events.append("reset")

    def configure_for_sweep(self, config: SweepConfig) -> None:
        self.events.append("configure")

    def output_on(self) -> None:
        self.events.append("output_on")

    def output_off(self) -> None:
        self.events.append("output_off")

    def set_source(self, source_cmd: str, value: float) -> None:
        self.source_value = float(value)
        self.events.append(f"set:{value}")

    def read_source_and_measure(self) -> tuple[float, float]:
        self.read_starts.append(self.clock.now)
        self.read_count += 1
        self.clock.now += self.read_duration_s
        return self.source_value, self.source_value / 1000.0


class _FixedRangeMeter(_TimedMeter):
    def __init__(self, clock: _FakeClock) -> None:
        super().__init__(clock, 0.0)
        self.autorange = False
        self.range_A = 1e-3
        self.autorange_queries = 0
        self.range_queries = 0

    def get_current_autorange(self) -> bool:
        self.autorange_queries += 1
        return self.autorange

    def get_current_range(self) -> float:
        self.range_queries += 1
        return self.range_A

    def set_current_autorange(self, enabled: bool) -> None:
        self.autorange = bool(enabled)
        self.events.append(f"autorange:{enabled}")

    def set_current_range(self, range_A: float) -> None:
        self.range_A = float(range_A)
        self.events.append(f"range:{range_A}")


def _continuous_config(**changes) -> SweepConfig:
    values = dict(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0.0,
        stop=0.0,
        step=1.0,
        compliance=0.01,
        nplc=0.1,
        delay_s=0.0,
        sweep_kind=SweepKind.CONSTANT_TIME,
        constant_value=0.1,
        continuous_time=True,
        interval_s=0.1,
    )
    values.update(changes)
    return SweepConfig(**values)


def _run_for_reads(monkeypatch, meter: _TimedMeter, config: SweepConfig, reads: int):
    monkeypatch.setattr(sweep_runner.time, "monotonic", meter.clock.monotonic)
    monkeypatch.setattr(sweep_runner.time, "sleep", meter.clock.sleep)
    return SweepRunner(meter).run(config, should_stop=lambda: meter.read_count >= reads)


def test_continuous_interval_is_start_to_start_not_extra_sleep(monkeypatch) -> None:
    clock = _FakeClock()
    meter = _TimedMeter(clock, read_duration_s=0.03)

    result = _run_for_reads(monkeypatch, meter, _continuous_config(interval_s=0.1), reads=4)

    assert meter.read_starts == pytest.approx([0.0, 0.1, 0.2, 0.3])
    assert [point.elapsed_s for point in result.points] == pytest.approx([0.03, 0.13, 0.23, 0.33])


def test_continuous_overrun_runs_back_to_back_without_extra_interval_sleep(monkeypatch) -> None:
    clock = _FakeClock()
    meter = _TimedMeter(clock, read_duration_s=0.05)

    _run_for_reads(monkeypatch, meter, _continuous_config(interval_s=0.02), reads=4)

    assert meter.read_starts == pytest.approx([0.0, 0.05, 0.10, 0.15])


def test_continuous_pause_rebases_deadline_and_does_not_catch_up(monkeypatch) -> None:
    clock = _FakeClock()
    meter = _TimedMeter(clock, read_duration_s=0.03)
    pause_until = 0.0

    def should_pause() -> bool:
        return pause_until > 0.0 and clock.now < pause_until

    def on_point(point, index: int, total: int) -> None:
        nonlocal pause_until
        if index == 1:
            pause_until = 1.0

    monkeypatch.setattr(sweep_runner.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(sweep_runner.time, "sleep", clock.sleep)
    result = SweepRunner(meter).run(
        _continuous_config(interval_s=0.1),
        on_point=on_point,
        should_stop=lambda: meter.read_count >= 2,
        should_pause=should_pause,
    )

    assert len(result.points) == 2
    assert meter.read_starts[0] == pytest.approx(0.0)
    assert 1.0 <= meter.read_starts[1] < 1.1


def test_fixed_measure_range_skips_redundant_per_point_queries(monkeypatch) -> None:
    clock = _FakeClock()
    meter = _FixedRangeMeter(clock)
    config = _continuous_config(
        auto_measure_range=False,
        measure_range=1e-3,
        interval_s=0.1,
    )

    _run_for_reads(monkeypatch, meter, config, reads=3)

    assert meter.autorange_queries == 0
    assert meter.range_queries == 0


def test_fixed_range_action_still_refreshes_state_and_discards_reads(monkeypatch) -> None:
    clock = _FakeClock()
    meter = _FixedRangeMeter(clock)
    control = CurrentRangeControl()
    control.request_autorange(True)
    config = _continuous_config(
        auto_measure_range=False,
        measure_range=1e-3,
        discard_after_range_change=1,
    )

    result = SweepRunner(meter).run(
        config,
        current_range_control=control,
        should_stop=lambda: meter.read_count >= 2,
    )

    assert meter.autorange_queries >= 1
    assert meter.range_queries >= 1
    assert "autorange:True" in meter.events
    assert len(result.points) == 1
