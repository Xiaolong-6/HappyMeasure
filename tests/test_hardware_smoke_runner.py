from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
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
    # 9.91e37 itself is finite (that is why the sentinel is dangerous).
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


def test_fast_scpi_order_accepts_auto_setup_snapshot() -> None:
    commands = _fast_sequence(
        ":SENS:FUNC:CONC OFF",
        ":SENS:FUNC 'CURR'",
        ":FORM:ELEM CURR",
        ":SENS:CURR:RANG?",
        ":READ?",
        ":READ?",
    )

    ok, _ = smoke.check_fast_scpi_order(commands, auto_measure_range=True)

    assert ok is True


def test_fast_scpi_order_rejects_setup_snapshot_for_fixed_range() -> None:
    commands = _fast_sequence(
        ":SENS:FUNC:CONC OFF",
        ":SENS:FUNC 'CURR'",
        ":FORM:ELEM CURR",
        ":SENS:CURR:RANG?",
        ":READ?",
    )

    ok, detail = smoke.check_fast_scpi_order(commands, auto_measure_range=False)

    assert ok is False
    assert "setup" in detail


def test_fast_scpi_order_rejects_hot_path_range_queries() -> None:
    for query in (":SENS:CURR:RANG?", ":SENS:CURR:RANG:AUTO?"):
        commands = _fast_sequence(
            ":SENS:FUNC:CONC OFF",
            ":SENS:FUNC 'CURR'",
            ":FORM:ELEM CURR",
            ":READ?",
            query,
            ":READ?",
        )

        ok, detail = smoke.check_fast_scpi_order(commands, auto_measure_range=True)

        assert ok is False
        assert "hot path" in detail


def test_fast_scpi_order_rejects_broken_function_selection() -> None:
    curr_before_conc_only = _fast_sequence(
        ":SENS:FUNC 'CURR'",
        ":SENS:FUNC:CONC OFF",
        ":FORM:ELEM CURR",
        ":READ?",
    )
    ok, detail = smoke.check_fast_scpi_order(curr_before_conc_only)
    assert ok is False
    assert "reselection" in detail

    no_curr = _fast_sequence(
        ":SENS:FUNC:CONC OFF",
        ":FORM:ELEM CURR",
        ":READ?",
    )
    ok, _ = smoke.check_fast_scpi_order(no_curr)
    assert ok is False

    read_before_form = _fast_sequence(
        ":SENS:FUNC:CONC OFF",
        ":SENS:FUNC 'CURR'",
        ":READ?",
        ":FORM:ELEM CURR",
    )
    ok, _ = smoke.check_fast_scpi_order(read_before_form)
    assert ok is False

    ok, _ = smoke.check_fast_scpi_order([(0.0, ":SENS:FUNC:CONC OFF")])
    assert ok is False


def test_make_fast_cfg_is_zero_volt_output_off_by_default() -> None:
    from keith_ivt.models import validate_config

    cfg = smoke.make_fast_cfg("COM3", 57600, smoke.Terminal.REAR)

    validate_config(cfg)
    assert cfg.fast_acquisition is True
    assert cfg.constant_value == 0.0
    assert cfg.output_off_after_run is True
    assert cfg.nplc == pytest.approx(0.1)


def test_make_cfg_default_remains_zero_volt() -> None:
    from keith_ivt.models import validate_config

    cfg = smoke.make_cfg("COM3", 57600, smoke.Terminal.REAR, 0.1, 0.2, 3)
    validate_config(cfg)

    assert cfg.constant_value == 0.0
    custom = smoke.make_cfg("COM3", 57600, smoke.Terminal.REAR, 0.1, 0.2, 3, constant_v=0.1)
    assert custom.constant_value == pytest.approx(0.1)


def test_git_commit_returns_string() -> None:
    assert isinstance(smoke.git_commit(), str)


def test_resistor_range_selection_avoids_overrange() -> None:
    assert smoke.choose_measure_range(10e-6) == pytest.approx(100e-6)
    assert smoke.choose_measure_range(10e-6) != pytest.approx(1e-6)
    assert smoke.choose_measure_range(0.1 / 1e6) == pytest.approx(1e-6)


def test_resistor_configs_share_identical_measurement_range() -> None:
    expected_a = 0.1 / 10_000.0
    resistor_range = smoke.choose_measure_range(expected_a)
    standard = smoke.make_cfg(
        "COM3", 57600, smoke.Terminal.REAR, 0.1, 0.2, 3,
        constant_v=0.1, measure_range=resistor_range,
    )
    fast = smoke.make_fast_cfg(
        "COM3", 57600, smoke.Terminal.REAR,
        duration_s=0.5, constant_v=0.1, measure_range=resistor_range,
    )

    assert standard.auto_measure_range is False
    assert fast.auto_measure_range is False
    assert standard.measure_range == pytest.approx(resistor_range)
    assert fast.measure_range == pytest.approx(resistor_range)


def test_resistor_near_compliance_is_refused() -> None:
    with pytest.raises(RuntimeError, match="Refusing Level-1 run"):
        smoke.check_resistor_compliance(95e-6)
    smoke.check_resistor_compliance(10e-6)


def test_invalid_resistor_values_are_refused() -> None:
    for bad in ("bad", "ask-me", None, float("nan"), float("inf"), 0.0, -100.0):
        with pytest.raises(ValueError, match="Invalid --resistor-ohms"):
            smoke.parse_resistor_ohms(bad)
    assert smoke.parse_resistor_ohms("10000") == pytest.approx(10_000.0)


def test_nanosecond_trace_boundary_preserves_sub_15ms_differences() -> None:
    base_ns = 1_000_000_000
    starts_ns = [base_ns + index * 7_000_000 for index in range(4)]
    starts_s = [stamp_ns * 1e-9 for stamp_ns in starts_ns]
    summary = smoke.acquisition_summary(
        "fast_fixed",
        elapsed=starts_s,
        measured=[1e-9, 2e-9, 3e-9, 4e-9],
        warnings=[],
    )

    assert summary["strictly_increasing"] is True
    assert summary["duplicate_elapsed_count"] == 0
    assert summary["median_dt_ms"] == pytest.approx(7.0)
    assert summary["mean_dt_ms"] == pytest.approx(7.0)
    assert summary["p95_dt_ms"] == pytest.approx(7.0)


def test_nanosecond_trace_boundary_detects_duplicates() -> None:
    base_ns = 2_000_000_000
    starts_ns = [base_ns, base_ns + 7_000_000, base_ns + 7_000_000]
    starts_s = [stamp_ns * 1e-9 for stamp_ns in starts_ns]
    summary = smoke.acquisition_summary(
        "fast_fixed",
        elapsed=starts_s,
        measured=[1e-9, 2e-9, 3e-9],
        warnings=[],
    )

    assert summary["strictly_increasing"] is False
    assert summary["duplicate_elapsed_count"] == 1


def test_diagnostic_clock_is_high_resolution_monotonic() -> None:
    first = smoke.diagnostic_clock_ns()
    second = smoke.diagnostic_clock_ns()

    assert isinstance(first, int)
    assert isinstance(second, int)
    assert second >= first
