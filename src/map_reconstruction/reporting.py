"""Headless summaries and optional Qt PDF reports for Map Reconstruction."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from map_reconstruction.models import ReconstructionResult, TimeSeriesData
from map_reconstruction.processing import ProcessedMap
from map_reconstruction.project_io import ProjectState


def _friendly(value: str) -> str:
    return value.replace("_", " ").capitalize()


def _processing_lines(state: ProjectState) -> list[str]:
    config = state.processing
    lines = [f"Value: {_friendly(config.transform.value)}"]
    lines.append(
        "Baseline: "
        + (_friendly(config.baseline_mode.value))
        + (f" ({config.baseline_value:.6g})" if config.baseline_value is not None else "")
    )
    if config.baseline_mode.value == "percentile":
        lines.append(f"Baseline percentile: {config.baseline_percentile:.3g}%")
    lines.append("Normalization: " + _friendly(config.normalization.value))
    if config.normalization_reference is not None:
        lines.append(f"Normalization reference: {config.normalization_reference:.6g}")
    lines.append("Scale: " + _friendly(config.value_scale.value))
    color = _friendly(config.color_range_mode.value)
    if config.color_range_mode.value == "percentile":
        color += f" ({config.percentile_low:.3g} - {config.percentile_high:.3g}%)"
    elif config.color_range_mode.value == "manual":
        color += f" ({config.color_min:.6g} - {config.color_max:.6g})"
    lines.append("Color limits: " + color)
    if config.transform.value == "custom":
        lines.append(f"f(x): {config.custom_expression}")
    return lines


def format_parameter_summary(
    state: ProjectState,
    data: TimeSeriesData | None = None,
    result: ReconstructionResult | None = None,
    processed: ProcessedMap | None = None,
) -> str:
    """Return a portable, human-readable summary without local-path data."""

    row_period = "—"
    point_period = "—"
    unused = "—"
    valid = "—"
    median_samples = "—"
    warnings: list[str] = []
    if result is not None:
        row_period = f"{result.timing.row_period_s:.4f} s"
        point_period = f"{result.timing.point_period_s:.4f} s"
        unused = (
            f"{result.timing.row_period_s - state.columns * result.timing.point_period_s:.3f} s"
        )
        finite = np.isfinite(result.values)
        valid = f"{100.0 * float(np.mean(finite)):.0f} %"
        median_samples = (
            f"{float(np.median(result.sample_counts[finite])):.3g}" if np.any(finite) else "0"
        )
        warnings.extend(result.warnings)
    if processed is not None:
        warnings.extend(processed.warnings)
    sample_count = str(data.sample_count) if data is not None else "—"
    elapsed = f"{data.time_s[0]:.3f} - {data.time_s[-1]:.3f} s" if data is not None else "—"
    geometry = f"{state.rows} × {state.columns}" if state.is_geometry_set else "—"
    lines = [
        "Map Reconstruction Parameters",
        "============================",
        "",
        "Source",
        "------",
        f"File: {state.original_filename}",
        f"Signal: {state.signal}",
        f"Samples: {sample_count}",
        f"Elapsed time: {elapsed}",
        "",
        "Geometry",
        "--------",
        f"Rows × columns: {geometry}",
        f"Scan pattern: {_friendly(state.scan_pattern.value)}",
        f"First row: {'L -> R' if state.first_row_ltr else 'R -> L'}",
        f"Aggregation: {_friendly(state.aggregation)}",
        f"Flip Y display: {'Yes' if state.flip_y else 'No'}",
        "",
        "Registration",
        "------------",
        "Method: Dual Offset",
        f"YA: {state.row_a_s:.3f} s",
        f"YB: {state.row_b_s:.3f} s",
        f"Rows apart: {state.rows_apart}",
        f"Row period: {row_period}",
        f"Row offset: {state.row_offset}",
        f"XA: {state.point_a_s:.3f} s",
        f"XB: {state.point_b_s:.3f} s",
        f"Points apart: {state.points_apart}",
        f"Point period: {point_period}",
        f"Point offset: {state.point_offset}",
        f"Unused / row: {unused}",
        "",
        "Processing",
        "----------",
        *_processing_lines(state),
        "",
        "QC",
        "--",
        f"Valid pixels: {valid}",
        f"Median samples / pixel: {median_samples}",
        "Warnings: " + (" | ".join(warnings) if warnings else "None"),
    ]
    if result is not None and processed is None:
        lines.extend(["", "Processed map: unavailable; raw reconstruction retained."])
    return "\n".join(lines) + "\n"


def write_parameter_summary(
    path: str | Path,
    state: ProjectState,
    data: TimeSeriesData | None = None,
    result: ReconstructionResult | None = None,
    processed: ProcessedMap | None = None,
) -> None:
    Path(path).write_text(
        format_parameter_summary(state, data, result, processed), encoding="utf-8", newline="\n"
    )


def _render_widget(widget: Any, width: int, height: int) -> Any:
    """Render one plot widget into a print-resolution QImage on demand."""

    from PySide6 import QtCore, QtGui  # type: ignore[import-not-found]

    image = QtGui.QImage(width, height, QtGui.QImage.Format.Format_RGB32)
    image.fill(QtCore.Qt.GlobalColor.white)
    painter = QtGui.QPainter(image)
    source_size = widget.size()
    if source_size.width() > 0 and source_size.height() > 0:
        painter.scale(width / source_size.width(), height / source_size.height())
    widget.render(painter)
    painter.end()
    return image


def generate_pdf_report(
    path: str | Path,
    state: ProjectState,
    data: TimeSeriesData,
    result: ReconstructionResult,
    processed: ProcessedMap | None,
    *,
    map_widget: Any,
    count_widget: Any,
    trace_widget: Any,
) -> None:
    """Create a two-page A4 landscape scientific report using existing Qt only."""

    from PySide6 import QtCore, QtGui  # type: ignore[import-not-found]

    writer = QtGui.QPdfWriter(str(path))
    writer.setResolution(150)
    writer.setPageLayout(
        QtGui.QPageLayout(
            QtGui.QPageSize(QtGui.QPageSize.PageSizeId.A4),
            QtGui.QPageLayout.Orientation.Landscape,
            QtCore.QMarginsF(12, 12, 12, 12),
        )
    )
    painter = QtGui.QPainter(writer)
    if not painter.isActive():
        raise ValueError("Could not create PDF report.")
    page = writer.pageLayout().paintRectPixels(writer.resolution())
    painter.setPen(QtGui.QColor("#14213D"))
    title_font = QtGui.QFont("Arial", 15)
    title_font.setBold(True)
    body_font = QtGui.QFont("Arial", 8)
    painter.setFont(title_font)
    painter.drawText(page.left(), page.top() + 22, "Map Reconstruction Report")
    painter.setFont(body_font)
    generated = datetime.now(UTC).strftime("Generated %Y-%m-%d %H:%M UTC")
    summary_lines = (
        generated + "\n\n" + format_parameter_summary(state, data, result, processed)
    ).splitlines()
    y = page.top() + 42
    for line in summary_lines:
        painter.drawText(page.left(), y, line.encode("ascii", "replace").decode("ascii"))
        y += 14
    writer.newPage()
    painter.setFont(title_font)
    painter.drawText(page.left(), page.top() + 22, "Figures")
    labels = (
        ("Reconstructed map" if processed is not None else "Raw reconstruction", map_widget),
        ("Samples / pixel", count_widget),
        ("Raw time trace with anchors", trace_widget),
    )
    figure_top = page.top() + 30
    figure_height = (page.height() - 38) // 3
    for index, (label, widget) in enumerate(labels):
        top = figure_top + index * figure_height
        painter.setFont(body_font)
        painter.drawText(page.left(), top + 12, label.encode("ascii", "replace").decode("ascii"))
        target = QtCore.QRect(page.left(), top + 16, page.width(), figure_height - 22)
        image = _render_widget(widget, target.width(), target.height())
        painter.drawImage(target, image)
    painter.end()
