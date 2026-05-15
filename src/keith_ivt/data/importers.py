from __future__ import annotations

import csv
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from keith_ivt.models import SenseMode, SweepConfig, SweepMode, SweepPoint, SweepResult, Terminal


def _parse_float(text: str) -> float:
    return float(str(text).strip())


def _config_from_metadata(metadata: dict[str, Any], fallback_name: str = "Imported_Device") -> SweepConfig:
    mode_text = str(metadata.get("mode", "VOLT")).upper()
    mode = SweepMode.CURRENT_SOURCE if mode_text == "CURR" else SweepMode.VOLTAGE_SOURCE
    terminal_text = str(metadata.get("terminal", Terminal.REAR.value)).upper()
    sense_text = str(metadata.get("sense_mode", SenseMode.TWO_WIRE.value)).upper()
    return SweepConfig(
        mode=mode,
        start=float(metadata.get("start", 0.0)),
        stop=float(metadata.get("stop", 0.0)),
        step=float(metadata.get("step", 1.0)),
        compliance=float(metadata.get("compliance", 0.0)),
        nplc=float(metadata.get("nplc", 1.0)),
        port=str(metadata.get("port", "")),
        baud_rate=int(metadata.get("baud_rate", 9600)),
        terminal=Terminal.FRONT if terminal_text.startswith("FR") else Terminal.REAR,
        sense_mode=SenseMode.FOUR_WIRE if sense_text.startswith("4") else SenseMode.TWO_WIRE,
        device_name=str(metadata.get("device_name", fallback_name)),
        operator=str(metadata.get("operator", "")),
        debug=bool(metadata.get("debug", False)),
        autorange=bool(metadata.get("autorange", True)),
        auto_source_range=bool(metadata.get("auto_source_range", metadata.get("autorange", True))),
        auto_measure_range=bool(metadata.get("auto_measure_range", metadata.get("autorange", True))),
        source_range=float(metadata.get("source_range", 0.0)),
        measure_range=float(metadata.get("measure_range", 0.0)),
    )


