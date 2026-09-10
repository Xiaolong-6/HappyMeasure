from __future__ import annotations

import math

import pytest

import keith_ivt.core.sweep_runner as sweep_runner
import keith_ivt.services.measurement_service as measurement_service
from keith_ivt.core.current_range import CurrentRangeControl
from keith_ivt.core.sweep_runner import SweepRunner
from keith_ivt.drivers.base import DriverReadback, MeasureMode, SourceMode
from keith_ivt.services.measurement_service import MeasurementService
from keith_ivt.models import SweepConfig, SweepKind, SweepMode
from keith_ivt.sweeps.plan import SweepExecutionKind, make_plan


class _FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def perf_counter_ns(self) -> int:
        return round(self.now * 1e9)

    def sleep(self, seconds: float) -> None:
        self.now += max(0.0, float(seconds))


class _TimedMeter:
    def __init__(
        self,
        clock: _FakeClock,
        read_duration_s: float,
        *,
        reset_duration_s: float = 0.0,
        configure_duration_s: float = 0.0,
        output_on_duration_s: float = 0.0,
        source_duration_s: float = 0.0,
    ) -> None:
        self.clock = clock
        self.read_duration_s = read_duration_s
        self.reset_duration_s = reset_duration_s
        self.configure_duration_s = configure_duration_s
        self.output_on_duration_s = output_on_duration_s
        self.source_duration_s = source_duration_s
        self.read_starts: list[float] = []
        self.read_count = 0
        self.source_value = 0.0
        self.events: list[str] = []

    def reset(self) -> None:
        self.events.append("reset")
        self.clock.now += self.reset_duration_s

    def configure_for_sweep(self, config: SweepConfig) -> None:
        self.events.append("configure")
        self.clock.now += self.configure_duration_s

    def output_on(self) -> None:
        self.events.append("output_on")
        self.clock.now += self.output_on_duration_s

    def output_off(self) -> None:
        self.events.append("output_off")

    def set_source(self, source_cmd: str, value: float) -> None:
        self.source_value = float(value)
        self.events.append(f"set:{value}")
        self.clock.now += self.source_duration_s

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
    monkeypatch.setattr(sweep_runner, "_acquisition_clock_ns", meter.clock.perf_counter_ns)
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


class _VariableTimedMeter(_TimedMeter):
    def __init__(self, clock: _FakeClock, read_durations_s: list[float]) -> None:
        super().__init__(clock, read_duration_s=0.0)
        self.read_durations_s = read_durations_s

    def read_source_and_measure(self) -> tuple[float, float]:
        self.read_starts.append(self.clock.now)
        self.read_count += 1
        duration = self.read_durations_s[min(self.read_count - 1, len(self.read_durations_s) - 1)]
        self.clock.now += duration
        return self.source_value, self.source_value / 1000.0


def test_continuous_transient_overrun_rebases_without_catch_up_burst(monkeypatch) -> None:
    clock = _FakeClock()
    meter = _VariableTimedMeter(clock, [0.03, 0.35, 0.03, 0.03])

    _run_for_reads(monkeypatch, meter, _continuous_config(interval_s=0.1), reads=4)

    assert meter.read_starts == pytest.approx([0.0, 0.1, 0.45, 0.55])


def test_finite_constant_time_uses_start_to_start_deadlines(monkeypatch) -> None:
    clock = _FakeClock()
    meter = _TimedMeter(clock, read_duration_s=0.03)
    config = _continuous_config(
        continuous_time=False,
        duration_s=0.31,
        interval_s=0.1,
    )

    result = _run_for_reads(monkeypatch, meter, config, reads=4)

    assert meter.read_starts == pytest.approx([0.0, 0.1, 0.2, 0.3])
    assert [point.elapsed_s for point in result.points] == pytest.approx([0.03, 0.13, 0.23, 0.33])


def test_acquisition_elapsed_zero_starts_after_hardware_preparation(monkeypatch) -> None:
    clock = _FakeClock()
    meter = _TimedMeter(
        clock,
        read_duration_s=0.03,
        reset_duration_s=1.0,
        configure_duration_s=0.5,
        output_on_duration_s=0.2,
        source_duration_s=0.1,
    )

    result = _run_for_reads(monkeypatch, meter, _continuous_config(interval_s=0.1), reads=1)

    assert result.points[0].elapsed_s == pytest.approx(0.03)
    assert meter.read_starts[0] == pytest.approx(1.8)


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

    monkeypatch.setattr(sweep_runner, "_acquisition_clock_ns", clock.perf_counter_ns)
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


