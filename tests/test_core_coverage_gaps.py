from __future__ import annotations

import pytest

from keith_ivt.data.dataset_store import DatasetStore
from keith_ivt.drivers.command_plan import build_keithley2400_sweep_command_plan
from keith_ivt.models import (
    SweepConfig,
    SweepKind,
    SweepMode,
    SweepResult,
    SweepPoint,
    estimate_point_seconds,
    make_constant_time_values,
    make_source_values,
    minimum_interval_seconds,
    validate_config,
)
from keith_ivt.services.serial_safety import SerialRetryPolicy
from keith_ivt.utils.formatting import format_si, format_voltage, format_current, format_resistance
from keith_ivt.utils.thread_safe import ThreadSafeXYBuffer


def test_source_value_generation_and_validation_errors() -> None:
    assert make_source_values(0, 1, 0.5) == [0.0, 0.5, 1.0]
    assert make_source_values(1, 0, -0.5) == [1.0, 0.5, 0.0]
    with pytest.raises(ValueError):
        make_source_values(0, 1, 0)
    with pytest.raises(ValueError):
        make_source_values(0, 1, -1)
    with pytest.raises(ValueError):
        make_source_values(1, 0, 1)


def test_timing_helpers_and_constant_time_validation() -> None:
    assert minimum_interval_seconds(1.0, line_frequency_hz=50, overhead_s=0.03) == pytest.approx(0.05)
    assert estimate_point_seconds(1.0, mode=SweepKind.CONSTANT_TIME.value, interval_s=0.2) == pytest.approx(0.2)
    assert make_constant_time_values(2.0, duration_s=1.0, interval_s=0.5) == [2.0, 2.0, 2.0]
    with pytest.raises(ValueError):
        make_constant_time_values(0.0, duration_s=0.0, interval_s=1.0)
    with pytest.raises(ValueError):
        make_constant_time_values(0.0, duration_s=1.0, interval_s=0.0)


def test_config_properties_and_validation_edges() -> None:
    vcfg = SweepConfig(mode=SweepMode.VOLTAGE_SOURCE, start=0, stop=1, step=1, compliance=0.01, nplc=0.1)
    assert vcfg.source_scpi == "VOLT"
    assert vcfg.measure_scpi == "CURR"
    assert vcfg.source_label == "Voltage (V)"
    assert vcfg.measure_label == "Current (A)"
    assert vcfg.csv_headers == ("Voltage_V", "Current_A")
    validate_config(vcfg)

    icfg = SweepConfig(mode=SweepMode.CURRENT_SOURCE, start=0, stop=1e-3, step=1e-3, compliance=5, nplc=0.1)
    assert icfg.source_scpi == "CURR"
    assert icfg.measure_scpi == "VOLT"
    assert icfg.csv_headers == ("Current_A", "Voltage_V")

    with pytest.raises(ValueError):
        validate_config(SweepConfig(mode=SweepMode.VOLTAGE_SOURCE, start=0, stop=1, step=1, compliance=0, nplc=0.1))
    with pytest.raises(ValueError):
        validate_config(SweepConfig(mode=SweepMode.VOLTAGE_SOURCE, start=0, stop=1, step=1, compliance=1, nplc=0.001))
    with pytest.raises(ValueError):
        validate_config(SweepConfig(mode=SweepMode.VOLTAGE_SOURCE, start=0, stop=1, step=1, compliance=1, nplc=0.1, auto_source_range=False, source_range=0))
    with pytest.raises(ValueError):
        validate_config(SweepConfig(mode=SweepMode.VOLTAGE_SOURCE, start=0, stop=1, step=1, compliance=1, nplc=0.1, auto_measure_range=False, measure_range=0))


def test_command_plan_covers_fixed_ranges_without_output() -> None:
    cfg = SweepConfig(
        mode=SweepMode.CURRENT_SOURCE,
        start=0,
        stop=1e-3,
        step=1e-3,
        compliance=5.0,
        nplc=0.1,
        auto_source_range=False,
        source_range=0.001,
        auto_measure_range=False,
        measure_range=10.0,
    )
    commands = build_keithley2400_sweep_command_plan(cfg, include_output=False)
    assert ":SOUR:CURR:RANG:AUTO OFF" in commands
    assert ":SOUR:CURR:RANG 0.001" in commands
    assert ":SENS:VOLT:RANG:AUTO OFF" in commands
    assert ":SENS:VOLT:RANG 10" in commands
    assert ":OUTP ON" not in commands


