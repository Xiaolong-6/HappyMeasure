from __future__ import annotations

import pytest

from keith_ivt.core.adaptive_logic import adaptive_values_from_logic
from keith_ivt.models import (
    SweepConfig,
    SweepKind,
    SweepMode,
    make_constant_time_values,
    make_source_values,
    validate_config,
)


@pytest.mark.parametrize(
    ("start", "stop", "step", "expected"),
    [
        (-1, 1, 1, [-1.0, 0.0, 1.0]),
        (-1, 1, -1, [-1.0, 0.0, 1.0]),
        (1, -1, 1, [1.0, 0.0, -1.0]),
        (1, -1, -1, [1.0, 0.0, -1.0]),
        (1, 1, 1, [1.0]),
    ],
)
def test_make_source_values_uses_step_as_magnitude(
    start: float, stop: float, step: float, expected: list[float]
) -> None:
    assert make_source_values(start, stop, step) == expected


def test_make_source_values_rejects_zero_step() -> None:
    with pytest.raises(ValueError, match="Step cannot be zero"):
        make_source_values(0, 1, 0)


@pytest.mark.parametrize(
    ("start", "stop", "step"),
    [
        (float("nan"), 1.0, 0.1),
        (0.0, float("inf"), 0.1),
        (0.0, 1.0, float("-inf")),
    ],
)
def test_make_source_values_rejects_non_finite_inputs(
    start: float, stop: float, step: float
) -> None:
    with pytest.raises(ValueError, match="Start, stop, and step must be finite"):
        make_source_values(start, stop, step)


def test_constant_time_values_and_validation() -> None:
    assert make_constant_time_values(0.5, 1.0, 0.5) == [0.5, 0.5, 0.5]
    assert len(make_constant_time_values(0.5, 0.3, 0.1)) == 4
    assert len(make_constant_time_values(0.5, 0.7, 0.1)) == 8
    with pytest.raises(ValueError):
        make_constant_time_values(0.5, 0.0, 0.5)
    with pytest.raises(ValueError, match="must be finite"):
        make_constant_time_values(0.5, float("inf"), 0.5)
    cfg = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0,
        stop=1,
        step=1,
        compliance=0.01,
        sweep_kind=SweepKind.CONSTANT_TIME,
        duration_s=1,
        interval_s=0.2,
    )
    validate_config(cfg)


def test_validate_config_rejects_bad_ranges_and_compliance() -> None:
    cfg = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0,
        stop=1,
        step=1,
        compliance=0.01,
        auto_source_range=False,
        source_range=0,
    )
    with pytest.raises(ValueError):
        validate_config(cfg)
    cfg = SweepConfig(mode=SweepMode.VOLTAGE_SOURCE, start=0, stop=1, step=1, compliance=0)
    with pytest.raises(ValueError):
        validate_config(cfg)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"compliance": float("nan")}, "Compliance must be finite"),
        ({"nplc": float("inf")}, "NPLC must be finite"),
        ({"delay_s": float("-inf")}, "Delay must be finite"),
        (
            {"auto_source_range": False, "source_range": float("nan")},
            "Fixed source range must be finite",
        ),
        (
            {"auto_measure_range": False, "measure_range": float("inf")},
            "Fixed measure range must be finite",
        ),
        ({"range_settle_delay_ms": float("nan")}, "Range settle delay must be finite"),
        (
            {"discard_after_range_change": float("inf")},
            "Discard readings after range change must be finite",
        ),
        (
            {"sweep_kind": SweepKind.CONSTANT_TIME, "constant_value": float("nan")},
            "Constant value must be finite",
        ),
        (
            {"sweep_kind": SweepKind.CONSTANT_TIME, "duration_s": float("inf")},
            "Duration must be finite",
        ),
        (
            {"sweep_kind": SweepKind.CONSTANT_TIME, "interval_s": float("nan")},
            "Interval must be finite",
        ),
        (
            {"sweep_kind": SweepKind.MANUAL_OUTPUT, "constant_value": float("inf")},
            "Manual output value must be finite",
        ),
    ],
)
def test_validate_config_rejects_non_finite_active_values(changes, message: str) -> None:
    values = dict(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0.0,
        stop=1.0,
        step=0.1,
        compliance=0.01,
        nplc=0.1,
    )
    values.update(changes)

    with pytest.raises(ValueError, match=message):
        validate_config(SweepConfig(**values))


def test_adaptive_logic_values() -> None:
    vals = adaptive_values_from_logic("values = [0, 0.5, 1]")
    assert vals == [0.0, 0.5, 1.0]
    vals = adaptive_values_from_logic("values = linspace(0, 1, 3)")
    assert vals == [0.0, 0.5, 1.0]


@pytest.mark.parametrize(
    "logic",
    [
        "import os\nvalues = [0]",
        "values = __import__('os').getcwd()",
        "values = [x for x in range(3)]",
        "other = [0]",
        "values = [float('nan')]",
    ],
)
def test_adaptive_logic_rejects_executable_python(logic: str) -> None:
    with pytest.raises(ValueError):
        adaptive_values_from_logic(logic)


def test_adaptive_logic_rejects_huge_generated_plan_before_allocation() -> None:
    with pytest.raises(ValueError, match="must not exceed"):
        adaptive_values_from_logic("values = linspace(0, 1, 100001)")