def test_constant_time_skips_recognised_overflow_and_keeps_next_valid_read(monkeypatch) -> None:
    clock = _FakeClock()
    meter = _TimedMeter(clock, read_duration_s=0.01)
    overflow_pending = False

    def read_with_one_overflow() -> tuple[float, float]:
        nonlocal overflow_pending
        meter.read_starts.append(clock.now)
        meter.read_count += 1
        clock.now += meter.read_duration_s
        overflow_pending = meter.read_count == 1
        return meter.source_value, float("nan") if overflow_pending else meter.read_count / 1000.0

    def consume_overflow() -> bool:
        nonlocal overflow_pending
        marked = overflow_pending
        overflow_pending = False
        return marked

    meter.read_source_and_measure = read_with_one_overflow  # type: ignore[method-assign]
    meter.consume_measurement_overflow = consume_overflow  # type: ignore[attr-defined]
    result = _run_for_reads(monkeypatch, meter, _continuous_config(), reads=3)

    assert meter.read_count == 3
    assert [point.measured_value for point in result.points] == pytest.approx([0.002, 0.003])
    assert all(point.measured_value != 9.91e37 for point in result.points)
    assert result.warnings == ["Skipped 1 Keithley overflow measurement(s)."]


def _finite_config(**changes) -> SweepConfig:
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
        continuous_time=False,
        duration_s=0.45,
        interval_s=0.1,
    )
    values.update(changes)
    return SweepConfig(**values)


def _overflow_meter(clock, overflow_reads, read_duration_s=0.01):
    meter = _TimedMeter(clock, read_duration_s=read_duration_s)
    overflow_pending = False

    def read_with_overflow() -> tuple[float, float]:
        nonlocal overflow_pending
        meter.read_starts.append(clock.now)
        meter.read_count += 1
        clock.now += meter.read_duration_s
        overflow_pending = meter.read_count in overflow_reads
        if overflow_pending:
            return meter.source_value, float("nan")
        return meter.source_value, meter.read_count / 1000.0

    def consume_overflow() -> bool:
        nonlocal overflow_pending
        marked = overflow_pending
        overflow_pending = False
        return marked

    meter.read_source_and_measure = read_with_overflow  # type: ignore[method-assign]
    meter.consume_measurement_overflow = consume_overflow  # type: ignore[attr-defined]
    return meter


def _run_finite(monkeypatch, meter: _TimedMeter, config: SweepConfig, backstop: int = 50):
    monkeypatch.setattr(sweep_runner, "_acquisition_clock_ns", meter.clock.perf_counter_ns)
    monkeypatch.setattr(sweep_runner.time, "sleep", meter.clock.sleep)
    return SweepRunner(meter).run(config, should_stop=lambda: meter.read_count >= backstop)


def test_finite_standard_time_overflow_does_not_extend_scheduled_slots(
    monkeypatch,
) -> None:
    clock = _FakeClock()
    meter = _overflow_meter(clock, {2})
    result = _run_finite(monkeypatch, meter, _finite_config())

    assert meter.read_count == 5
    assert len(result.points) == 4
    assert [point.measured_value for point in result.points] == pytest.approx(
        [0.001, 0.003, 0.004, 0.005]
    )
    assert all(math.isfinite(point.elapsed_s) for point in result.points)
    assert result.warnings == ["Skipped 1 Keithley overflow measurement(s)."]


def test_finite_standard_time_overflow_on_last_slot_still_ends_on_schedule(
    monkeypatch,
) -> None:
    clock = _FakeClock()
    meter = _overflow_meter(clock, {2, 5})
    result = _run_finite(monkeypatch, meter, _finite_config())

    assert meter.read_count == 5
    assert len(result.points) == 3
    assert [point.measured_value for point in result.points] == pytest.approx(
        [0.001, 0.003, 0.004]
    )
    assert result.warnings == ["Skipped 2 Keithley overflow measurement(s)."]


def test_fast_finite_time_with_overflow_stops_by_elapsed_duration(monkeypatch) -> None:
    clock = _FakeClock()
    meter = _overflow_meter(clock, {1, 2})
    config = _finite_config(fast_acquisition=True, duration_s=0.05)
    result = _run_finite(monkeypatch, meter, config)

    assert meter.read_count < 20
    assert len(result.points) == meter.read_count - 2
    assert result.points[-1].elapsed_s >= 0.05
    assert result.warnings == ["Skipped 2 Keithley overflow measurement(s)."]


