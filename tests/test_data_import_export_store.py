from __future__ import annotations

from pathlib import Path

from keith_ivt.data.dataset_store import DatasetStore
from keith_ivt.data.exporters import save_combined_csv, save_csv
from keith_ivt.data.importers import load_csv
from keith_ivt.models import SweepConfig, SweepMode, SweepPoint, SweepResult


def make_result(name: str, scale: float = 1.0) -> SweepResult:
    cfg = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=-1.0,
        stop=1.0,
        step=1.0,
        compliance=0.01,
        device_name=name,
        debug=True,
    )
    pts = [SweepPoint(-1.0, -scale, elapsed_s=0.0), SweepPoint(0.0, 0.0, elapsed_s=0.1), SweepPoint(1.0, scale, elapsed_s=0.2)]
    return SweepResult(cfg, pts)


def test_dataset_store_unique_names_rename_visibility_color() -> None:
    store = DatasetStore()
    a = store.add_result(make_result("dev"), "dev")
    b = store.add_result(make_result("dev"), "dev")
    assert a.name == "dev"
    assert b.name == "dev_2"
    store.rename(b.trace_id, "dev")
    assert store.get(b.trace_id).name == "dev_2"
    store.toggle_visibility(a.trace_id)
    assert store.get(a.trace_id).visible is False
    store.set_color(a.trace_id, "#abcdef")
    assert store.get(a.trace_id).color == "#abcdef"
    store.remove(a.trace_id)
    assert store.get(a.trace_id) is None
    store.clear()
    assert store.all() == []


def test_single_csv_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "single.csv"
    save_csv(make_result("round"), path)
    loaded = load_csv(path)
    assert len(loaded) == 1
    assert loaded[0].config.device_name == "round"
    assert [p.source_value for p in loaded[0].points] == [-1.0, 0.0, 1.0]
    assert loaded[0].points[-1].measured_value == 1.0


def test_combined_csv_wide_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "combined.csv"
    save_combined_csv([make_result("a", 1.0), make_result("b", 2.0)], path)
    loaded = load_csv(path)
    assert len(loaded) == 2
    assert {r.config.device_name for r in loaded} == {"a", "b"}
    assert loaded[1].points[-1].source_value == 1.0


def test_combined_csv_rejects_empty(tmp_path: Path) -> None:
    try:
        save_combined_csv([], tmp_path / "empty.csv")
    except ValueError as exc:
        assert "No sweep results" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_import_metadata_preserves_false_booleans_and_ranges(tmp_path: Path) -> None:
    cfg = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0.0,
        stop=1.0,
        step=1.0,
        compliance=0.02,
        nplc=0.5,
        device_name="meta_bool",
        debug=False,
        autorange=False,
        auto_source_range=False,
        auto_measure_range=False,
        source_range=2.0,
        measure_range=0.01,
    )
    result = SweepResult(cfg, [SweepPoint(0.0, 0.0), SweepPoint(1.0, 1e-3)])
    path = tmp_path / "meta_bool.csv"
    save_csv(result, path)

    loaded = load_csv(path)[0].config

    assert loaded.debug is False
    assert loaded.autorange is False
    assert loaded.auto_source_range is False
    assert loaded.auto_measure_range is False
    assert loaded.source_range == 2.0
    assert loaded.measure_range == 0.01
    assert loaded.compliance == 0.02
    assert loaded.nplc == 0.5


def test_single_csv_round_trip_preserves_time_sweep_metadata(tmp_path: Path) -> None:
    from keith_ivt.models import SweepKind

    cfg = SweepConfig(
        mode=SweepMode.CURRENT_SOURCE,
        start=5e-6,
        stop=5e-6,
        step=0.0,
        compliance=5.0,
        device_name="time_trace",
        operator="XL",
        debug=True,
        sweep_kind=SweepKind.CONSTANT_TIME,
        constant_value=5e-6,
        duration_s=3.0,
        continuous_time=True,
        interval_s=0.25,
        output_off_after_run=False,
        debug_model="Diode",
    )
    result = SweepResult(
        cfg,
        [
            SweepPoint(5e-6, 0.10, elapsed_s=0.0),
            SweepPoint(5e-6, 0.11, elapsed_s=0.25),
        ],
    )
    path = tmp_path / "time_trace.csv"
    save_csv(result, path)

    loaded = load_csv(path)[0]

    assert loaded.config.mode is SweepMode.CURRENT_SOURCE
    assert loaded.config.sweep_kind is SweepKind.CONSTANT_TIME
    assert loaded.config.constant_value == 5e-6
    assert loaded.config.duration_s == 3.0
    assert loaded.config.continuous_time is True
    assert loaded.config.interval_s == 0.25
    assert loaded.config.output_off_after_run is False
    assert loaded.config.debug_model == "Diode"
    assert [p.elapsed_s for p in loaded.points] == [0.0, 0.25]


def test_combined_long_round_trip_preserves_metadata_when_axes_differ(tmp_path: Path) -> None:
    from keith_ivt.models import SweepKind

    a = make_result("same_axis", 1.0)
    cfg_b = SweepConfig(
        mode=SweepMode.CURRENT_SOURCE,
        start=1e-6,
        stop=3e-6,
        step=2e-6,
        compliance=3.0,
        nplc=0.25,
        device_name="current_device",
        operator="operator_b",
        debug=False,
        sweep_kind=SweepKind.STEP,
        autorange=False,
        auto_source_range=False,
        source_range=1e-5,
        auto_measure_range=False,
        measure_range=10.0,
    )
    b = SweepResult(
        cfg_b,
        [SweepPoint(1e-6, 0.2, elapsed_s=0.0), SweepPoint(3e-6, 0.4, elapsed_s=0.5)],
    )
    path = tmp_path / "long.csv"
    save_combined_csv([a, b], path)

    loaded = load_csv(path)
    loaded_b = next(result for result in loaded if result.config.device_name == "current_device")

    assert loaded_b.config.mode is SweepMode.CURRENT_SOURCE
    assert loaded_b.config.operator == "operator_b"
    assert loaded_b.config.autorange is False
    assert loaded_b.config.auto_source_range is False
    assert loaded_b.config.auto_measure_range is False
    assert loaded_b.config.source_range == 1e-5
    assert loaded_b.config.measure_range == 10.0
    assert loaded_b.config.nplc == 0.25
    assert [p.source_value for p in loaded_b.points] == [1e-6, 3e-6]
