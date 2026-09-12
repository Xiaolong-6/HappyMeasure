from __future__ import annotations

from keith_ivt.data.exporters import result_metadata
from keith_ivt.models import SweepConfig, SweepKind, SweepMode, SweepPoint, SweepResult
from keith_ivt.ui.export_naming import suggested_all_csv_name, suggested_single_csv_name


def _result(name="Device_A", operator="XL", y_scale=1.0):
    cfg = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0.0,
        stop=0.2,
        step=0.1,
        compliance=0.01,
        nplc=1.0,
        device_name=name,
        operator=operator,
        sweep_kind=SweepKind.STEP,
    )
    points = [
        SweepPoint(0.0, 0.0),
        SweepPoint(0.1, 1e-5 * y_scale),
        SweepPoint(0.2, 2e-5 * y_scale),
    ]
    return SweepResult(cfg, points)


def _kind_result(kind: SweepKind, *, points: int = 3) -> SweepResult:
    cfg = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0.0,
        stop=0.2,
        step=0.1,
        compliance=0.01,
        device_name="Device_A",
        sweep_kind=kind,
        constant_value=0.1,
    )
    return SweepResult(cfg, [SweepPoint(float(i), float(i)) for i in range(points)])


def test_metadata_fingerprint_distinguishes_same_name_different_data() -> None:
    first = result_metadata(_result(y_scale=1.0))
    second = result_metadata(_result(y_scale=2.0))

    assert first["device_name"] == second["device_name"]
    assert first["operator"] == "XL"
    assert first["data_fingerprint"] != second["data_fingerprint"]
    assert first["trace_uid"] != second["trace_uid"]


def test_single_and_combined_export_names_are_compact_and_informative() -> None:
    result = _result("Long Device Name With Spaces", "XL")
    single = suggested_single_csv_name(result)
    combined = suggested_all_csv_name([result, _result("D2", "YL", 2.0)])

    assert single.startswith("HM_") and single.endswith(".csv")
    assert "op-XL" in single
    assert "Vsrc" in single
    assert "step" in single
    assert len(single) <= 96
    assert "all-2" in combined and "Vsrc" in combined and len(combined) <= 96


def test_selected_export_name_does_not_duplicate_underscore_rich_device_name() -> None:
    name = suggested_single_csv_name(_result("Ge45o_5mm_ind_y1_x"))
    assert "Ge45o_5mm_ind_y1_x_5mm_ind_y1_x" not in name
    assert name.endswith(".csv")


def test_time_and_adaptive_names_do_not_repeat_kind_or_point_count() -> None:
    time_name = suggested_single_csv_name(_kind_result(SweepKind.CONSTANT_TIME, points=7))
    adaptive_name = suggested_single_csv_name(_kind_result(SweepKind.ADAPTIVE, points=7))

    assert "time_time" not in time_name
    assert "adapt_adapt" not in adaptive_name
    assert time_name.count("7pts") == 1
    assert adaptive_name.count("7pts") == 1


def test_export_name_sanitizes_long_renamed_trace_tokens() -> None:
    name = suggested_single_csv_name(_result("renamed trace_with-hyphens and spaces" * 4))
    assert "renamed-trace_with" in name
    assert len(name) <= 96
    assert name.endswith(".csv")
