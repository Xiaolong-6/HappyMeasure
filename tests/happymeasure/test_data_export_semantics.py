from __future__ import annotations

from pathlib import Path

import pytest

from keith_ivt.data.exporters import result_metadata, save_combined_csv
from keith_ivt.data.importers import load_csv
from keith_ivt.models import SweepConfig, SweepKind, SweepMode, SweepPoint, SweepResult


def _fast_time_result(
    name: str, *, interval_s: float, elapsed: list[float], warning: str | None = None
) -> SweepResult:
    config = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0.0,
        stop=0.0,
        step=1.0,
        compliance=1e-3,
        nplc=0.1,
        delay_s=0.0,
        device_name=name,
        sweep_kind=SweepKind.CONSTANT_TIME,
        constant_value=0.0,
        duration_s=1.0,
        interval_s=interval_s,
        auto_source_range=False,
        auto_measure_range=False,
        source_range=20.0,
        measure_range=1e-3,
        fast_acquisition=True,
    )
    points = [
        SweepPoint(0.0, float(index + 1) * 1e-6, elapsed_s=value)
        for index, value in enumerate(elapsed)
    ]
    return SweepResult(config, points, warnings=[warning] if warning else [])


def test_fast_metadata_separates_configured_interval_from_execution_policy() -> None:
    first = _fast_time_result("same", interval_s=0.1, elapsed=[0.01, 0.02])
    second = _fast_time_result("same", interval_s=0.5, elapsed=[0.01, 0.02])
    first_meta = result_metadata(first)
    second_meta = result_metadata(second)

    assert first_meta["interval_s"] == pytest.approx(0.1)
    assert second_meta["interval_s"] == pytest.approx(0.5)
    assert first_meta["configured_interval_s"] == pytest.approx(0.1)
    assert second_meta["configured_interval_s"] == pytest.approx(0.5)
    assert first_meta["sampling_policy"] == second_meta["sampling_policy"] == "as_fast_as_possible"
    assert first_meta["effective_interval_s"] is None
    assert second_meta["effective_interval_s"] is None
    assert first_meta["effective_nplc"] == second_meta["effective_nplc"] == pytest.approx(0.1)
    assert (
        first_meta["effective_software_delay_s"] == second_meta["effective_software_delay_s"] == 0.0
    )
    assert first_meta["config_fingerprint"] == second_meta["config_fingerprint"]


def test_combined_csv_uses_long_format_for_different_elapsed_axes_and_keeps_warnings(
    tmp_path: Path,
) -> None:
    first = _fast_time_result("a", interval_s=0.1, elapsed=[0.01, 0.10], warning="warning a")
    second = _fast_time_result("b", interval_s=0.1, elapsed=[0.02, 0.11], warning="warning b")

    path = save_combined_csv([first, second], tmp_path / "different_elapsed.csv")
    loaded = {result.config.device_name: result for result in load_csv(path)}

    assert "# format,long-v2" in path.read_text(encoding="utf-8").replace("\r", "")
    assert [point.elapsed_s for point in loaded["a"].points] == [0.01, 0.10]
    assert [point.elapsed_s for point in loaded["b"].points] == [0.02, 0.11]
    assert loaded["a"].warnings == ["warning a"]
    assert loaded["b"].warnings == ["warning b"]