def test_dataset_store_unique_names_mutation_and_missing_ids() -> None:
    store = DatasetStore()
    cfg = SweepConfig(mode=SweepMode.VOLTAGE_SOURCE, start=0, stop=0, step=1, compliance=1, nplc=0.1, device_name="D")
    result = SweepResult(cfg, [SweepPoint(0.0, 0.0), SweepPoint(1.0, 1e-3)])
    t1 = store.add_result(result, "D")
    t2 = store.add_result(result, "D")
    assert t1.name == "D"
    assert t2.name == "D_2"
    assert t1.point_count == 2
    assert "visible" in t1.label
    store.toggle_visibility(t1.trace_id)
    assert "hidden" in t1.label
    store.set_color(t1.trace_id, "#abcdef")
    assert t1.color == "#abcdef"
    store.rename(t2.trace_id, "D")
    assert t2.name == "D_2"
    store.rename(999999, "missing")
    store.toggle_visibility(999999)
    store.set_color(999999, "#000000")
    store.remove(t1.trace_id)
    assert store.get(t1.trace_id) is None
    store.clear()
    assert store.all() == []


def test_retry_policy_success_retry_and_validation(monkeypatch) -> None:
    with pytest.raises(ValueError):
        SerialRetryPolicy(max_attempts=0)
    with pytest.raises(ValueError):
        SerialRetryPolicy(base_delay_s=-1)
    with pytest.raises(ValueError):
        SerialRetryPolicy(backoff_factor=0.5)

    sleeps: list[float] = []
    monkeypatch.setattr("keith_ivt.services.serial_safety.time.sleep", sleeps.append)
    messages: list[str] = []
    attempts = {"n": 0}

    def flaky() -> str:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise TimeoutError("temporary")
        return "ok"

    result = SerialRetryPolicy(max_attempts=2, base_delay_s=0.01).run(flaky, label="query", logger=messages.append)
    assert result == "ok"
    assert sleeps == [0.01]
    assert messages and "temporary" in messages[0]

    with pytest.raises(RuntimeError):
        SerialRetryPolicy(max_attempts=1).run(lambda: (_ for _ in ()).throw(RuntimeError("final")))


def test_small_formatting_and_thread_buffer_edges() -> None:
    assert format_si("bad", "V") == "bad V"
    assert format_si(float("nan"), "V") == "nan V"
    assert format_si(0.0).startswith("0")
    assert format_voltage(1e-3) == "1 mV"
    assert format_current(1e-6) == "1 µA"
    assert format_resistance(1e3) == "1 kΩ"
    buf = ThreadSafeXYBuffer(maxsize=2)
    assert buf.get_snapshot() == ([], [])
    buf.append(1, 2)
    buf.append(3, 4)
    buf.append(5, 6)
    assert buf.get_snapshot() == ([3.0, 5.0], [4.0, 6.0])
    buf.clear()
    assert buf.get_snapshot() == ([], [])

from keith_ivt.core.sweep_runner import SweepRunner
from keith_ivt.data.logging_utils import AppLog
from keith_ivt.drivers.base import DriverCapabilities, DriverReadback, MeasureMode, SourceMode
from keith_ivt.services.measurement_service import MeasurementService
from keith_ivt.sweeps.plan import SweepExecutionKind, make_plan
from keith_ivt.utils.thread_safe import ThreadSafeBuffer




class RecordingMeterForCoverage:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.value = 0.0
    def connect(self): self.calls.append("connect")
    def close(self): self.calls.append("close")
    def identify(self): return "FAKE"
    def reset(self): self.calls.append("reset")
    def configure_for_sweep(self, config): self.calls.append(f"configure:{config.mode.value}")
    def set_source(self, source_cmd, value):
        self.calls.append(f"set:{source_cmd}:{value}")
        self.value = value
    def read_source_and_measure(self):
        self.calls.append("read")
        return self.value, self.value / 1000.0
    def output_on(self): self.calls.append("on")
    def output_off(self): self.calls.append("off")

