from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from map_reconstruction.models import ScanPattern
from map_reconstruction.processing import (
    BaselineMode,
    ColorRangeMode,
    MapProcessingConfig,
    NormalizationMode,
    ValueScale,
    ValueTransform,
)
from map_reconstruction.project_io import (
    PROJECT_JSON_PATH,
    PROJECT_SCHEMA,
    RAW_CSV_PATH,
    ProjectState,
    load_project,
    save_project,
)
from map_reconstruction.reporting import format_parameter_summary


def _raw_csv() -> bytes:
    return (
        b"# schema,single-v2\r\n"
        b'# metadata,"{"operator": "test"}"\r\n'
        b"# section,data\r\n"
        b"Elapsed_s,Current_A,Voltage_V\r\n"
        b"0,1e-6,0.1\r\n"
        b"0.1,2e-6,0.2\r\n"
        b"0.2,3e-6,0.3\r\n"
    )


def _state(*, geometry: bool = True, custom: bool = False) -> ProjectState:
    processing = MapProcessingConfig(
        baseline_mode=BaselineMode.MANUAL,
        baseline_value=2.5e-6,
        baseline_percentile=42.0,
        transform=ValueTransform.CUSTOM if custom else ValueTransform.ABSOLUTE,
        custom_expression="abs(x) * 2" if custom else "x",
        normalization=NormalizationMode.REFERENCE,
        normalization_reference=4e-6,
        value_scale=ValueScale.LINEAR,
        color_range_mode=ColorRangeMode.PERCENTILE,
        color_min=None,
        color_max=None,
        percentile_low=5.0,
        percentile_high=95.0,
    )
    return ProjectState(
        original_filename="measurement.csv",
        signal="Current_A",
        rows=3 if geometry else 0,
        columns=4 if geometry else 0,
        scan_pattern=ScanPattern.SERPENTINE,
        first_row_ltr=False,
        aggregation="median",
        row_a_s=0.010123456,
        row_b_s=0.110123456,
        rows_apart=2,
        row_offset=1 if geometry else 0,
        point_a_s=0.020123456,
        point_b_s=0.050123456,
        points_apart=3,
        point_offset=2 if geometry else 0,
        processing=processing,
        flip_y=True,
    )


def _write_project(path: Path, payload: dict[str, object], raw: bytes) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(PROJECT_JSON_PATH, json.dumps(payload))
        archive.writestr(RAW_CSV_PATH, raw)