def load_csv(path: str | Path) -> list[SweepResult]:
    """Load either a single-device export or Save-All export.

    Supported formats:
    - single export from save_csv(): metadata JSON + two data columns
    - combined wide export from save_combined_csv(): one source column + device columns
    - combined long export from save_combined_csv(): trace_index/device_name/mode rows
    """
    path = Path(path)
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if not rows:
        raise ValueError("CSV file is empty.")

    metadata: dict[str, Any] = {}
    all_metadata: list[dict[str, Any]] = []
    data_rows: list[list[str]] = []
    header: list[str] | None = None
    combined_format = ""

    current_section = "data"
    for row in rows:
        if not row:
            continue
        first = row[0].strip()
        if first.startswith("#"):
            key = first.lstrip("#").strip()
            if key == "metadata" and len(row) > 1:
                try:
                    metadata = json.loads(row[1])
                except json.JSONDecodeError:
                    metadata = {}
            elif key == "device_metadata" and len(row) > 1:
                try:
                    all_metadata.append(json.loads(row[1]))
                except json.JSONDecodeError:
                    pass
            elif key == "format" and len(row) > 1:
                combined_format = row[1].strip().lower()
            elif key == "section" and len(row) > 1:
                current_section = row[1].strip().lower()
                if current_section == "data":
                    header = None
                    data_rows = []
            continue
        # v2 combined exports include a visible trace_metadata table before the
        # actual numeric data.  It is for humans; import uses the later data
        # section plus # device_metadata comments.
        if current_section not in {"data", ""}:
            continue
        if header is None:
            header = row
        else:
            data_rows.append(row)

    if header is None:
        raise ValueError("CSV file has no data header.")

    # Combined long table.
    if combined_format in {"long", "long-v2"} or header[:5] == ["trace_index", "device_name", "mode", "point_index", "elapsed_s"] or header[:6] == ["trace_index", "device_name", "operator", "mode", "sweep_type", "point_index"]:
        grouped: dict[str, list[SweepPoint]] = {}
        metas: dict[str, dict[str, Any]] = {}
        v2 = header[:6] == ["trace_index", "device_name", "operator", "mode", "sweep_type", "point_index"]
        for row in data_rows:
            if v2:
                if len(row) < 9:
                    continue
                key = f"{row[0]}::{row[1]}"
                grouped.setdefault(key, []).append(SweepPoint(_parse_float(row[7]), _parse_float(row[8]), elapsed_s=_parse_float(row[6])))
                metas[key] = {"device_name": row[1], "operator": row[2], "mode": row[3], "sweep_kind": row[4]}
            else:
                if len(row) < 7:
                    continue
                key = f"{row[0]}::{row[1]}"
                grouped.setdefault(key, []).append(SweepPoint(_parse_float(row[5]), _parse_float(row[6]), elapsed_s=_parse_float(row[4])))
                metas[key] = {"device_name": row[1], "mode": row[2]}
        out: list[SweepResult] = []
        for key, points in grouped.items():
            _, name = key.split("::", 1)
            meta = metas.get(key, {"device_name": name, "mode": "VOLT"})
            # Prefer full comment metadata when trace_index lines are present.
            try:
                trace_idx = int(key.split("::", 1)[0]) - 1
                if 0 <= trace_idx < len(all_metadata):
                    meta = {**all_metadata[trace_idx], **meta}
            except Exception:
                pass
            cfg = _config_from_metadata(meta, fallback_name=name)
            if points:
                cfg = replace(cfg, start=points[0].source_value, stop=points[-1].source_value, step=(points[1].source_value - points[0].source_value if len(points) > 1 else 1.0))
            out.append(SweepResult(cfg, points))
        return out

    # Combined wide table. Single-device exports also have three columns
    # (Elapsed_s + source + measured), so require explicit combined metadata,
    # explicit wide marker, or more than one measured device column.
    if combined_format in {"wide", "wide-v2"} or all_metadata or len(header) > 3:
        has_elapsed = header[0] == "Elapsed_s"
        x_col = 1 if has_elapsed else 0
        first_y_col = 2 if has_elapsed else 1
        x_header = header[x_col]
        mode = SweepMode.CURRENT_SOURCE if "Current" in x_header else SweepMode.VOLTAGE_SOURCE
        axis = [_parse_float(row[x_col]) for row in data_rows if len(row) > x_col]
        elapsed = [_parse_float(row[0]) if has_elapsed and row and str(row[0]).strip() else 0.0 for row in data_rows if len(row) > x_col]
        out = []
        for col_idx, col_name in enumerate(header[first_y_col:], start=first_y_col):
            # v2 labels look like "T001 Device · Operator [Current (A)]".
            device_name = col_name
            if col_name.startswith("T") and " " in col_name:
                device_name = col_name.split(" ", 1)[1]
            if " [" in device_name:
                device_name = device_name.split(" [", 1)[0]
            if " · " in device_name:
                device_name = device_name.split(" · ", 1)[0]
            if "_" in device_name and device_name.startswith(("Current", "Voltage")):
                device_name = device_name.split("_", 2)[-1]
            meta_index = col_idx - first_y_col
            meta = all_metadata[meta_index] if meta_index < len(all_metadata) else {"device_name": device_name, "mode": mode.value}
            cfg = _config_from_metadata(meta, fallback_name=device_name)
            cfg = replace(cfg, mode=mode, device_name=str(meta.get("device_name", device_name)))
            points = []
            for row_idx, (row, x) in enumerate(zip(data_rows, axis)):
                if col_idx < len(row) and str(row[col_idx]).strip() != "":
                    points.append(SweepPoint(x, _parse_float(row[col_idx]), elapsed_s=elapsed[row_idx] if row_idx < len(elapsed) else 0.0))
            if points:
                cfg = replace(cfg, start=points[0].source_value, stop=points[-1].source_value, step=(points[1].source_value - points[0].source_value if len(points) > 1 else 1.0))
            out.append(SweepResult(cfg, points))
        return out

    # Single-device table.
    cfg = _config_from_metadata(metadata, fallback_name=path.stem)
    if header and header[0] == "Elapsed_s":
        points = [SweepPoint(_parse_float(row[1]), _parse_float(row[2]), elapsed_s=_parse_float(row[0])) for row in data_rows if len(row) >= 3]
    else:
        points = [SweepPoint(_parse_float(row[0]), _parse_float(row[1])) for row in data_rows if len(row) >= 2]
    if points:
        cfg = replace(cfg, start=points[0].source_value, stop=points[-1].source_value, step=(points[1].source_value - points[0].source_value if len(points) > 1 else 1.0))
    return [SweepResult(cfg, points)]
