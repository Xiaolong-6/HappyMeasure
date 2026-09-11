from __future__ import annotations

from dataclasses import replace

import pytest

from keith_ivt.acquisition import (
    FAST_NPLC,
    fast_profiles_available,
    resolve_time_acquisition,
)
from keith_ivt.core.current_range import CurrentRangeControl, CurrentRangeState
from keith_ivt.core.sweep_runner import SweepRunner
from keith_ivt.drivers.base import DriverCapabilities, supports_fast_acquisition_for_idn
from keith_ivt.instrument.serial_2400 import Keithley2400Serial
from keith_ivt.models import SweepConfig, SweepKind, SweepMode, validate_config


def _time_config(**changes) -> SweepConfig:
    base = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0.0,
        stop=0.0,
        step=1.0,
        compliance=1e-3,
        nplc=1.0,
        delay_s=0.25,
        sweep_kind=SweepKind.CONSTANT_TIME,
        constant_value=0.0,
        duration_s=0.025,
        interval_s=0.5,
        continuous_time=False,
        auto_source_range=False,
        auto_measure_range=False,
        source_range=20.0,
        measure_range=1e-3,
    )
    return replace(base, **changes)


def test_fast_profile_resolves_benchmark_backed_settings() -> None:
    config = _time_config(fast_acquisition=True, interval_s=0.0)
    validate_config(config)  # Interval is intentionally irrelevant in Fast.
    settings = resolve_time_acquisition(config)
    assert settings.nplc == pytest.approx(FAST_NPLC)
    assert settings.software_delay_s == 0.0
    assert settings.as_fast_as_possible is True
    assert settings.zero_refresh_before_run is True
    assert settings.autozero_during_run is False
    assert settings.digital_filter is False
    assert settings.concurrent_measurement is False
    assert settings.display_during_run is True
    assert settings.measurement_only_read is True
    assert settings.range_telemetry is False
    assert settings.source_write_each_sample is False
    assert settings.trigger_delay_s == 0.0


def test_standard_profile_preserves_historical_time_settings() -> None:
    config = _time_config(nplc=0.2, delay_s=0.03)
    settings = resolve_time_acquisition(config)
    assert settings.apply_instrument_overrides is False
    assert settings.nplc == pytest.approx(0.2)
    assert settings.software_delay_s == pytest.approx(0.03)
    assert settings.measurement_only_read is False
    assert settings.range_telemetry is True


def test_custom_profile_uses_explicit_advanced_settings() -> None:
    config = _time_config(
        custom_acquisition=True,
        nplc=0.5,
        delay_s=0.02,
        zero_refresh_before_run=False,
        autozero_during_run=True,
        digital_filter=True,
        digital_filter_count=3,
        concurrent_measurement=True,
        display_during_run=False,
        measurement_only_read=False,
        range_telemetry=True,
        source_write_each_sample=True,
        trigger_delay_s=0.004,
    )
    settings = resolve_time_acquisition(config)
    assert settings.apply_instrument_overrides is True
    assert settings.nplc == pytest.approx(0.5)
    assert settings.software_delay_s == pytest.approx(0.02)
    assert settings.zero_refresh_before_run is False
    assert settings.autozero_during_run is True
    assert settings.digital_filter is True
    assert settings.digital_filter_count == 3
    assert settings.concurrent_measurement is True
    assert settings.display_during_run is False
    assert settings.measurement_only_read is False
    assert settings.range_telemetry is True
    assert settings.source_write_each_sample is True
    assert settings.trigger_delay_s == pytest.approx(0.004)


def test_fast_and_custom_are_mutually_exclusive() -> None:
    with pytest.raises(ValueError, match="cannot both"):
        validate_config(_time_config(fast_acquisition=True, custom_acquisition=True))


def test_fast_profile_configures_measurement_only_without_per_point_range_queries() -> None:
    meter = Keithley2400Serial("COM_FAKE")
    commands: list[str] = []
    query_commands: list[str] = []
    meter.write = commands.append  # type: ignore[method-assign]

    def fake_query(command: str) -> str:
        query_commands.append(command)
        if command == ":READ?":
            return "-4.200000E-04"
        raise AssertionError(f"Unexpected query: {command}")

    meter.query = fake_query  # type: ignore[method-assign]
    config = _time_config(fast_acquisition=True)
    meter.configure_for_sweep(config)

    assert ":SENS:CURR:NPLC 0.1" in commands
    assert ":SENS:FUNC:CONC OFF" in commands
    concurrent_index = commands.index(":SENS:FUNC:CONC OFF")
    assert commands[concurrent_index + 1] == ":SENS:FUNC 'CURR'"
    assert ":SENS:AVER:STAT OFF" in commands
    assert ":DISP:ENAB ON" in commands
    assert ":SYST:AZER:STAT ONCE" in commands
    assert "*WAI" in commands
    assert ":SYST:AZER:STAT OFF" in commands
    autozero_sequence = [":SYST:AZER:STAT ONCE", "*WAI", ":SYST:AZER:STAT OFF"]
    assert any(
        commands[offset : offset + 3] == autozero_sequence for offset in range(len(commands) - 2)
    )
    assert ":TRIG:DEL 0" in commands
    assert ":FORM:ELEM CURR" in commands
    assert not any("BAUD" in command.upper() for command in commands)

    meter.set_source("VOLT", 0.25)
    source, measured = meter.read_source_and_measure()
    assert source == pytest.approx(0.25)
    assert measured == pytest.approx(-4.2e-4)
    assert query_commands == [":READ?"]

    # Range-state calls used by SweepRunner must stay cache-only in Fast.
    assert meter.get_current_autorange() is False
    assert meter.get_current_range() == pytest.approx(1e-3)
    assert query_commands == [":READ?"]


