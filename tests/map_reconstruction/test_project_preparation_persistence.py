from __future__ import annotations

from pathlib import Path

import pytest

from map_reconstruction.models import ScanPattern
from map_reconstruction.processing import MapProcessingConfig
from map_reconstruction.project_io import ProjectState, load_project, save_project
from map_reconstruction.preparation import DarkCorrectionMode, DarkRegion, SignalPreparationConfig


def _state(preparation: SignalPreparationConfig) -> ProjectState:
    return ProjectState(
        original_filename="measurement.csv",
        signal="Current_A",
        rows=2,
        columns=2,
        scan_pattern=ScanPattern.SAME_DIRECTION,
        first_row_ltr=True,
        aggregation="median",
        row_a_s=0.0,
        row_b_s=1.0,
        rows_apart=1,
        row_offset=0,
        point_a_s=0.0,
        point_b_s=0.1,
        points_apart=1,
        point_offset=0,
        preparation=preparation,
        processing=MapProcessingConfig(),
        flip_y=False,
    )


def _raw_csv() -> bytes:
    return (
        b"# schema,single-v2\r\n"
        b"# section,data\r\n"
        b"Elapsed_s,Current_A,Voltage_V\r\n"
        b"0,1e-6,0.1\r\n"
        b"0.1,2e-6,0.1\r\n"
    )


@pytest.mark.parametrize(
    "preparation",
    [
        SignalPreparationConfig(
            dark_correction_mode=DarkCorrectionMode.MANUAL_REGIONS,
            manual_dark_regions=(DarkRegion(0.0, 0.1),),
            apply_baseline=False,
        ),
        SignalPreparationConfig(
            dark_correction_mode=DarkCorrectionMode.ROLLING_QUANTILE,
            apply_baseline=False,
        ),
    ],
)
def test_nondefault_preparation_round_trips_when_baseline_is_disabled(
    tmp_path: Path, preparation: SignalPreparationConfig
) -> None:
    path = tmp_path / "configured_preparation.hmmap"
    save_project(path, _state(preparation), _raw_csv())

    loaded = load_project(path)

    assert loaded.project_metadata["schema"] == "map-reconstruction-project-v3"
    assert loaded.state.preparation == preparation