def test_project_archive_has_schema_and_preserves_raw_csv_bytes(tmp_path: Path) -> None:
    raw = _raw_csv()
    project = tmp_path / "saved.hmmap"
    save_project(project, _state(), raw)

    with zipfile.ZipFile(project) as archive:
        assert set(archive.namelist()) == {PROJECT_JSON_PATH, RAW_CSV_PATH}
        assert archive.read(RAW_CSV_PATH) == raw
        payload = json.loads(archive.read(PROJECT_JSON_PATH))
    assert payload["schema"] == PROJECT_SCHEMA
    assert payload["source"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert payload["source"]["original_filename"] == "measurement.csv"
    assert "C:" not in json.dumps(payload)


def test_project_round_trip_restores_scientific_state_and_processing(tmp_path: Path) -> None:
    project = tmp_path / "round_trip.hmmap"
    state = _state(custom=True)
    save_project(project, state, _raw_csv())

    loaded = load_project(project)

    assert loaded.state == state
    assert loaded.raw_csv_bytes == _raw_csv()
    assert loaded.state.processing.custom_expression == "abs(x) * 2"
    assert loaded.state.processing.baseline_value == pytest.approx(2.5e-6)
    assert loaded.state.processing.normalization_reference == pytest.approx(4e-6)


def test_partial_project_with_unset_geometry_is_valid(tmp_path: Path) -> None:
    project = tmp_path / "partial.hmmap"
    save_project(project, _state(geometry=False), _raw_csv())

    loaded = load_project(project)

    assert not loaded.state.is_geometry_set
    assert (loaded.state.rows, loaded.state.columns) == (0, 0)


def test_corrupted_embedded_raw_data_is_rejected(tmp_path: Path) -> None:
    project = tmp_path / "corrupt.hmmap"
    save_project(project, _state(), _raw_csv())
    with zipfile.ZipFile(project) as archive:
        payload = json.loads(archive.read(PROJECT_JSON_PATH))
    _write_project(project, payload, b"corrupted raw data")

    with pytest.raises(ValueError, match="Embedded raw data failed SHA-256 verification"):
        load_project(project)


def test_unsupported_schema_is_rejected(tmp_path: Path) -> None:
    project = tmp_path / "future.hmmap"
    raw = _raw_csv()
    state = _state()
    payload = state.to_project_dict(
        raw_sha256=hashlib.sha256(raw).hexdigest(), application_version="test"
    )
    payload["schema"] = "map-reconstruction-project-v999"
    _write_project(project, payload, raw)

    with pytest.raises(ValueError, match="Unsupported Map Reconstruction project schema"):
        load_project(project)


@pytest.mark.parametrize(
    ("payload", "raw", "message"),
    [
        ({}, b"", "missing project.json"),
        ({PROJECT_JSON_PATH: b"{}"}, b"", "missing embedded raw data"),
    ],
)
def test_project_missing_required_members_is_rejected(
    tmp_path: Path, payload: dict[str, bytes], raw: bytes, message: str
) -> None:
    project = tmp_path / "missing.hmmap"
    with zipfile.ZipFile(project, "w") as archive:
        for name, contents in payload.items():
            archive.writestr(name, contents)
        if raw:
            archive.writestr(RAW_CSV_PATH, raw)
    with pytest.raises(ValueError, match=message):
        load_project(project)


def test_malformed_project_fields_are_rejected_without_key_errors(tmp_path: Path) -> None:
    raw = _raw_csv()
    payload = _state().to_project_dict(
        raw_sha256=hashlib.sha256(raw).hexdigest(), application_version="test"
    )
    payload["registration"]["row_a_s"] = "not-a-number"  # type: ignore[index]
    project = tmp_path / "invalid.hmmap"
    _write_project(project, payload, raw)

    with pytest.raises(ValueError, match="registration.row_a_s"):
        load_project(project)


def test_malformed_json_and_invalid_processing_or_geometry_are_rejected(tmp_path: Path) -> None:
    raw = _raw_csv()
    malformed = tmp_path / "malformed.hmmap"
    with zipfile.ZipFile(malformed, "w") as archive:
        archive.writestr(PROJECT_JSON_PATH, b"{")
        archive.writestr(RAW_CSV_PATH, raw)
    with pytest.raises(ValueError, match="metadata is not valid JSON"):
        load_project(malformed)

    payload = _state().to_project_dict(
        raw_sha256=hashlib.sha256(raw).hexdigest(), application_version="test"
    )
    payload["processing"]["transform"] = "not-a-transform"  # type: ignore[index]
    invalid_processing = tmp_path / "invalid_processing.hmmap"
    _write_project(invalid_processing, payload, raw)
    with pytest.raises(ValueError, match="Invalid project processing configuration"):
        load_project(invalid_processing)

    payload["processing"]["transform"] = "absolute"  # type: ignore[index]
    payload["geometry"]["rows"] = -1  # type: ignore[index]
    invalid_geometry = tmp_path / "invalid_geometry.hmmap"
    _write_project(invalid_geometry, payload, raw)
    with pytest.raises(ValueError, match="geometry.rows"):
        load_project(invalid_geometry)


def test_parameter_summary_uses_compact_anchor_names_and_partial_placeholders() -> None:
    summary = format_parameter_summary(_state(geometry=False))

    assert "YA: 0.010 s" in summary
    assert "YB: 0.110 s" in summary
    assert "XA: 0.020 s" in summary
    assert "XB: 0.050 s" in summary
    assert "Row period: —" in summary
    assert "Point period: —" in summary
    assert "C:\\Users" not in summary
