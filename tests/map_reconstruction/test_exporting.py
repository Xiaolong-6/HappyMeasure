from pathlib import Path
from types import SimpleNamespace

from map_reconstruction.display_units import DisplayUnit
from map_reconstruction.processing import MapProcessingConfig, process_map
from map_reconstruction.ui.exporting import export_paths


def test_export_paths_use_one_base_destination() -> None:
    raw, processed, sidecar = export_paths(Path("scan_map.csv"))

    assert raw.name == "scan_map_raw.csv"
    assert processed.name == "scan_map_processed.csv"
    assert sidecar.name == "scan_map_processed.json"


def test_processed_metadata_separates_source_and_display_units() -> None:
    from map_reconstruction.ui.exporting import processed_export_metadata

    processed = process_map(
        [[1e-6, 2e-6]],
        MapProcessingConfig(),
        signal_name="Current_A",
    )
    window = SimpleNamespace(
        processing_config=MapProcessingConfig(),
        signal_combo=SimpleNamespace(currentText=lambda: "Current_A"),
        processed=processed,
        _active_color_limits=(1.0, 2.0),
        _raw_display_unit=lambda: DisplayUnit("Current", "µA", 1e6),
    )

    metadata = processed_export_metadata(window)

    assert metadata["source_physical_unit"] == "A"
    assert metadata["raw_physical_unit"] == "A"
    assert metadata["display_unit"] == "µA"
    assert metadata["display_scale"] == 1e6
