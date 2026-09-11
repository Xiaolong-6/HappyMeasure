"""Focused export workflow helpers for Map Reconstruction."""

from __future__ import annotations

import base64
import html
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

import numpy as np
from PySide6 import QtCore, QtWidgets  # type: ignore[import-not-found]

from map_reconstruction.display_units import scientific_unit_for_signal
from map_reconstruction.project_io import save_project
from map_reconstruction.reporting import format_parameter_summary, write_parameter_summary


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


def export_prepared(window: Any) -> None:
    """Export raw, baseline, and prepared time traces without changing source data."""

    if window.data is None or window.prepared is None:
        QtWidgets.QMessageBox.information(
            window, "No prepared signal", "Prepare a source signal first."
        )
        return
    default = f"{_source_stem(window)}_prepared.csv"
    path, _ = QtWidgets.QFileDialog.getSaveFileName(
        window, "Export prepared time-series", default, "CSV files (*.csv);;All files (*.*)"
    )
    if not path:
        return
    columns = [
        window.prepared.time_s,
        window.data.signals[window.prepared.source_signal],
        window.prepared.values,
    ]
    header = [
        "Elapsed_s",
        f"Raw_{window.prepared.source_signal}",
        f"Prepared_{window.prepared.source_signal}",
    ]
    if window.prepared.baseline is not None:
        columns.insert(2, window.prepared.baseline)
        header.insert(2, f"Baseline_{window.prepared.source_signal}")
    try:
        np.savetxt(
            path,
            np.column_stack(columns),
            delimiter=",",
            header=",".join(header),
            comments="",
            fmt="%.12g",
        )
    except OSError as exc:
        QtWidgets.QMessageBox.critical(window, "Export failed", str(exc))
        return
    window.statusBar().showMessage(f"Exported prepared trace to {path}")


def processed_export_metadata(window: Any) -> dict[str, object]:
    """Build a reproducible sidecar for preparation, reconstruction output, and display."""

    config = window.processing_config
    payload = {
        key: (value.value if hasattr(value, "value") else value)
        for key, value in asdict(config).items()
    }
    display = window._raw_display_unit()
    source_unit = scientific_unit_for_signal(window.signal_combo.currentText())
    preparation = window.preparation_config.to_dict()
    return {
        "source_signal": window.signal_combo.currentText(),
        "source_physical_unit": source_unit,
        "raw_physical_unit": source_unit,
        "display_unit": display.unit,
        "display_scale": display.scale,
        "signal_preparation": preparation,
        "prepared_metadata": dict(window.prepared.metadata) if window.prepared is not None else {},
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


def export_project(window: Any) -> bool:
    if window.data is None or not window._raw_source_bytes:
        QtWidgets.QMessageBox.information(window, "No source data", "Open a source CSV first.")
        return False
    path, _ = QtWidgets.QFileDialog.getSaveFileName(
        window,
        "Export Map Reconstruction project",
        f"{_source_stem(window)}.hmmap",
        "Map Reconstruction Project (*.hmmap)",
    )
    if not path:
        return False
    try:
        save_project(Path(path), window._project_state(), window._raw_source_bytes)
    except (OSError, ValueError) as exc:
        QtWidgets.QMessageBox.critical(window, "Project export failed", str(exc))
        return False
    window.statusBar().showMessage(f"Exported project to {path}")
    return True


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


def _widget_png_data_uri(widget: QtWidgets.QWidget) -> str:
    """Return a widget snapshot as an inline PNG suitable for an HTML report."""

    pixmap = widget.grab()
    if pixmap.isNull():
        raise ValueError("The report figure could not be rendered.")
    buffer = QtCore.QBuffer()
    if not buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly):
        raise OSError("Could not create the report image buffer.")
    try:
        if not pixmap.save(buffer, "PNG"):
            raise OSError("Could not encode a report figure as PNG.")
        encoded = base64.b64encode(cast(bytes, buffer.data())).decode("ascii")
    finally:
        buffer.close()
    return f"data:image/png;base64,{encoded}"


def _html_figure(title: str, data_uri: str, description: str) -> str:
    """Format one accessible, self-contained report figure."""

    return "\n".join(
        (
            "<figure>",
            f'<img src="{data_uri}" alt="{html.escape(description)}">',
            f"<figcaption>{html.escape(title)}</figcaption>",
            "</figure>",
        )
    )


def export_html_report(window: Any) -> None:
    """Export a portable report with the current scientific views and settings."""

    if window.data is None or window.result is None:
        QtWidgets.QMessageBox.information(
            window,
            "No reconstruction",
            "Reconstruct a valid raw map before exporting an HTML report.",
        )
        return
    path, _ = QtWidgets.QFileDialog.getSaveFileName(
        window,
        "Export HTML reconstruction report",
        f"{_source_stem(window)}_map_report.html",
        "HTML files (*.html)",
    )
    if not path:
        return
    try:
        state = window._project_state()
        summary = format_parameter_summary(state, window.data, window.result, window.processed)
        previous_trace = window.trace_view.trace_source_combo.currentText()
        try:
            # The report labels this panel as raw time trace. Force Raw only for
            # rendering, then restore the operator's on-screen selection.
            window.trace_view.trace_source_combo.setCurrentText("Raw")
            window.trace_view._refresh_trace_curve()
            figures = "\n".join(
                (
                    _html_figure(
                        "Reconstructed map",
                        _widget_png_data_uri(window.analysis_map_views.map_plot),
                        "Current reconstructed map",
                    ),
                    _html_figure(
                        "Samples per pixel",
                        _widget_png_data_uri(window.analysis_map_views.count_plot),
                        "Current sample-count map",
                    ),
                    _html_figure(
                        "Raw time trace",
                        _widget_png_data_uri(window.raw_plot),
                        "Raw source time trace",
                    ),
                )
            )
        finally:
            window.trace_view.trace_source_combo.setCurrentText(previous_trace)
            window.trace_view._refresh_trace_curve()
        document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Map Reconstruction Report</title>
<style>
body {{ max-width: 1180px; margin: 2rem auto; padding: 0 1rem; color: #172033; background: #fff; font: 16px/1.45 system-ui, sans-serif; }}
h1 {{ margin-bottom: .2rem; }}
.note {{ color: #4b5563; }}
pre {{ overflow-x: auto; padding: 1rem; border: 1px solid #d1d5db; border-radius: 6px; background: #f8fafc; white-space: pre-wrap; }}
.figures {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 1.25rem; }}
figure {{ margin: 0; padding: .75rem; border: 1px solid #d1d5db; border-radius: 6px; background: #fff; }}
img {{ display: block; width: 100%; height: auto; }}
figcaption {{ margin-top: .5rem; font-weight: 600; }}
</style>
</head>
<body>
<h1>Map Reconstruction Report</h1>
<p class="note">Self-contained HTML export. The figures show the current Analysis display; the raw trace is rendered as Raw for this report only.</p>
<h2>Reproducibility and QC summary</h2>
<pre>{html.escape(summary)}</pre>
<h2>Current views</h2>
<section class="figures">{figures}</section>
</body>
</html>
"""
        destination = Path(path)
        if not destination.suffix:
            destination = destination.with_suffix(".html")
        destination.write_text(document, encoding="utf-8", newline="\n")
    except (OSError, ValueError) as exc:
        QtWidgets.QMessageBox.critical(window, "HTML export failed", str(exc))
        return
    window.statusBar().showMessage(f"Exported HTML report to {destination}")