class FakeSMUDriver:
    capabilities = DriverCapabilities(name="fake")

    def __init__(self):
        self.calls: list[str] = []
        self.value = 0.0

    def connect(self, profile): self.calls.append("connect")
    def disconnect(self): self.calls.append("disconnect")
    def identify(self): return "fake"
    def reset(self): self.calls.append("reset")
    def configure_source_measure(self, source_mode, measure_mode, compliance, nplc, autorange=True, source_range=None, measure_range=None):
        self.calls.append(f"config:{source_mode.value}:{measure_mode.value}:{compliance}:{nplc}:{autorange}:{source_range}:{measure_range}")
    def set_source(self, source_mode, value):
        self.calls.append(f"set:{source_mode.value}:{value}")
        self.value = value
    def read(self):
        self.calls.append("read")
        return DriverReadback(self.value, self.value / 1000.0)
    def output_on(self): self.calls.append("on")
    def output_off(self): self.calls.append("off")
    def close(self): self.calls.append("close")


def test_app_log_tail_and_missing_tail(tmp_path) -> None:
    log = AppLog(tmp_path / "log.txt", max_bytes=1024)
    assert log.tail() == []
    log.write("one")
    log.write("two")
    assert [line.split("] ", 1)[1] for line in log.tail(1)] == ["two"]


def test_thread_safe_buffer_edges() -> None:
    with pytest.raises(ValueError):
        ThreadSafeBuffer(maxsize=0)
    buf = ThreadSafeBuffer[int](maxsize=2)
    assert buf.is_empty()
    buf.extend([1, 2, 3])
    assert len(buf) == 2
    assert buf.had_overflow() is True
    assert buf.had_overflow() is False
    assert buf.get_snapshot() == [2, 3]
    assert buf.pop_front() == 2
    assert buf.pop_front() == 3
    assert buf.pop_front() is None


def test_measurement_service_run_plan_and_legacy_bridge(monkeypatch) -> None:
    driver = FakeSMUDriver()
    service = MeasurementService(driver)
    monkeypatch.setattr("keith_ivt.services.measurement_service.time.sleep", lambda _s: None)
    plan = make_plan(
        source_mode=SourceMode.VOLTAGE,
        measure_mode=MeasureMode.CURRENT,
        values=[0.0, 1.0],
        compliance=0.01,
        nplc=0.1,
        execution_kind=SweepExecutionKind.CONSTANT_TIME,
        interval_s=0.1,
    )
    callback: list[tuple[float, int, int]] = []
    reads = service.run_plan(plan, on_point=lambda r, i, t: callback.append((r.source_value, i, t)))
    assert [r.source_value for r in reads] == [0.0, 1.0]
    assert callback == [(0.0, 1, 2), (1.0, 2, 2)]
    assert driver.calls[-1] == "off"

    points = []
    cfg = SweepConfig(mode=SweepMode.VOLTAGE_SOURCE, start=0, stop=1, step=1, compliance=0.01, nplc=0.1)
    result = service.run_legacy_config(cfg, on_point=lambda p, i, t: points.append((p.source_value, i, t)))
    assert len(result.points) == 2
    assert points[-1] == (1.0, 2, 2)


def test_measurement_service_manual_and_stop_pause_paths(monkeypatch) -> None:
    driver = FakeSMUDriver()
    service = MeasurementService(driver)
    monkeypatch.setattr("keith_ivt.services.measurement_service.time.sleep", lambda _s: None)
    manual = make_plan(source_mode=SourceMode.VOLTAGE, measure_mode=MeasureMode.CURRENT, values=[], compliance=1, nplc=0.1, execution_kind=SweepExecutionKind.MANUAL_OUTPUT)
    with pytest.raises(ValueError):
        service.run_plan(manual)

    plan = make_plan(source_mode=SourceMode.VOLTAGE, measure_mode=MeasureMode.CURRENT, values=[1, 2], compliance=1, nplc=0.1)
    assert service.run_plan(plan, should_stop=lambda: True) == []
    assert driver.calls[-1] == "off"