def test_custom_concurrent_setup_restores_the_intended_voltage_measurement_function() -> None:
    meter = Keithley2400Serial("COM_FAKE")
    commands: list[str] = []
    meter.write = commands.append  # type: ignore[method-assign]
    meter.query = lambda command: "0.25,-4.2E-4"  # type: ignore[method-assign]
    config = _time_config(
        mode=SweepMode.CURRENT_SOURCE,
        fast_acquisition=False,
        custom_acquisition=True,
        concurrent_measurement=False,
    )
    meter.configure_for_sweep(config)
    concurrent_index = commands.index(":SENS:FUNC:CONC OFF")
    assert commands[concurrent_index + 1] == ":SENS:FUNC 'VOLT'"


def test_keithley_overflow_sentinel_is_returned_as_nan_not_a_scientific_value() -> None:
    meter = Keithley2400Serial("COM_FAKE")
    meter._measurement_only_read = True
    meter.query = lambda command: "9.91E+37"  # type: ignore[method-assign]
    _source, measured = meter.read_source_and_measure()
    assert measured != measured
    assert meter._normalise_measurement(1e30) == pytest.approx(1e30)


def test_standard_profile_keeps_two_field_readback() -> None:
    meter = Keithley2400Serial("COM_FAKE")
    commands: list[str] = []
    meter.write = commands.append  # type: ignore[method-assign]
    meter.query = lambda command: "0.25,-4.2E-4"  # type: ignore[method-assign]
    meter.configure_for_sweep(_time_config())
    assert ":FORM:ELEM VOLT,CURR" in commands
    assert ":SYST:AZER:STAT ONCE" not in commands
    source, measured = meter.read_source_and_measure()
    assert source == pytest.approx(0.25)
    assert measured == pytest.approx(-4.2e-4)


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def perf_counter_ns(self) -> int:
        return round(self.now * 1e9)


class _FastMeter:
    def __init__(self, clock: _Clock) -> None:
        self.clock = clock
        self.source_sets: list[float] = []
        self.reads = 0
        self.capabilities = DriverCapabilities(
            name="test", vendor="test", model_family="test", supports_fast_acquisition=True
        )

    def reset(self) -> None:
        pass

    def configure_for_sweep(self, config: SweepConfig) -> None:
        pass

    def output_on(self) -> None:
        pass

    def output_off(self) -> None:
        pass

    def set_source(self, source_cmd: str, value: float) -> None:
        self.source_sets.append(float(value))

    def read_source_and_measure(self) -> tuple[float, float]:
        self.clock.now += 0.01
        self.reads += 1
        return 0.0, float(self.reads)

    def get_current_autorange(self) -> bool:
        return False

    def get_current_range(self) -> float:
        return 1e-3


def test_custom_source_write_each_sample_writes_exactly_once_per_sample() -> None:
    meter = Keithley2400Serial("COM_FAKE")
    meter.capabilities = DriverCapabilities(  # type: ignore[attr-defined]
        name="test", vendor="test", model_family="test", supports_fast_acquisition=True
    )
    writes: list[str] = []
    reads: list[str] = []
    meter.write = writes.append  # type: ignore[method-assign]

    def fake_query(command: str) -> str:
        reads.append(command)
        if command == ":READ?":
            return "0.25,-4.2E-4"
        raise AssertionError(f"Unexpected query: {command}")

    meter.query = fake_query  # type: ignore[method-assign]
    config = _time_config(
        custom_acquisition=True,
        nplc=0.1,
        delay_s=0.0,
        duration_s=0.35,
        interval_s=0.1,
        zero_refresh_before_run=False,
        measurement_only_read=False,
        range_telemetry=True,
        source_write_each_sample=True,
    )
    result = SweepRunner(meter).run(config)

    assert len(result.points) == 4
    assert reads == [":READ?"] * 4
    source_writes = [command for command in writes if command.startswith(":SOUR:VOLT ")]
    # One pre-run source set plus exactly one write per acquired sample: the
    # runner owns scheduling, so the driver read path must not add its own.
    assert len(source_writes) == len(result.points) + 1


