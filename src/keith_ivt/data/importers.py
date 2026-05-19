from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from keith_ivt.models import SenseMode, SweepConfig, SweepKind, SweepMode, SweepPoint, SweepResult, Terminal


def _float_or_default(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _int_or_default(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _bool_or_default(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _sweep_mode_from_text(value: Any) -> SweepMode:
    text = str(value or SweepMode.VOLTAGE_SOURCE.value).strip().upper()
    if text.startswith("CUR") or text.startswith("I"):
        return SweepMode.CURRENT_SOURCE
    return SweepMode.VOLTAGE_SOURCE


def _sweep_kind_from_text(value: Any) -> SweepKind:
    text = str(value or SweepKind.STEP.value).strip().upper()
    if text in {"TIME", "CONSTANT_TIME"}:
        return SweepKind.CONSTANT_TIME
    if text == "ADAPTIVE":
        return SweepKind.ADAPTIVE
    if text == "MANUAL_OUTPUT":
        return SweepKind.MANUAL_OUTPUT
    return SweepKind.STEP


def _terminal_from_text(value: Any) -> Terminal:
    text = str(value or Terminal.REAR.value).strip().upper()
    return Terminal.FRONT if text.startswith("FR") else Terminal.REAR


def _sense_mode_from_text(value: Any) -> SenseMode:
    text = str(value or SenseMode.TWO_WIRE.value).strip().upper()
    return SenseMode.FOUR_WIRE if text.startswith("4") or text.startswith("FOUR") else SenseMode.TWO_WIRE


def _inferred_step(points: list[SweepPoint]) -> float:
    if len(points) < 2:
        return 1.0
    return points[1].source_value - points[0].source_value


def _config_from_metadata(metadata: dict[str, Any], fallback_name: str = "Imported_Device") -> SweepConfig:
    mode = _sweep_mode_from_text(metadata.get("mode", "VOLT"))
    autorange = _bool_or_default(metadata.get("autorange"), True)
    return SweepConfig(
        mode=mode,
        start=_float_or_default(metadata.get("start"), 0.0),
        stop=_float_or_default(metadata.get("stop"), 0.0),
        step=_float_or_default(metadata.get("step"), 1.0),
        compliance=_float_or_default(metadata.get("compliance"), 0.0),
        nplc=_float_or_default(metadata.get("nplc"), 1.0),
        delay_s=_float_or_default(metadata.get("delay_s"), 0.0),
        port=str(metadata.get("port") or ""),
        baud_rate=_int_or_default(metadata.get("baud_rate"), 9600),
        terminal=_terminal_from_text(metadata.get("terminal")),
        sense_mode=_sense_mode_from_text(metadata.get("sense_mode")),
        device_name=str(metadata.get("device_name") or fallback_name),
        operator=str(metadata.get("operator") or ""),
        debug=_bool_or_default(metadata.get("debug"), False),
        output_off_after_run=_bool_or_default(metadata.get("output_off_after_run"), True),
        sweep_kind=_sweep_kind_from_text(metadata.get("sweep_kind")),
        hysteresis=_bool_or_default(metadata.get("hysteresis"), False),
        constant_value=_float_or_default(metadata.get("constant_value"), 0.0),
        duration_s=_float_or_default(metadata.get("duration_s"), 10.0),
        continuous_time=_bool_or_default(metadata.get("continuous_time"), False),
        interval_s=_float_or_default(metadata.get("interval_s"), 0.5),
        autorange=autorange,
        auto_source_range=_bool_or_default(metadata.get("auto_source_range"), autorange),
        auto_measure_range=_bool_or_default(metadata.get("auto_measure_range"), autorange),
        source_range=_float_or_default(metadata.get("source_range"), 0.0),
        measure_range=_float_or_default(metadata.get("measure_range"), 0.0),
        adaptive_logic=str(metadata.get("adaptive_logic") or "values = logspace(1e-3, 1, 31)"),
        debug_model=str(metadata.get("debug_model") or "Linear resistor 10 kΩ"),
    )


def _parse_metadata_rows(rows: list[list[str]]) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    metadata: dict[str, Any] = {}
    all_metadata: list[dict[str, Any]] = []
    combined_format = ""
    for row in rows:
        if not row:
            continue
        first = row[0].strip()
        if not first.startswith("#"):
            continue
        key = first.lstrip("#").strip()
        if key == "metadata" and len(row) > 1:
            try:
                metadata = json.loads(row[1])
            except Exception:
                metadata = {}
        elif key == "device_metadata" and len(row) > 1:
            try:
                all_metadata.append(json.loads(row[1]))
            except Exception:
                pass
        elif key == "format" and len(row) > 1:
            combined_format = row[1]
    return metadata, all_metadata, combined_format


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

    metadata, all_metadata, combined_format = _parse_metadata_rows(rows)
    data_rows: list[list[str]] = []
    header: list[str] | None = None
    current_section = "data"
    for row in rows:
        if not row:
            continue
        first = row[0].strip()
        if first.startswith("#"):
            key = first.lstrip("#").strip()
            if key == "section" and len(row) > 1:
                current_section = row[1].strip()
            continue
        if current_section != "data":
            continue
        if header is None:
            header = row
        else:
            data_rows.append(row)

    if header is None:
        raise ValueError("CSV data section is missing.")

    if combined_format == "wide-v2" or (len(header) >= 3 and header[0] == "Elapsed_s"):
        results: list[SweepResult] = []
        source_values = [_float_or_default(r[1], 0.0) for r in data_rows if len(r) >= 2]
        for col in range(2, len(header)):
            trace_meta = all_metadata[col - 2] if col - 2 < len(all_metadata) else {}
            cfg = _config_from_metadata(trace_meta, fallback_name=header[col].split("[")[0].strip() or f"Imported_{col-1}")
            points = []
            for row in data_rows:
                if len(row) <= col:
                    continue
                elapsed = _float_or_default(row[0], 0.0)
                points.append(SweepPoint(source_value=_float_or_default(row[1], 0.0), measured_value=_float_or_default(row[col], 0.0), elapsed_s=elapsed))
            if points:
                if not trace_meta:
                    cfg = SweepConfig(
                        mode=cfg.mode,
                        start=source_values[0],
                        stop=source_values[-1],
                        step=_inferred_step(points),
                        compliance=cfg.compliance,
                        device_name=cfg.device_name,
                    )
                results.append(SweepResult(config=cfg, points=points))
        return results

    if combined_format == "long-v2" or (header and header[0] == "trace_index"):
        grouped: dict[int, list[SweepPoint]] = {}
        names: dict[int, str] = {}
        meta_by_index = {int(m.get("trace_index", i + 1)): m for i, m in enumerate(all_metadata)}
        for row in data_rows:
            if len(row) < 9:
                continue
            idx = _int_or_default(row[0], 1)
            names[idx] = row[1]
            grouped.setdefault(idx, []).append(SweepPoint(source_value=_float_or_default(row[7], 0.0), measured_value=_float_or_default(row[8], 0.0), elapsed_s=_float_or_default(row[6], 0.0)))
        results = []
        for idx, points in sorted(grouped.items()):
            cfg = _config_from_metadata(meta_by_index.get(idx, {}), fallback_name=names.get(idx, f"Imported_{idx}"))
            results.append(SweepResult(config=cfg, points=points))
        return results

    x_col = 1 if len(header) >= 3 and header[0] == "Elapsed_s" else 0
    y_col = 2 if len(header) >= 3 and header[0] == "Elapsed_s" else 1
    points = []
    for row in data_rows:
        if len(row) <= y_col:
            continue
        points.append(SweepPoint(source_value=_float_or_default(row[x_col], 0.0), measured_value=_float_or_default(row[y_col], 0.0), elapsed_s=_float_or_default(row[0], 0.0) if x_col == 1 else 0.0))
    cfg = _config_from_metadata(metadata)
    if points and not metadata:
        cfg = SweepConfig(mode=cfg.mode, start=points[0].source_value, stop=points[-1].source_value, step=_inferred_step(points), compliance=cfg.compliance, device_name=path.stem)
    return [SweepResult(config=cfg, points=points)]