def test_sweep_runner_constant_time_manual_and_no_output_off(monkeypatch) -> None:
    meter = RecordingMeterForCoverage()
    runner = SweepRunner(meter)
    monkeypatch.setattr("keith_ivt.core.sweep_runner._interruptible_sleep", lambda _s, _stop=None: None)
    cfg = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0,
        stop=0,
        step=1,
        compliance=0.01,
        nplc=0.1,
        sweep_kind=SweepKind.CONSTANT_TIME,
        constant_value=0.5,
        duration_s=0.1,
        interval_s=0.1,
        output_off_after_run=False,
    )
    result = runner.run(cfg, on_point=lambda p, i, t: None)
    assert len(result.points) == 2
    assert meter.calls[-1] != "off"
    with pytest.raises(ValueError):
        runner.run(SweepConfig(mode=SweepMode.VOLTAGE_SOURCE, start=0, stop=0, step=1, compliance=1, nplc=0.1, sweep_kind=SweepKind.MANUAL_OUTPUT))


def test_constant_time_interval_too_short_validation() -> None:
    with pytest.raises(ValueError):
        validate_config(SweepConfig(mode=SweepMode.VOLTAGE_SOURCE, start=0, stop=0, step=1, compliance=1, nplc=1, sweep_kind=SweepKind.CONSTANT_TIME, interval_s=0.001, duration_s=1))


def test_additional_small_branch_coverage(monkeypatch) -> None:
    assert estimate_point_seconds(0.1, mode="STEP", interval_s=None) == pytest.approx(minimum_interval_seconds(0.1))
    store = DatasetStore()
    cfg = SweepConfig(mode=SweepMode.VOLTAGE_SOURCE, start=0, stop=0, step=1, compliance=1, nplc=0.1)
    trace = store.add_result(SweepResult(cfg, []), name="A")
    store.rename(trace.trace_id, "   ")
    assert trace.name == "A"
    with pytest.raises(ValueError):
        ThreadSafeXYBuffer(maxsize=0)
    validate_config(SweepConfig(mode=SweepMode.VOLTAGE_SOURCE, start=0, stop=0, step=1, compliance=1, nplc=0.1, sweep_kind=SweepKind.ADAPTIVE, adaptive_logic="values=[0, 1]"))


def test_pause_paths_break_cleanly(monkeypatch) -> None:
    monkeypatch.setattr("keith_ivt.core.sweep_runner._interruptible_sleep", lambda _s, _stop=None: None)
    meter = RecordingMeterForCoverage()
    runner = SweepRunner(meter)
    cfg = SweepConfig(mode=SweepMode.VOLTAGE_SOURCE, start=0, stop=1, step=1, compliance=0.01, nplc=0.1)
    pause_calls = {"n": 0}
    def pause_then_stop() -> bool:
        pause_calls["n"] += 1
        return pause_calls["n"] == 1
    result = runner.run(cfg, should_pause=pause_then_stop, should_stop=lambda: pause_calls["n"] >= 1)
    assert result.points == []
    assert meter.calls[-1] == "off"

    meter2 = RecordingMeterForCoverage()
    continuous = SweepConfig(mode=SweepMode.VOLTAGE_SOURCE, start=0, stop=0, step=1, compliance=0.01, nplc=0.1, sweep_kind=SweepKind.CONSTANT_TIME, continuous_time=True, constant_value=0.1, interval_s=0.1)
    stop_calls = {"n": 0}
    def stop_after_pause() -> bool:
        stop_calls["n"] += 1
        return stop_calls["n"] >= 2
    result2 = SweepRunner(meter2).run(continuous, should_pause=lambda: True, should_stop=stop_after_pause)
    assert result2.points == []
    assert meter2.calls[-1] == "off"


def test_measurement_service_pause_stop_inner_branch(monkeypatch) -> None:
    driver = FakeSMUDriver()
    service = MeasurementService(driver)
    monkeypatch.setattr("keith_ivt.services.measurement_service.time.sleep", lambda _s: None)
    plan = make_plan(source_mode=SourceMode.VOLTAGE, measure_mode=MeasureMode.CURRENT, values=[1, 2], compliance=1, nplc=0.1)
    calls = {"pause": 0, "stop": 0}
    def pause_once() -> bool:
        calls["pause"] += 1
        return calls["pause"] == 1
    def stop_during_pause() -> bool:
        calls["stop"] += 1
        return calls["stop"] >= 2
    reads = service.run_plan(plan, should_pause=pause_once, should_stop=stop_during_pause)
    assert reads == []
    assert driver.calls[-1] == "off"
