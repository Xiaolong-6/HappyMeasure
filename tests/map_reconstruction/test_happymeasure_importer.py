from __future__ import annotations

import csv
import json

import numpy as np
import pytest

from map_reconstruction.importers.happymeasure import import_happymeasure_csv


def write_single(path, *, schema="single-v2", rows=None, metadata=None, header=None):
    rows = rows or [[0.2, 2.0, -2e-9], [0.0, 0.0, -1e-9]]
    metadata = metadata or {"device_name": "sample, with comma", "mode": "VOLT"}
    header = header or ["Elapsed_s", "Voltage_V", "Current_A"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["# HappyMeasure measurement export"])
        writer.writerow(["# schema", schema])
        writer.writerow(["# metadata", json.dumps(metadata)])
        writer.writerow(["# section", "data"])
        writer.writerow(header)
        writer.writerows(rows)


def test_importer_parses_quoted_metadata_and_sorts_time(tmp_path):
    path = tmp_path / "single.csv"
    write_single(path)

    data = import_happymeasure_csv(path)

    assert data.source_path == path
    assert data.metadata["device_name"] == "sample, with comma"
    assert set(data.signal_names) == {
        "Voltage_V",
        "Current_A",
    }
    np.testing.assert_allclose(data.time_s, [0.0, 0.2])
    np.testing.assert_allclose(data.signals["Current_A"], [-1e-9, -2e-9])


def test_importer_preserves_closely_spaced_elapsed_timestamps(tmp_path):
    path = tmp_path / "high_resolution_elapsed.csv"
    elapsed = [0.031000000027, 0.031000900031, 0.031001800042]
    write_single(
        path, rows=[[time_s, 0.0, current] for time_s, current in zip(elapsed, (1e-9, 2e-9, 3e-9))]
    )

    data = import_happymeasure_csv(path)

    np.testing.assert_allclose(data.time_s, elapsed, rtol=0.0, atol=0.0)
    assert np.all(np.diff(data.time_s) > 0.0)


def test_importer_rejects_combined_schema(tmp_path):
    path = tmp_path / "combined.csv"
    write_single(path, schema="combined-v2")

    with pytest.raises(ValueError, match="Combined HappyMeasure"):
        import_happymeasure_csv(path)


def test_importer_requires_elapsed_header(tmp_path):
    path = tmp_path / "bad.csv"
    write_single(path, header=["Time", "Current_A"], rows=[[0.0, 1e-9]])

    with pytest.raises(ValueError, match="Elapsed_s"):
        import_happymeasure_csv(path)


def test_importer_rejects_ragged_or_nonfinite_data(tmp_path):
    ragged = tmp_path / "ragged.csv"
    write_single(ragged, rows=[[0.0, 1.0], [0.1, 2.0, 3.0]])
    with pytest.raises(ValueError, match="fields"):
        import_happymeasure_csv(ragged)

    nonfinite = tmp_path / "nonfinite.csv"
    write_single(nonfinite, rows=[[0.0, "nan", 1e-9]])
    with pytest.raises(ValueError, match="non-finite"):
        import_happymeasure_csv(nonfinite)


@pytest.mark.parametrize(
    "content, message",
    [
        ("", "empty"),
        ("# schema,wrong-v2\n", "single-v2"),
        ("# schema,single-v2\n# metadata,{bad}\n# section,data\nElapsed_s,x\n0,1\n", "valid JSON"),
        ("# schema,single-v2\n# metadata,[]\n# section,data\nElapsed_s,x\n0,1\n", "object"),
        ("# schema,single-v2\nElapsed_s,x\n0,1\n", "section,data"),
        ("# schema,single-v2\n# section,data\n", "empty"),
        ("# schema,single-v2\n# section,data\nElapsed_s,x\n", "no data rows"),
        ("# schema,single-v2\n# section,data\nElapsed_s,x,x\n0,1,2\n", "unique"),
        ("# schema,single-v2\n# section,data\nElapsed_s,x\n0,bad\n", "non-numeric"),
    ],
)
def test_importer_reports_structural_errors(tmp_path, content, message):
    path = tmp_path / "invalid.csv"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        import_happymeasure_csv(path)


def test_importer_reports_missing_file(tmp_path):
    with pytest.raises(ValueError, match="Could not read"):
        import_happymeasure_csv(tmp_path / "missing.csv")