def test_step_sweep_overflow_is_a_hard_error_not_a_silent_drop(monkeypatch) -> None:
    clock = _FakeClock()
    meter = _overflow_meter(clock, {1})
    config = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0.0,
        stop=1.0,
        step=0.5,
        compliance=0.01,
        nplc=0.1,
        delay_s=0.0,
        sweep_kind=SweepKind.STEP,
    )
    monkeypatch.setattr(sweep_runner, "_acquisition_clock_ns", clock.perf_counter_ns)
    monkeypatch.setattr(sweep_runner.time, "sleep", clock.sleep)
    with pytest.raises(RuntimeError, match="Non-finite measurement readback"):
        SweepRunner(meter).run(config)


def test_unmarked_nonfinite_readback_remains_an_acquisition_error(monkeypatch) -> None:
    clock = _FakeClock()
    meter = _TimedMeter(clock, read_duration_s=0.01)
    meter.read_source_and_measure = lambda: (0.1, float("nan"))  # type: ignore[method-assign]

    monkeypatch.setattr(sweep_runner, "_acquisition_clock_ns", clock.perf_counter_ns)
    monkeypatch.setattr(sweep_runner.time, "sleep", clock.sleep)
    with pytest.raises(RuntimeError, match="Non-finite measurement readback"):
        SweepRunner(meter).run(_continuous_config())


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


def test_runtime_fixed_range_state_skips_later_per_point_queries(monkeypatch) -> None:
    clock = _FakeClock()
    meter = _FixedRangeMeter(clock)
    control = CurrentRangeControl()
    control.request_fixed_range(1e-3)
    config = _continuous_config(interval_s=0.1)

    _run_for_reads_with_control(monkeypatch, meter, config, reads=3, control=control)

    # One refresh at startup and one after the explicit action; no per-point
    # refreshes should follow once the runtime state is fixed.
    assert meter.autorange_queries == 2
    assert meter.range_queries == 2


class _TimedNativeDriver:
    def __init__(self, clock: _FakeClock, read_durations_s: list[float]) -> None:
        self.clock = clock
        self.read_durations_s = read_durations_s
        self.read_starts: list[float] = []
        self.read_count = 0
        self.source_value = 0.0

    def reset(self) -> None:
        pass

    def configure_source_measure(self, **_kwargs) -> None:
        pass

    def output_on(self) -> None:
        pass

    def output_off(self) -> None:
        pass

    def set_source(self, _source_mode: SourceMode, value: float) -> None:
        self.source_value = float(value)

    def read(self) -> DriverReadback:
        self.read_starts.append(self.clock.now)
        self.read_count += 1
        duration = self.read_durations_s[min(self.read_count - 1, len(self.read_durations_s) - 1)]
        self.clock.now += duration
        return DriverReadback(self.source_value, self.source_value / 1000.0)


def test_native_constant_time_uses_deadline_rebase(monkeypatch) -> None:
    clock = _FakeClock()
    driver = _TimedNativeDriver(clock, [0.03, 0.35, 0.03, 0.03])
    monkeypatch.setattr(measurement_service.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(measurement_service.time, "sleep", clock.sleep)
    plan = make_plan(
        source_mode=SourceMode.VOLTAGE,
        measure_mode=MeasureMode.CURRENT,
        values=[0.1, 0.1, 0.1, 0.1],
        compliance=0.01,
        nplc=0.1,
        execution_kind=SweepExecutionKind.CONSTANT_TIME,
        interval_s=0.1,
    )

    MeasurementService(driver).run_plan(plan)

    assert driver.read_starts == pytest.approx([0.0, 0.1, 0.45, 0.55])


def _run_for_reads_with_control(
    monkeypatch,
    meter: _TimedMeter,
    config: SweepConfig,
    *,
    reads: int,
    control: CurrentRangeControl,
):
    monkeypatch.setattr(sweep_runner, "_acquisition_clock_ns", meter.clock.perf_counter_ns)
    monkeypatch.setattr(sweep_runner.time, "sleep", meter.clock.sleep)
    return SweepRunner(meter).run(
        config,
        should_stop=lambda: meter.read_count >= reads,
        current_range_control=control,
    )