def test_fast_support_identity_matrix() -> None:
    assert supports_fast_acquisition_for_idn("KEITHLEY INSTRUMENTS INC.,MODEL 2401,4612952,B02")
    # Only MODEL 2401 is validated for Fast in this release; other 2400-series
    # remain Standard-only until explicitly re-validated.
    assert not supports_fast_acquisition_for_idn("Keithley Instruments Inc., Model 2400")
    assert not supports_fast_acquisition_for_idn("KEITHLEY INSTRUMENTS INC.,MODEL 2410,123")
    assert supports_fast_acquisition_for_idn("SIMULATED Keithley 2400")
    assert not supports_fast_acquisition_for_idn("KEITHLEY INSTRUMENTS INC.,MODEL 2450")
    assert not supports_fast_acquisition_for_idn("Generic IV instrument")
    assert not supports_fast_acquisition_for_idn("")


def test_fast_profile_availability_matrix() -> None:
    assert fast_profiles_available(
        connected=False, simulator=False, supports_fast_acquisition=False
    )
    assert fast_profiles_available(connected=False, simulator=False, supports_fast_acquisition=True)
    assert fast_profiles_available(connected=True, simulator=True, supports_fast_acquisition=False)
    assert fast_profiles_available(connected=True, simulator=False, supports_fast_acquisition=True)
    assert not fast_profiles_available(
        connected=True, simulator=False, supports_fast_acquisition=False
    )


class _CapabilityMeter(_FastMeter):
    def __init__(self, clock: _Clock, supports_fast: bool) -> None:
        super().__init__(clock)
        self.capabilities = DriverCapabilities(
            name="test meter",
            vendor="test",
            model_family="test",
            supports_fast_acquisition=supports_fast,
        )


def test_fast_runtime_guard_rejects_unvalidated_instrument() -> None:
    clock = _Clock()
    meter = _CapabilityMeter(clock, supports_fast=False)
    config = _time_config(fast_acquisition=True, duration_s=0.025, interval_s=99.0)
    with pytest.raises(ValueError, match="not validated"):
        SweepRunner(meter).run(config)


def test_fast_runtime_guard_rejects_unvalidated_custom_overrides() -> None:
    clock = _Clock()
    meter = _CapabilityMeter(clock, supports_fast=False)
    config = _time_config(custom_acquisition=True, source_write_each_sample=True)
    with pytest.raises(ValueError, match="not validated"):
        SweepRunner(meter).run(config)


def test_fast_runtime_guard_allows_standard_on_unvalidated_instrument() -> None:
    clock = _Clock()
    meter = _CapabilityMeter(clock, supports_fast=False)
    control = CurrentRangeControl(
        CurrentRangeState(autorange=False, actual_range_A=1e-3, fixed_range_A=1e-3)
    )
    result = SweepRunner(meter).run(
        _time_config(nplc=0.1, delay_s=0.0, duration_s=0.06, interval_s=0.02),
        current_range_control=control,
    )
    assert len(result.points) == 4


def test_fast_runtime_guard_allows_validated_and_legacy_instruments(monkeypatch) -> None:
    import keith_ivt.core.sweep_runner as runner_module

    for meter in (_CapabilityMeter(_Clock(), True), _FastMeter(_Clock())):
        clock = meter.clock
        monkeypatch.setattr(runner_module, "_acquisition_clock_ns", clock.perf_counter_ns)
        config = _time_config(fast_acquisition=True, duration_s=0.025, interval_s=99.0)
        control = CurrentRangeControl(
            CurrentRangeState(autorange=False, actual_range_A=1e-3, fixed_range_A=1e-3)
        )
        result = SweepRunner(meter).run(config, current_range_control=control)
        assert len(result.points) == 3


def test_fast_finite_time_sweep_is_duration_based_and_has_no_interval_wait(monkeypatch) -> None:
    import keith_ivt.core.sweep_runner as runner_module

    clock = _Clock()
    meter = _FastMeter(clock)
    monkeypatch.setattr(runner_module, "_acquisition_clock_ns", clock.perf_counter_ns)
    config = _time_config(fast_acquisition=True, duration_s=0.025, interval_s=99.0)
    control = CurrentRangeControl(
        CurrentRangeState(autorange=False, actual_range_A=1e-3, fixed_range_A=1e-3)
    )
    result = SweepRunner(meter).run(config, current_range_control=control)
    assert [point.elapsed_s for point in result.points] == pytest.approx([0.01, 0.02, 0.03])
    assert meter.source_sets == [0.0]
    assert meter.reads == 3
