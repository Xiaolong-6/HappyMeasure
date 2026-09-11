from __future__ import annotations

import json

import pytest

from keith_ivt.data.exporters import save_csv
from keith_ivt.data.importers import load_csv
from keith_ivt.data.presets import _clean
from keith_ivt.data.settings import load_settings
from keith_ivt.models import (
    SweepConfig,
    SweepKind,
    SweepMode,
    SweepPoint,
    SweepResult,
    source_values_for_config,
)
from keith_ivt.sweeps.plan import plan_from_config
from keith_ivt.sweeps.table_sweep import (
    parse_segment_text,
)


def test_segment_text_runs_ascending_ranges_in_line_order() -> None:
    values = parse_segment_text("0.1, 1, 0.1\n1, 20, 1")

    assert len(values) == 29
    assert values[:3] == pytest.approx([0.1, 0.2, 0.3])
    assert values[9:12] == pytest.approx([1, 2, 3])
    assert values[-1] == pytest.approx(20)


@pytest.mark.parametrize("step", [1, -1])
def test_segment_text_supports_descending_ranges_with_step_magnitude(step: int) -> None:
    assert parse_segment_text(f"20, 1, {step}") == pytest.approx(list(range(20, 0, -1)))


def test_segment_text_supports_ascending_ranges_with_negative_step() -> None:
    assert parse_segment_text("1, 3, -1") == pytest.approx([1, 2, 3])


def test_duplicate_option_is_global_and_preserves_first_occurrence() -> None:
    text = "0, 2, 1\n2, 0, -1"

    assert parse_segment_text(text, remove_duplicates=True) == pytest.approx([0, 1, 2])
    assert parse_segment_text(text, remove_duplicates=False) == pytest.approx([0, 1, 2, 2, 1, 0])


def test_segment_text_ignores_blank_lines_and_comments() -> None:
    text = "# coarse range\n\n0, 1, 0.5  # volts\n1, 2, 1"
    assert parse_segment_text(text) == pytest.approx([0, 0.5, 1, 2])


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("1, 20", "Line 1"),
        ("a, 20, 1", "Line 1"),
        ("1, 20, 0", "step cannot be 0"),
        ("1, inf, 1", "infinite"),
        ("# nothing", "at least one"),
    ],
)
def test_segment_text_reports_actionable_errors(text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_segment_text(text)


def test_segment_text_rejects_huge_ranges_before_allocating() -> None:
    with pytest.raises(ValueError, match="exceeds 100 points"):
        parse_segment_text("0, 1000000, 0.001", max_points=100)


def test_old_settings_leave_new_adaptive_editor_empty(tmp_path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"default_adaptive_logic": "values = [0, 0.5, 1, 2, 3]"}),
        encoding="utf-8",
    )

    settings = load_settings(path)

    assert settings.default_adaptive_segments == ""
    assert settings.default_adaptive_remove_duplicates is True


def test_old_presets_leave_new_adaptive_editor_empty() -> None:
    migrated = _clean(
        {
            "default_sweep_kind": "ADAPTIVE",
            "default_adaptive_logic": "values = [0, 0.5, 1]",
        }
    )
    assert migrated["sweep"]["parameters"]["segments"] == ""


def test_invalid_old_preset_logic_does_not_fill_the_new_editor() -> None:
    migrated = _clean(
        {
            "default_sweep_kind": "ADAPTIVE",
            "default_adaptive_logic": "not valid",
        }
    )
    assert migrated["sweep"]["parameters"]["segments"] == ""


def test_config_preserves_duplicate_values_when_option_is_disabled() -> None:
    config = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0,
        stop=1,
        step=1,
        compliance=1,
        sweep_kind=SweepKind.ADAPTIVE,
        adaptive_segments="0, 1, 1\n1, 2, 1",
        adaptive_remove_duplicates=False,
    )

    assert source_values_for_config(config) == pytest.approx([0, 1, 1, 2])
    assert plan_from_config(config).values == pytest.approx([0, 1, 1, 2])


def test_csv_round_trip_preserves_editable_segments_and_duplicate_option(tmp_path) -> None:
    config = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0,
        stop=2,
        step=1,
        compliance=1,
        sweep_kind=SweepKind.ADAPTIVE,
        adaptive_logic="values = [0.0, 1.0, 1.0, 2.0]",
        adaptive_segments="0, 1, 1\n1, 2, 1",
        adaptive_remove_duplicates=False,
    )
    path = save_csv(
        SweepResult(config=config, points=[SweepPoint(0, 0), SweepPoint(1, 0.1)]),
        tmp_path / "adaptive.csv",
    )

    restored = load_csv(path)[0].config

    assert restored.adaptive_segments == config.adaptive_segments
    assert restored.adaptive_remove_duplicates is False
