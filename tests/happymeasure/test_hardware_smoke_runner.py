from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SMOKE = ROOT / "tools" / "hardware" / "keithley2400_smoke.py"


def _load_smoke_module():
    spec = importlib.util.spec_from_file_location("keithley2400_smoke", SMOKE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["keithley2400_smoke"] = module
    spec.loader.exec_module(module)
    return module


smoke = _load_smoke_module()


def test_overflow_reading_mirrors_driver_sentinel() -> None:
    assert smoke.is_overflow_reading(9.91e37) is True
    assert smoke.is_overflow_reading(-9.91e37) is True
    assert smoke.is_overflow_reading(9.905e37) is True
    assert smoke.is_overflow_reading(1e-6) is False
    assert smoke.is_overflow_reading(float("nan")) is False
    assert smoke.is_overflow_reading(float("inf")) is False
    assert smoke.is_overflow_reading("bad") is False


def test_acquisition_summary_reports_timing_and_data_quality() -> None:
    summary = smoke.acquisition_summary(
        "fast_fixed",
        elapsed=[0.0, 0.007, 0.014, 0.021],
        measured=[1e-9, 2e-9, 3e-9, 4e-9],
        warnings=[],
    )
    assert summary["point_count"] == 4
    assert summary["median_dt_ms"] == pytest.approx(7.0)
    assert summary["mean_dt_ms"] == pytest.approx(7.0)
    assert summary["p95_dt_ms"] == pytest.approx(7.0)
    assert summary["effective_hz"] == pytest.approx(1000.0 / 7.0)
    assert summary["strictly_increasing"] is True
    assert summary["duplicate_elapsed_count"] == 0
    assert summary["overflow_count"] == 0
    assert summary["invalid_nonfinite_count"] == 0


def test_acquisition_summary_flags_duplicates_overflow_and_warnings() -> None:
    summary = smoke.acquisition_summary(
        "fast_auto",
        elapsed=[0.0, 0.007, 0.007, 0.021],
        measured=[1e-9, 9.91e37, float("nan"), 4e-9],
        warnings=["Skipped 1 Keithley overflow measurement(s)."],
    )
    assert summary["strictly_increasing"] is False
    assert summary["duplicate_elapsed_count"] == 1
    assert summary["overflow_count"] == 1
    assert summary["invalid_nonfinite_count"] == 1
    assert summary["warnings"] == ["Skipped 1 Keithley overflow measurement(s)."]


def _fast_sequence(*names: str) -> list[tuple[float, str]]:
    return [(float(index) * 0.1, name) for index, name in enumerate(names)]


def test_fast_scpi_order_accepts_valid_sequence() -> None:
    commands = _fast_sequence(
        ":SENS:FUNC 'CURR'",
        ":SENS:FUNC:CONC OFF",
        ":SENS:FUNC 'CURR'",
        ":SENS:AVER:STAT OFF",
        ":FORM:ELEM CURR",
        ":READ?",
        ":READ?",
    )
    ok, detail = smoke.check_fast_scpi_order(commands)
    assert ok is True
    assert "no hot-path range queries" in detail


def test_fast_scpi_order_allows_only_expected_range_snapshot() -> None:
    auto_commands = _fast_sequence(
        ":SENS:FUNC:CONC OFF",
        ":SENS:FUNC 'CURR'",
        ":FORM:ELEM CURR",
        ":SENS:CURR:RANG?",
        ":READ?",
        ":READ?",
    )
    assert smoke.check_fast_scpi_order(auto_commands, auto_measure_range=True)[0] is True
    ok, detail = smoke.check_fast_scpi_order(auto_commands, auto_measure_range=False)
    assert ok is False
    assert "setup" in detail

    for query in (":SENS:CURR:RANG?", ":SENS:CURR:RANG:AUTO?"):
        hot_path = _fast_sequence(
            ":SENS:FUNC:CONC OFF",
            ":SENS:FUNC 'CURR'",
            ":FORM:ELEM CURR",
            ":READ?",
            query,
            ":READ?",
        )
        ok, detail = smoke.check_fast_scpi_order(hot_path, auto_measure_range=True)
        assert ok is False
        assert "hot path" in detail


def test_fast_scpi_order_rejects_broken_function_selection() -> None:
    for commands in (
        _fast_sequence(":SENS:FUNC 'CURR'", ":SENS:FUNC:CONC OFF", ":FORM:ELEM CURR", ":READ?"),
        _fast_sequence(":SENS:FUNC:CONC OFF", ":FORM:ELEM CURR", ":READ?"),
        _fast_sequence(":SENS:FUNC:CONC OFF", ":SENS:FUNC 'CURR'", ":READ?", ":FORM:ELEM CURR"),
        [(0.0, ":SENS:FUNC:CONC OFF")],
    ):
        assert smoke.check_fast_scpi_order(commands)[0] is False


def test_fast_and_standard_configs_are_safe_by_default() -> None:
    from keith_ivt.models import validate_config

    fast = smoke.make_fast_cfg("COM3", 57600, smoke.Terminal.REAR)
    standard = smoke.make_cfg("COM3", 57600, smoke.Terminal.REAR, 0.1, 0.2, 3)
    validate_config(fast)
    validate_config(standard)

    assert fast.fast_acquisition is True
    assert fast.constant_value == 0.0
    assert fast.output_off_after_run is True
    assert fast.nplc == pytest.approx(0.1)
    assert standard.constant_value == 0.0
    custom = smoke.make_cfg("COM3", 57600, smoke.Terminal.REAR, 0.1, 0.2, 3, constant_v=0.1)
    assert custom.constant_value == pytest.approx(0.1)


def test_resistor_range_selection_and_configs_avoid_overrange() -> None:
    assert smoke.choose_measure_range(10e-6) == pytest.approx(100e-6)
    assert smoke.choose_measure_range(0.1 / 1e6) == pytest.approx(1e-6)
    expected_a = 0.1 / 10_000.0
    measure_range = smoke.choose_measure_range(expected_a)
    standard = smoke.make_cfg(
        "COM3",
        57600,
        smoke.Terminal.REAR,
        0.1,
        0.2,
        3,
        constant_v=0.1,
        measure_range=measure_range,
    )
    fast = smoke.make_fast_cfg(
        "COM3",
        57600,
        smoke.Terminal.REAR,
        duration_s=0.5,
        constant_v=0.1,
        measure_range=measure_range,
    )
    assert standard.auto_measure_range is False
    assert fast.auto_measure_range is False
    assert standard.measure_range == pytest.approx(measure_range)
    assert fast.measure_range == pytest.approx(measure_range)


def test_resistor_validation_refuses_unsafe_or_invalid_values() -> None:
    with pytest.raises(RuntimeError, match="Refusing Level-1 run"):
        smoke.check_resistor_compliance(95e-6)
    smoke.check_resistor_compliance(10e-6)

    for bad in ("bad", "ask-me", None, float("nan"), float("inf"), 0.0, -100.0):
        with pytest.raises(ValueError, match="Invalid --resistor-ohms"):
            smoke.parse_resistor_ohms(bad)
    assert smoke.parse_resistor_ohms("10000") == pytest.approx(10_000.0)


def test_nanosecond_trace_boundary_preserves_timing_and_detects_duplicates() -> None:
    base_ns = 1_000_000_000
    starts_ns = [base_ns + index * 7_000_000 for index in range(4)]
    summary = smoke.acquisition_summary(
        "fast_fixed",
        elapsed=[stamp * 1e-9 for stamp in starts_ns],
        measured=[1e-9, 2e-9, 3e-9, 4e-9],
        warnings=[],
    )
    assert summary["strictly_increasing"] is True
    assert summary["duplicate_elapsed_count"] == 0
    assert summary["median_dt_ms"] == pytest.approx(7.0)

    duplicate_ns = [2_000_000_000, 2_007_000_000, 2_007_000_000]
    duplicate = smoke.acquisition_summary(
        "fast_fixed",
        elapsed=[stamp * 1e-9 for stamp in duplicate_ns],
        measured=[1e-9, 2e-9, 3e-9],
        warnings=[],
    )
    assert duplicate["strictly_increasing"] is False
    assert duplicate["duplicate_elapsed_count"] == 1


def test_diagnostic_clock_is_monotonic_integer_nanoseconds() -> None:
    first = smoke.diagnostic_clock_ns()
    second = smoke.diagnostic_clock_ns()
    assert isinstance(first, int)
    assert isinstance(second, int)
    assert second >= first
