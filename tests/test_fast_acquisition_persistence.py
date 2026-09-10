from __future__ import annotations

from keith_ivt.data.exporters import result_metadata, save_csv
from keith_ivt.data.importers import load_csv
from keith_ivt.models import SweepConfig, SweepKind, SweepMode, SweepPoint, SweepResult


def _result() -> SweepResult:
    config = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0.0,
        stop=0.0,
        step=1.0,
        compliance=1e-3,
        nplc=0.1,
        delay_s=0.0,
        sweep_kind=SweepKind.CONSTANT_TIME,
        constant_value=0.25,
        duration_s=1.0,
        interval_s=0.5,
        auto_source_range=False,
        auto_measure_range=False,
        source_range=20.0,
        measure_range=1e-3,
        fast_acquisition=True,
        zero_refresh_before_run=True,
        autozero_during_run=False,
        digital_filter=False,
        concurrent_measurement=False,
        display_during_run=True,
        measurement_only_read=True,
        range_telemetry=False,
        source_write_each_sample=False,
        trigger_delay_s=0.0,
    )
    return SweepResult(
        config=config,
        points=[SweepPoint(0.25, -4.2e-4, elapsed_s=0.015)],
    )


def test_fast_acquisition_profile_is_in_result_metadata() -> None:
    metadata = result_metadata(_result())
    assert metadata["fast_acquisition"] is True
    assert metadata["custom_acquisition"] is False
    assert metadata["zero_refresh_before_run"] is True
    assert metadata["autozero_during_run"] is False
    assert metadata["measurement_only_read"] is True
    assert metadata["range_telemetry"] is False
    assert metadata["trigger_delay_s"] == 0.0


def test_fast_acquisition_profile_round_trips_through_single_csv(tmp_path) -> None:
    path = save_csv(_result(), tmp_path / "fast.csv")
    loaded = load_csv(path)[0]
    config = loaded.config
    assert config.fast_acquisition is True
    assert config.custom_acquisition is False
    assert config.zero_refresh_before_run is True
    assert config.autozero_during_run is False
    assert config.measurement_only_read is True
    assert config.range_telemetry is False
    assert config.source_write_each_sample is False
    assert config.trigger_delay_s == 0.0
