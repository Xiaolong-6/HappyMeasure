from __future__ import annotations

from pathlib import Path

from keith_ivt.data.exporters import result_metadata
from keith_ivt.models import SweepConfig, SweepMode, SweepPoint, SweepResult


def make_result() -> SweepResult:
    cfg = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=-1,
        stop=1,
        step=1,
        compliance=0.01,
        nplc=0.1,
        device_name="schema_device",
        operator="operator",
        debug=True,
        debug_model="Linear resistor 10 kΩ",
    )
    return SweepResult(config=cfg, points=[
        SweepPoint(source_value=-1, measured_value=-1e-3, timestamp="2026-05-16T12:00:00", elapsed_s=0.0),
        SweepPoint(source_value=0, measured_value=0.0, timestamp="2026-05-16T12:00:01", elapsed_s=1.0),
    ])


def test_result_metadata_contains_trace_schema_contract_keys() -> None:
    metadata = result_metadata(make_result())
    required = {
        "schema", "exported_at", "start_time", "device_name", "operator",
        "mode", "sweep_kind", "start", "stop", "step", "compliance", "nplc",
        "port", "baud_rate", "terminal", "sense_mode", "debug", "debug_model",
        "output_off_after_run", "point_count", "constant_value", "duration_s",
        "continuous_time", "interval_s", "autorange", "auto_source_range",
        "auto_measure_range", "source_range", "measure_range", "adaptive_logic",
        "data_fingerprint", "config_fingerprint", "trace_uid",
    }
    assert required.issubset(metadata.keys())
    assert metadata["schema"] == "HappyMeasure CSV v2"
    assert metadata["point_count"] == 2
    assert metadata["trace_uid"] == f"{metadata['config_fingerprint']}-{metadata['data_fingerprint']}"


def test_trace_schema_document_mentions_export_visibility_semantics() -> None:
    doc = Path("docs/TRACE_SCHEMA.md").read_text(encoding="utf-8")
    assert "HappyMeasure CSV v2" in doc
    assert "Export all" in doc
    assert "Export visible" in doc
    assert "hidden" in doc
