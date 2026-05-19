from __future__ import annotations

from keith_ivt.models import (
    SweepConfig,
    SweepKind,
    SweepMode,
    make_hysteresis_values,
    source_values_for_config,
)


def test_make_hysteresis_values_returns_forward_then_reverse_without_duplicate_turnpoint() -> None:
    assert make_hysteresis_values([0.0, 0.5, 1.0]) == [0.0, 0.5, 1.0, 0.5, 0.0]


def test_step_sweep_hysteresis_extends_source_sequence() -> None:
    cfg = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0.0,
        stop=2.0,
        step=1.0,
        compliance=0.01,
        sweep_kind=SweepKind.STEP,
        hysteresis=True,
    )

    assert source_values_for_config(cfg) == [0.0, 1.0, 2.0, 1.0, 0.0]


def test_adaptive_sweep_hysteresis_extends_generated_values() -> None:
    cfg = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0.0,
        stop=1.0,
        step=1.0,
        compliance=0.01,
        sweep_kind=SweepKind.ADAPTIVE,
        hysteresis=True,
        adaptive_logic="values = [0.0, 0.25, 1.0]",
    )

    assert source_values_for_config(cfg) == [0.0, 0.25, 1.0, 0.25, 0.0]


def test_time_sweep_ignores_hysteresis_flag() -> None:
    cfg = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0.0,
        stop=1.0,
        step=1.0,
        compliance=0.01,
        sweep_kind=SweepKind.CONSTANT_TIME,
        hysteresis=True,
        constant_value=0.1,
        duration_s=1.0,
        interval_s=0.5,
    )

    assert source_values_for_config(cfg) == [0.1, 0.1, 0.1]
