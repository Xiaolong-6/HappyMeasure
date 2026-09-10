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


def test_fast_scpi_order_accepts_valid_sequence() -> None:
    commands = [
        (0.0, ":SENS:FUNC:CONC OFF"),
        (0.1, ":SENS:AVER:STAT OFF"),
        (0.2, ":FORM:ELEM CURR"),
        (0.3, ":READ?"),
    ]

    ok, detail = smoke.check_fast_scpi_order(commands)

    assert ok is True
    assert "no per-sample range queries" in detail


def test_fast_scpi_order_rejects_missing_or_misordered_commands() -> None:
    ok, _ = smoke.check_fast_scpi_order([(0.0, ":SENS:FUNC:CONC OFF")])
    assert ok is False

    ok, detail = smoke.check_fast_scpi_order(
        [(0.0, ":FORM:ELEM CURR"), (0.1, ":SENS:FUNC:CONC OFF")]
    )
    assert ok is False
    assert "precede" in detail

    ok, detail = smoke.check_fast_scpi_order(
        [
            (0.0, ":SENS:FUNC:CONC OFF"),
            (0.1, ":FORM:ELEM CURR"),
            (0.2, ":SENS:CURR:RANG?"),
        ]
    )
    assert ok is False
    assert "telemetry" in detail


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
