from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

import numpy as np

from map_reconstruction.models import TimeSeriesData


def _row_value(rows: list[list[str]], marker: str) -> list[str] | None:
    for row in rows:
        if row and row[0].strip() == marker:
            return row
    return None


def import_happymeasure_csv(path: str | Path) -> TimeSeriesData:
    """Import a HappyMeasure ``single-v2`` CSV using CSV-aware parsing.

    Metadata JSON is read from its complete CSV field, so commas inside JSON
    strings do not shift the data columns.
    """

    source = Path(path)
    try:
        raw_bytes = source.read_bytes()
    except OSError as exc:
        raise ValueError(f"Could not read CSV file {source}: {exc}") from exc
    return import_happymeasure_csv_bytes(raw_bytes, source.name, source_path=source)


def import_happymeasure_csv_bytes(
    raw_bytes: bytes, source_name: str, *, source_path: Path | None = None
) -> TimeSeriesData:
    """Import exact HappyMeasure CSV bytes without writing a temporary file.

    Project archives use this path so their embedded source remains the
    authoritative byte sequence while parsing follows the normal importer
    contract.
    """

    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Could not decode CSV file {source_name}: {exc}") from exc
    rows = list(csv.reader(io.StringIO(text, newline="")))
    if not rows:
        raise ValueError("CSV file is empty.")

    schema_row = _row_value(rows, "# schema")
    schema = schema_row[1].strip() if schema_row and len(schema_row) > 1 else ""
    if schema == "combined-v2" or schema.startswith("combined-"):
        raise ValueError(
            "Combined HappyMeasure CSV exports are not supported; choose a single-v2 export."
        )
    if schema != "single-v2":
        raise ValueError(
            f"Expected HappyMeasure single-v2 CSV schema, got {schema or 'missing'!r}."
        )

    metadata_row = _row_value(rows, "# metadata")
    metadata: dict[str, Any] = {}
    if metadata_row is not None:
        if len(metadata_row) < 2:
            raise ValueError("HappyMeasure metadata row is missing its JSON field.")
        try:
            parsed = json.loads(metadata_row[1])
        except json.JSONDecodeError as exc:
            raise ValueError(f"HappyMeasure metadata is not valid JSON: {exc.msg}.") from exc
        if not isinstance(parsed, dict):
            raise ValueError("HappyMeasure metadata JSON must be an object.")
        metadata = parsed

    section_index = next(
        (
            index
            for index, row in enumerate(rows)
            if len(row) >= 2 and row[0].strip() == "# section" and row[1].strip() == "data"
        ),
        None,
    )
    if section_index is None:
        raise ValueError("HappyMeasure CSV is missing its '# section,data' row.")

    data_rows = [
        row for row in rows[section_index + 1 :] if row and not row[0].strip().startswith("#")
    ]
    if not data_rows:
        raise ValueError("HappyMeasure CSV data section is empty.")
    header = [cell.strip() for cell in data_rows[0]]
    if len(set(header)) != len(header) or any(not name for name in header):
        raise ValueError("HappyMeasure data header must contain unique non-empty names.")
    if "Elapsed_s" not in header:
        raise ValueError("HappyMeasure data header must contain an 'Elapsed_s' column.")

    time_index = header.index("Elapsed_s")
    rows_data = data_rows[1:]
    if not rows_data:
        raise ValueError("HappyMeasure CSV contains a header but no data rows.")

    expected_width = len(header)
    for row_number, row in enumerate(rows_data, start=section_index + 3):
        if len(row) != expected_width:
            raise ValueError(
                f"HappyMeasure row {row_number} has {len(row)} fields; expected {expected_width}."
            )

    def parse_column(column_index: int, name: str) -> np.ndarray:
        values: list[float] = []
        for row_number, row in enumerate(rows_data, start=section_index + 3):
            raw = row[column_index].strip()
            try:
                value = float(raw)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Column {name!r} has a non-numeric value at row {row_number}: {raw!r}."
                ) from exc
            if not np.isfinite(value):
                raise ValueError(f"Column {name!r} has a non-finite value at row {row_number}.")
            values.append(value)
        return np.asarray(values, dtype=float)

    time_s = parse_column(time_index, "Elapsed_s")
    signals = {
        name: parse_column(index, name) for index, name in enumerate(header) if index != time_index
    }
    order = np.argsort(time_s, kind="stable")
    sorted_time = time_s[order]
    sorted_signals = {name: values[order] for name, values in signals.items()}
    return TimeSeriesData(
        time_s=sorted_time,
        signals=sorted_signals,
        metadata=metadata,
        source_path=source_path,
    )
