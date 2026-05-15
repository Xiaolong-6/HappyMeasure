from __future__ import annotations

import pytest

from keith_ivt.core.adaptive_logic import adaptive_values_from_logic
from keith_ivt.models import SweepConfig, SweepKind, SweepMode, make_constant_time_values, make_source_values, validate_config


def test_make_source_values_forward_reverse_and_invalid() -> None:
    assert make_source_values(0, 2, 1) == [0.0, 1.0, 2.0]
    assert make_source_values(2, 0, -1) == [2.0, 1.0, 0.0]
    with pytest.raises(ValueError):
        make_source_values(0, 1, 0)
    with pytest.raises(ValueError):
        make_source_values(0, 1, -1)


def test_constant_time_values_and_validation() -> None:
    assert make_constant_time_values(0.5, 1.0, 0.5) == [0.5, 0.5, 0.5]
    with pytest.raises(ValueError):
        make_constant_time_values(0.5, 0.0, 0.5)
    cfg = SweepConfig(mode=SweepMode.VOLTAGE_SOURCE, start=0, stop=1, step=1, compliance=0.01, sweep_kind=SweepKind.CONSTANT_TIME, duration_s=1, interval_s=0.2)
    validate_config(cfg)


def test_validate_config_rejects_bad_ranges_and_compliance() -> None:
    cfg = SweepConfig(mode=SweepMode.VOLTAGE_SOURCE, start=0, stop=1, step=1, compliance=0.01, auto_source_range=False, source_range=0)
    with pytest.raises(ValueError):
        validate_config(cfg)
    cfg = SweepConfig(mode=SweepMode.VOLTAGE_SOURCE, start=0, stop=1, step=1, compliance=0)
    with pytest.raises(ValueError):
        validate_config(cfg)


def test_adaptive_logic_values() -> None:
    vals = adaptive_values_from_logic("values = [0, 0.5, 1]")
    assert vals == [0.0, 0.5, 1.0]
    vals = adaptive_values_from_logic("values = linspace(0, 1, 3)")
    assert vals == [0.0, 0.5, 1.0]
