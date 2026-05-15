from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

from keith_ivt.models import SweepResult


def _point_fingerprint(result: SweepResult) -> str:
    h = hashlib.sha256()
    for p in result.points:
        h.update(f"{getattr(p, 'elapsed_s', 0.0):.12g},{p.source_value:.12g},{p.measured_value:.12g}\n".encode("utf-8"))
    return h.hexdigest()[:16]


def result_metadata(result: SweepResult) -> dict:
    """Serializable metadata shared by single, combined, and imported files.

    The fingerprint fields intentionally include the numeric data, not only the
    visible device name/start/stop values.  Import-overlap detection uses them
    to avoid treating two different sweeps with the same user-facing metadata as
    the same trace.
    """
    first_timestamp = ""
    if result.points:
        first_timestamp = getattr(result.points[0], "timestamp", "") or ""
    data_fingerprint = _point_fingerprint(result)
    cfg = result.config
    config_fingerprint = hashlib.sha256(json.dumps({
        "device_name": cfg.device_name,
        "operator": cfg.operator,
        "mode": cfg.mode.value,
        "sweep_kind": cfg.sweep_kind.value,
        "start": cfg.start,
        "stop": cfg.stop,
        "step": cfg.step,
        "constant_value": cfg.constant_value,
        "duration_s": cfg.duration_s,
        "interval_s": cfg.interval_s,
        "compliance": cfg.compliance,
        "nplc": cfg.nplc,
        "terminal": cfg.terminal.value,
        "sense_mode": cfg.sense_mode.value,
        "auto_source_range": getattr(cfg, "auto_source_range", cfg.autorange),
        "auto_measure_range": getattr(cfg, "auto_measure_range", cfg.autorange),
        "source_range": cfg.source_range,
        "measure_range": cfg.measure_range,
    }, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return {
        "schema": "HappyMeasure CSV v2",
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "start_time": first_timestamp,
        "device_name": cfg.device_name,
        "operator": cfg.operator,
        "mode": cfg.mode.value,
        "start": cfg.start,
        "stop": cfg.stop,
        "step": cfg.step,
        "compliance": cfg.compliance,
        "nplc": cfg.nplc,
        "port": cfg.port,
        "baud_rate": cfg.baud_rate,
        "terminal": cfg.terminal.value,
        "sense_mode": cfg.sense_mode.value,
        "debug": cfg.debug,
        "point_count": len(result.points),
        "sweep_kind": cfg.sweep_kind.value,
        "constant_value": cfg.constant_value,
        "duration_s": cfg.duration_s,
        "interval_s": cfg.interval_s,
        "autorange": cfg.autorange,
        "auto_source_range": getattr(cfg, "auto_source_range", cfg.autorange),
        "auto_measure_range": getattr(cfg, "auto_measure_range", cfg.autorange),
        "source_range": cfg.source_range,
        "measure_range": cfg.measure_range,
        "adaptive_logic": cfg.adaptive_logic,
        "data_fingerprint": data_fingerprint,
        "config_fingerprint": config_fingerprint,
        "trace_uid": f"{config_fingerprint}-{data_fingerprint}",
    }


def save_csv(result: SweepResult, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    x_header, y_header = result.config.csv_headers
    metadata = result_metadata(result)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["# HappyMeasure measurement export"])
        writer.writerow(["# schema", "single-v2"])
        writer.writerow(["# metadata", json.dumps(metadata, ensure_ascii=False)])
        writer.writerow(["# section", "data"])
        writer.writerow(["Elapsed_s", x_header, y_header])
        for point in result.points:
            writer.writerow([f"{getattr(point, 'elapsed_s', 0.0):.12g}", f"{point.source_value:.12g}", f"{point.measured_value:.12g}"])
    return path


def _write_trace_metadata_table(writer: csv.writer, results: list[SweepResult]) -> None:
    writer.writerow(["# section", "trace_metadata"])
    writer.writerow([
        "trace_index", "device_name", "operator", "mode", "sweep_type", "points",
        "start", "stop", "step", "compliance", "nplc", "source_range", "measure_range",
        "auto_source_range", "auto_measure_range", "data_fingerprint", "trace_uid",
    ])
    for index, result in enumerate(results, start=1):
        m = result_metadata(result)
        writer.writerow([
            index,
            m["device_name"],
            m.get("operator", ""),
            m["mode"],
            m["sweep_kind"],
            m["point_count"],
            m["start"],
            m["stop"],
            m["step"],
            m["compliance"],
            m["nplc"],
            m["source_range"],
            m["measure_range"],
            m["auto_source_range"],
            m["auto_measure_range"],
            m["data_fingerprint"],
            m["trace_uid"],
        ])


def save_combined_csv(results: Iterable[SweepResult], path: str | Path) -> Path:
    """Save multiple device traces in a human-readable CSV.

    The file starts with an explicit trace metadata table, then a data section.
    If all traces share a source axis and source mode, the data section is wide
    (one measured column per trace).  Otherwise it falls back to a long table.
    Both variants keep machine-readable ``# device_metadata`` lines for robust
    import while staying understandable in Excel/Origin.
    """
    results = list(results)
    if not results:
        raise ValueError("No sweep results to save.")

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    first = results[0]
    same_mode = all(r.config.mode == first.config.mode for r in results)
    first_axis = [p.source_value for p in first.points]
    same_axis = all([p.source_value for p in r.points] == first_axis for r in results)
    table_format = "wide-v2" if same_mode and same_axis else "long-v2"

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["# HappyMeasure combined device export"])
        writer.writerow(["# schema", "combined-v2"])
        writer.writerow(["# created_at", datetime.now().isoformat(timespec="seconds")])
        writer.writerow(["# format", table_format])
        writer.writerow(["# trace_count", len(results)])
        for index, result in enumerate(results, start=1):
            metadata = result_metadata(result)
            metadata["trace_index"] = index
            writer.writerow(["# device_metadata", json.dumps(metadata, ensure_ascii=False)])

        _write_trace_metadata_table(writer, results)

        writer.writerow(["# section", "data"])
        if same_mode and same_axis:
            x_header, y_header = first.config.csv_headers
            labels = []
            for i, r in enumerate(results, start=1):
                name = r.config.device_name or f"Device_{i}"
                op = f" · {r.config.operator}" if r.config.operator else ""
                labels.append(f"T{i:03d} {name}{op} [{y_header}]")
            writer.writerow(["Elapsed_s", x_header] + labels)
            for row_idx, x in enumerate(first_axis):
                p0 = first.points[row_idx]
                row = [f"{getattr(p0, 'elapsed_s', 0.0):.12g}", f"{x:.12g}"]
                for result in results:
                    row.append(f"{result.points[row_idx].measured_value:.12g}")
                writer.writerow(row)
        else:
            writer.writerow(["trace_index", "device_name", "operator", "mode", "sweep_type", "point_index", "elapsed_s", "source_value", "measured_value"])
            for trace_idx, result in enumerate(results, start=1):
                for point_idx, point in enumerate(result.points, start=1):
                    writer.writerow([
                        trace_idx,
                        result.config.device_name,
                        result.config.operator,
                        result.config.mode.value,
                        result.config.sweep_kind.value,
                        point_idx,
                        f"{getattr(point, 'elapsed_s', 0.0):.12g}",
                        f"{point.source_value:.12g}",
                        f"{point.measured_value:.12g}",
                    ])
    return path
