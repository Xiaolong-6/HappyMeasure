"""Focused export workflow helpers for Map Reconstruction."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
from PySide6 import QtWidgets  # type: ignore[import-not-found]

from map_reconstruction.display_units import scientific_unit_for_signal
from map_reconstruction.project_io import save_project
from map_reconstruction.reporting import generate_pdf_report, write_parameter_summary


def export_paths(base_path: Path) -> tuple[Path, Path, Path]:
    """Return raw CSV, processed CSV, and processed JSON paths for one base choice."""

    stem = base_path.stem
    if stem.endswith("_map"):
        stem = stem[:-4]
    return (
        base_path.parent / f"{stem}_map_raw.csv",
        base_path.parent / f"{stem}_map_processed.csv",
        base_path.parent / f"{stem}_map_processed.json",
    )


def export_raw(window: Any) -> None:
    if window.result is None or window.data is None:
        QtWidgets.QMessageBox.information(
            window, "No map", "Load a CSV and reconstruct a map first."
        )
        return
    default = f"{window.data.source_path.stem if window.data.source_path else 'map'}_map_raw.csv"
    path, _ = QtWidgets.QFileDialog.getSaveFileName(
        window, "Export raw reconstructed map", default, "CSV files (*.csv);;All files (*.*)"
    )
    if not path:
        return
    try:
        np.savetxt(path, window.result.values, delimiter=",", fmt="%.12g")
    except OSError as exc:
        QtWidgets.QMessageBox.critical(window, "Export failed", str(exc))
        return
    window.statusBar().showMessage(f"Exported raw map to {path}")


def processed_export_metadata(window: Any) -> dict[str, object]:
    """Build the sidecar without conflating source and display units."""

    config = window.processing_config
    payload = {
        key: (value.value if hasattr(value, "value") else value)
        for key, value in asdict(config).items()
    }
    display = window._raw_display_unit()
    source_unit = scientific_unit_for_signal(window.signal_combo.currentText())
    return {
        "source_signal": window.signal_combo.currentText(),
        "source_physical_unit": source_unit,
        "raw_physical_unit": source_unit,
        "display_unit": display.unit,
        "display_scale": display.scale,
        "baseline_used_si": window.processed.baseline_used if window.processed else None,
        "processing": payload,
        "processing_warnings": list(window.processed.warnings) if window.processed else [],
        "value_label": window.processed.value_label if window.processed else "",
        "dimensionless": bool(window.processed.is_dimensionless) if window.processed else False,
        "display_color_limits": window._active_color_limits,
    }


def export_processed(window: Any) -> None:
    if (
        window.data is None
        or window.processed is None
        or not np.isfinite(window.processed.values).any()
    ):
        QtWidgets.QMessageBox.information(
            window, "No processed map", "Apply valid processing settings first."
        )
        return
    default = (
        f"{window.data.source_path.stem if window.data.source_path else 'map'}_map_processed.csv"
    )
    path, _ = QtWidgets.QFileDialog.getSaveFileName(
        window, "Export processed map", default, "CSV files (*.csv);;All files (*.*)"
    )
    if not path:
        return
    try:
        np.savetxt(path, window.processed.values, delimiter=",", fmt="%.12g")
        Path(path).with_suffix(".json").write_text(
            json.dumps(processed_export_metadata(window), indent=2), encoding="utf-8"
        )
    except (OSError, TypeError, ValueError) as exc:
        QtWidgets.QMessageBox.critical(window, "Export failed", str(exc))
        return
    window.statusBar().showMessage(f"Exported processed map to {path}")


def export_both(window: Any) -> None:
    if (
        window.result is None
        or window.data is None
        or window.processed is None
        or not np.isfinite(window.processed.values).any()
    ):
        QtWidgets.QMessageBox.information(
            window, "No map", "Apply valid processing settings before exporting both maps."
        )
        return
    default = f"{window.data.source_path.stem if window.data.source_path else 'map'}_map.csv"
    base, _ = QtWidgets.QFileDialog.getSaveFileName(
        window, "Choose base name for map exports", default, "CSV files (*.csv);;All files (*.*)"
    )
    if not base:
        return
    raw_path, processed_path, sidecar_path = export_paths(Path(base))
    existing = [path for path in (raw_path, processed_path, sidecar_path) if path.exists()]
    if existing:
        answer = QtWidgets.QMessageBox.question(
            window,
            "Overwrite existing exports?",
            "Files already exist:\n" + "\n".join(path.name for path in existing),
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )
        if answer is not QtWidgets.QMessageBox.StandardButton.Yes:
            return
    try:
        np.savetxt(raw_path, window.result.values, delimiter=",", fmt="%.12g")
        np.savetxt(processed_path, window.processed.values, delimiter=",", fmt="%.12g")
        sidecar_path.write_text(
            json.dumps(processed_export_metadata(window), indent=2), encoding="utf-8"
        )
    except (OSError, TypeError, ValueError) as exc:
        QtWidgets.QMessageBox.critical(window, "Export failed", str(exc))
        return
    window.statusBar().showMessage(f"Exported raw and processed maps to {raw_path.parent}")


def _source_stem(window: Any) -> str:
    return Path(window._loaded_filename or "map").stem


def export_project(window: Any) -> None:
    if window.data is None or not window._raw_source_bytes:
        QtWidgets.QMessageBox.information(window, "No source data", "Open a source CSV first.")
        return
    path, _ = QtWidgets.QFileDialog.getSaveFileName(
        window,
        "Export Map Reconstruction project",
        f"{_source_stem(window)}.hmmap",
        "Map Reconstruction Project (*.hmmap)",
    )
    if not path:
        return
    try:
        save_project(Path(path), window._project_state(), window._raw_source_bytes)
    except (OSError, ValueError) as exc:
        QtWidgets.QMessageBox.critical(window, "Project export failed", str(exc))
        return
    window.statusBar().showMessage(f"Exported project to {path}")


def export_parameter_summary(window: Any) -> None:
    if window.data is None:
        QtWidgets.QMessageBox.information(window, "No source data", "Open a source CSV first.")
        return
    path, _ = QtWidgets.QFileDialog.getSaveFileName(
        window,
        "Export parameter summary",
        f"{_source_stem(window)}_map_parameters.txt",
        "Text files (*.txt)",
    )
    if not path:
        return
    try:
        write_parameter_summary(
            Path(path), window._project_state(), window.data, window.result, window.processed
        )
    except (OSError, ValueError) as exc:
        QtWidgets.QMessageBox.critical(window, "Summary export failed", str(exc))
        return
    window.statusBar().showMessage(f"Exported parameter summary to {path}")


def export_pdf_report(window: Any) -> None:
    if window.data is None or window.result is None:
        QtWidgets.QMessageBox.information(
            window,
            "No reconstruction",
            "Reconstruct a valid raw map before exporting a PDF report.",
        )
        return
    path, _ = QtWidgets.QFileDialog.getSaveFileName(
        window,
        "Export PDF reconstruction report",
        f"{_source_stem(window)}_map_report.pdf",
        "PDF files (*.pdf)",
    )
    if not path:
        return
    try:
        generate_pdf_report(
            Path(path),
            window._project_state(),
            window.data,
            window.result,
            window.processed,
            count_widget=window.count_plot,
            trace_widget=window.raw_plot,
        )
    except (OSError, ValueError) as exc:
        QtWidgets.QMessageBox.critical(window, "PDF export failed", str(exc))
        return
    window.statusBar().showMessage(f"Exported PDF report to {path}")
