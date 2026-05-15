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
