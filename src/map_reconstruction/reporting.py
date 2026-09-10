"""Headless summaries and optional Qt PDF reports for Map Reconstruction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from map_reconstruction.display_units import (
    DisplayUnit,
    display_unit_for_signal,
    scientific_unit_for_signal,
)
from map_reconstruction.models import ReconstructionResult, TimeSeriesData, WindowMode
from map_reconstruction.processing import (
    BaselineMode,
    ColorRangeMode,
    MapProcessingConfig,
    NormalizationMode,
    ProcessedMap,
    ValueScale,
    ValueTransform,
    compute_color_limits,
)
from map_reconstruction.project_io import ProjectState
from map_reconstruction.preparation import DarkCorrectionMode


@dataclass(frozen=True, slots=True)
class ReportMap:
    """The one scientific map chosen for a report figure."""

    values: np.ndarray
    title: str
    display_unit: DisplayUnit
    processing_note: str | None
    color_limits: tuple[float, float]
    flip_y: bool


def _format_value(value: float, unit: str) -> str:
    return f"{value:.6g}" + (f" {unit}" if unit else "")


def _format_duration(value_s: float) -> str:
    """Format a timing value compactly without claiming false precision."""

    if abs(value_s) < 0.1:
        return f"{value_s * 1_000.0:.1f} ms"
    return f"{value_s:.4f} s"


def _format_phase(fraction: float, period_s: float | None) -> str:
    """Format a canonical phase fraction with its optional physical offset."""

    percent = f"{fraction * 100.0:.1f} %"
    return percent if period_s is None else f"{percent} ({_format_duration(fraction * period_s)})"


def _raw_processing_unit(state: ProjectState) -> str:
    """Return the source SI unit for values applied before transformation."""

    return scientific_unit_for_signal(state.signal)


def processing_value_unit(state: ProjectState) -> str:
    """Return a safe unit for the final processed/color-value domain."""

    config = state.processing
    if (
        config.transform is ValueTransform.CUSTOM
        or config.normalization is not NormalizationMode.NONE
        or config.value_scale is ValueScale.LOG10
    ):
        return ""
    return _raw_processing_unit(state)


def normalization_reference_unit(state: ProjectState) -> str:
    """Return the unit of an explicit normalization reference, when physical."""

    if state.processing.transform is ValueTransform.CUSTOM:
        return ""
    return _raw_processing_unit(state)


def _processing_lines(state: ProjectState) -> list[str]:
    """Format only active processing controls with scientifically safe units."""

    config = state.processing
    value_names = {
        ValueTransform.RAW: "Raw signed",
        ValueTransform.ABSOLUTE: "Absolute value",
        ValueTransform.NEGATE: "Negate",
        ValueTransform.CUSTOM: "Custom expression",
    }
    lines = [f"Value: {value_names[config.transform]}"]

    baseline_names = {
        BaselineMode.NONE: "None",
        BaselineMode.MANUAL: "Manual",
        BaselineMode.MEAN: "Mean",
        BaselineMode.MEDIAN: "Median",
        BaselineMode.MINIMUM: "Minimum",
        BaselineMode.MAXIMUM: "Maximum",
        BaselineMode.PERCENTILE: "Percentile",
    }
    lines.append(f"Baseline: {baseline_names[config.baseline_mode]}")
    if config.baseline_mode is BaselineMode.MANUAL and config.baseline_value is not None:
        lines.append(
            "Baseline value: " + _format_value(config.baseline_value, _raw_processing_unit(state))
        )
    elif config.baseline_mode is BaselineMode.PERCENTILE:
        lines.append(f"Baseline percentile: {config.baseline_percentile:.6g}%")

    normalization_names = {
        NormalizationMode.NONE: "None",
        NormalizationMode.MAX_MAGNITUDE: "Max magnitude",
        NormalizationMode.MIN_MAX: "Min-max",
        NormalizationMode.REFERENCE: "Reference",
    }
    lines.append(f"Normalization: {normalization_names[config.normalization]}")
    if (
        config.normalization is NormalizationMode.REFERENCE
        and config.normalization_reference is not None
    ):
        lines.append(
            "Normalization reference: "
            + _format_value(config.normalization_reference, normalization_reference_unit(state))
        )

    lines.append("Scale: " + ("Linear" if config.value_scale is ValueScale.LINEAR else "Log10"))
    color_names = {
        ColorRangeMode.AUTO: "Auto data range",
        ColorRangeMode.PERCENTILE: "Percentile",
        ColorRangeMode.MANUAL: "Manual",
    }
    lines.append(f"Color limits: {color_names[config.color_range_mode]}")
    if config.color_range_mode is ColorRangeMode.PERCENTILE:
        lines.append(f"Low percentile: {config.percentile_low:.6g}%")
        lines.append(f"High percentile: {config.percentile_high:.6g}%")
    elif config.color_range_mode is ColorRangeMode.MANUAL:
        unit = processing_value_unit(state)
        if config.color_min is not None:
            lines.append("Color minimum: " + _format_value(config.color_min, unit))
        if config.color_max is not None:
            lines.append("Color maximum: " + _format_value(config.color_max, unit))
    if config.transform is ValueTransform.CUSTOM:
        lines.append(f"f(x): {config.custom_expression}")
    return lines


def select_report_map(
    state: ProjectState, result: ReconstructionResult, processed: ProcessedMap | None
) -> ReportMap:
    """Choose the actual map displayed in a report without consulting Qt state."""

    raw_unit = display_unit_for_signal(state.signal, result.values)
    if processed is not None and np.isfinite(processed.values).any():
        unit = (
            DisplayUnit(processed.value_label, "", 1.0)
            if processed.is_dimensionless
            else DisplayUnit(processed.value_label, raw_unit.unit, raw_unit.scale)
        )
        limits = compute_color_limits(processed.values, state.processing)
        if limits is None:  # guarded by the finite-value check above
            raise ValueError("Processed report map has no finite values.")
        return ReportMap(
            processed.values,
            "Processed map",
            unit,
            None,
            (limits.minimum, limits.maximum),
            state.flip_y,
        )
    if processed is None:
        note = "Processed map unavailable; raw reconstruction shown."
    else:
        note = "No finite processed values; raw reconstruction shown."
    raw_limits = compute_color_limits(result.values, MapProcessingConfig())
    if raw_limits is None:
        raise ValueError("Raw report map has no finite values.")
    return ReportMap(
        result.values,
        "Raw reconstructed map",
        raw_unit,
        note,
        (raw_limits.minimum, raw_limits.maximum),
        state.flip_y,
    )


def report_display_arrays(
    report_map: ReportMap, result: ReconstructionResult
) -> tuple[np.ndarray, np.ndarray]:
    """Return display-oriented report arrays without mutating authoritative data."""

    if report_map.flip_y:
        return np.flipud(report_map.values), np.flipud(result.sample_counts)
    return report_map.values, result.sample_counts


def fit_size_keep_aspect(
    source_width: int, source_height: int, target_width: int, target_height: int
) -> tuple[int, int]:
    """Return the largest integer size that fits a target without distortion."""

    if min(source_width, source_height, target_width, target_height) <= 0:
        raise ValueError("Source and target dimensions must be positive.")
    scale = min(target_width / source_width, target_height / source_height)
    return max(1, round(source_width * scale)), max(1, round(source_height * scale))


def format_parameter_summary(
    state: ProjectState,
    data: TimeSeriesData | None = None,
    result: ReconstructionResult | None = None,
    processed: ProcessedMap | None = None,
) -> str:
    """Return a portable, human-readable summary without local-path data."""

    row_period = "—"
    point_period = "—"
    row_slack = "—"
    valid = "—"
    median_samples = "—"
    warnings: list[str] = []
    if result is not None:
        row_period = f"{result.timing.row_period_s:.4f} s"
        point_period = f"{result.timing.point_period_s:.4f} s"
        row_slack = (
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
    legacy = state.method == "dual_offset"
    registration = [
        "Registration",
        "------------",
        f"Method: {'Dual Offset (Legacy)' if legacy else 'Dual Offset — Phase Window'}",
        f"YA: {state.row_a_s:.3f} s",
        f"YB: {state.row_b_s:.3f} s",
        f"Rows apart: {state.rows_apart}",
        f"Row period: {row_period}",
        f"Row offset: {state.row_offset}",
    ]
    if legacy:
        registration.extend(
            (
                f"XA: {state.point_a_s:.3f} s",
                f"XB: {state.point_b_s:.3f} s",
                f"Points apart: {state.points_apart}",
                f"Point period: {point_period}",
                f"Point offset: {state.point_offset}",
                f"Unused / row: {row_slack}",
            )
        )
    else:
        timing = result.timing if result is not None else None
        registration.extend(
            (
                f"Y phase: {_format_phase(state.y_phase_fraction, timing.row_period_s if timing else None)}",
                f"XA: {state.point_a_s:.3f} s",
                f"XB: {state.point_b_s:.3f} s",
                f"Points apart: {state.points_apart}",
                f"Point period: {point_period}",
                f"X offset: {state.x_period_offset}",
                f"X phase: {_format_phase(state.x_phase_fraction, timing.point_period_s if timing else None)}",
                "Window mode: "
                + (
                    "Fraction of point period"
                    if state.window_mode is WindowMode.FRACTION
                    else "Fixed duration"
                ),
                "Window width: "
                + (
                    _format_phase(state.window_fraction, timing.point_period_s if timing else None)
                    if state.window_mode is WindowMode.FRACTION
                    else _format_duration(state.window_duration_s or 0.0)
                ),
                f"Aggregation: {state.aggregation.capitalize()}",
                f"Point-train slack / row: {row_slack}",
            )
        )
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
        "Signal Preparation",
        "------------------",
        f"Mode: {state.preparation.dark_correction_mode.value.replace('_', ' ').title()}",
        f"Output convention: {state.preparation.output_convention.value.replace('_', ' ').title()}",
        *(
            [
                f"Constant baseline: {_format_value(state.preparation.constant_baseline, scientific_unit_for_signal(state.signal))}"
            ]
            if state.preparation.dark_correction_mode is DarkCorrectionMode.CONSTANT
            else []
        ),
        *(
            [
                f"Manual regions: {len(state.preparation.manual_dark_regions)}",
                f"Manual fit: {state.preparation.manual_region_fit.value.title()}",
            ]
            if state.preparation.dark_correction_mode is DarkCorrectionMode.MANUAL_REGIONS
            else []
        ),
        *(
            [
                f"Response direction: {state.preparation.response_direction.value.title()} photocurrent",
                f"Quantile: {state.preparation.rolling_quantile * 100.0:.1f} %",
                f"Window: {state.preparation.rolling_window_s:.4g} s",
                f"Trend: {state.preparation.rolling_trend.value.replace('_', ' ').title()}",
            ]
            if state.preparation.dark_correction_mode is DarkCorrectionMode.ROLLING_QUANTILE
            else []
        ),
        "",
        "Geometry",
        "--------",
        f"Rows × columns: {geometry}",
        f"Scan pattern: {state.scan_pattern.value.replace('_', ' ').capitalize()}",
        f"First row: {'L -> R' if state.first_row_ltr else 'R -> L'}",
        f"Aggregation: {state.aggregation.capitalize()}",
        f"Flip Y display: {'Yes' if state.flip_y else 'No'}",
        "",
        *registration,
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
        lines.extend(["", "Processed map unavailable; raw reconstruction retained."])
    elif result is not None and processed is not None and not np.isfinite(processed.values).any():
        lines.extend(["", "No finite processed values; raw reconstruction retained."])
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


def _fit_rect_keep_aspect(target: Any, source_width: int, source_height: int) -> Any:
    """Center an aspect-preserving rectangle inside a Qt target rectangle."""

    from PySide6 import QtCore  # type: ignore[import-not-found]

    width, height = fit_size_keep_aspect(
        source_width, source_height, target.width(), target.height()
    )
    return QtCore.QRect(
        target.x() + (target.width() - width) // 2,
        target.y() + (target.height() - height) // 2,
        width,
        height,
    )


def _render_widget(widget: Any, width: int, height: int) -> Any:
    """Render a plot widget into a letterboxed print-resolution QImage."""

    from PySide6 import QtCore, QtGui  # type: ignore[import-not-found]

    image = QtGui.QImage(width, height, QtGui.QImage.Format.Format_RGB32)
    image.fill(QtCore.Qt.GlobalColor.white)
    painter = QtGui.QPainter(image)
    source_size = widget.size()
    if source_size.width() > 0 and source_size.height() > 0:
        target = _fit_rect_keep_aspect(
            QtCore.QRect(0, 0, width, height), source_size.width(), source_size.height()
        )
        painter.translate(target.x(), target.y())
        painter.scale(target.width() / source_size.width(), target.height() / source_size.height())
    widget.render(painter)
    painter.end()
    return image


def _array_image(values: np.ndarray, colors: np.ndarray, limits: tuple[float, float]) -> Any:
    """Create a report-only QImage from scientific map values without mutation."""

    from PySide6 import QtGui  # type: ignore[import-not-found]

    array = np.asarray(values, dtype=float)
    if array.ndim != 2:
        raise ValueError("Report map values must be two-dimensional.")
    finite = np.isfinite(array)
    rgba = np.full((*array.shape, 4), (238, 238, 238, 255), dtype=np.uint8)
    low, high = limits
    if not np.isfinite(low) or not np.isfinite(high) or low >= high:
        raise ValueError("Report color limits must be finite and increasing.")
    if np.any(finite):
        finite_values = array[finite]
        normalized = (finite_values - low) / (high - low)
        positions = np.clip(normalized, 0.0, 1.0) * (len(colors) - 1)
        lower = np.floor(positions).astype(int)
        upper = np.minimum(lower + 1, len(colors) - 1)
        blend = (positions - lower)[:, np.newaxis]
        rgb = colors[lower] * (1.0 - blend) + colors[upper] * blend
        rgba[finite, :3] = rgb.astype(np.uint8)
    height, width = array.shape
    return QtGui.QImage(
        rgba.data, width, height, rgba.strides[0], QtGui.QImage.Format.Format_RGBA8888
    ).copy()


def _draw_array_figure(
    painter: Any,
    target: Any,
    title: str,
    values: np.ndarray,
    colors: np.ndarray,
    limits: tuple[float, float],
) -> None:
    from PySide6 import QtCore, QtGui  # type: ignore[import-not-found]

    painter.setFont(QtGui.QFont("Segoe UI", 8))
    painter.drawText(target.left(), target.top() + 12, title)
    plot_target = QtCore.QRect(
        target.left(), target.top() + 18, target.width(), target.height() - 22
    )
    image = _array_image(values, colors, limits)
    fitted = _fit_rect_keep_aspect(plot_target, image.width(), image.height())
    painter.setPen(QtGui.QColor("#9CA3AF"))
    painter.drawRect(fitted)
    painter.drawImage(fitted, image)


def generate_pdf_report(
    path: str | Path,
    state: ProjectState,
    data: TimeSeriesData,
    result: ReconstructionResult,
    processed: ProcessedMap | None,
    *,
    count_widget: Any,
    trace_widget: Any,
) -> None:
    """Create a two-page A4 landscape scientific report using existing Qt only."""

    from PySide6 import QtCore, QtGui  # type: ignore[import-not-found]

    report_map = select_report_map(state, result, processed)
    map_values, count_values = report_display_arrays(report_map, result)
    count_limit_values = compute_color_limits(count_values, MapProcessingConfig())
    if count_limit_values is None:
        raise ValueError("Sample-count report figure has no finite values.")
    count_limits = (count_limit_values.minimum, count_limit_values.maximum)
    layout = QtGui.QPageLayout(
        QtGui.QPageSize(QtGui.QPageSize.PageSizeId.A4),
        QtGui.QPageLayout.Orientation.Landscape,
        QtCore.QMarginsF(12, 12, 12, 12),
    )
    printable = layout.paintRectPixels(150)
    page = QtCore.QRect(0, 0, printable.width(), printable.height())
    first_page = QtGui.QImage(page.size(), QtGui.QImage.Format.Format_RGB32)
    first_page.fill(QtCore.Qt.GlobalColor.white)
    painter = QtGui.QPainter(first_page)
    painter.setPen(QtGui.QColor("#14213D"))
    title_font = QtGui.QFont("Segoe UI", 15)
    title_font.setBold(True)
    body_font = QtGui.QFont("Segoe UI", 8)
    painter.setFont(title_font)
    painter.drawText(page.left(), page.top() + 22, "Map Reconstruction Report")
    painter.setFont(body_font)
    generated = datetime.now(UTC).strftime("Generated %Y-%m-%d %H:%M UTC")
    summary_lines = (
        generated + "\n\n" + format_parameter_summary(state, data, result, processed)
    ).splitlines()
    y = page.top() + 42
    for line in summary_lines:
        painter.drawText(page.left(), y, line)
        y += 14
    painter.end()

    figures_page = QtGui.QImage(page.size(), QtGui.QImage.Format.Format_RGB32)
    figures_page.fill(QtCore.Qt.GlobalColor.white)
    painter = QtGui.QPainter(figures_page)
    painter.setPen(QtGui.QColor("#14213D"))
    painter.setFont(title_font)
    painter.drawText(page.left(), page.top() + 22, "Figures")
    if report_map.processing_note:
        painter.setFont(body_font)
        painter.drawText(page.left(), page.top() + 38, report_map.processing_note)
    top = page.top() + 48
    gap = 18
    half_width = (page.width() - gap) // 2
    top_height = (page.height() - 88) // 2
    map_target = QtCore.QRect(page.left(), top, half_width, top_height)
    count_target = QtCore.QRect(page.left() + half_width + gap, top, half_width, top_height)
    trace_target = QtCore.QRect(page.left(), top + top_height + 20, page.width(), top_height)
    map_colors = np.asarray(
        [(18, 44, 90), (29, 101, 185), (32, 164, 166), (200, 216, 77), (247, 232, 90)],
        dtype=float,
    )
    count_colors = np.asarray(
        [(239, 246, 255), (191, 219, 254), (96, 165, 250), (37, 99, 235), (23, 62, 140)],
        dtype=float,
    )
    _draw_array_figure(
        painter,
        map_target,
        f"{report_map.title}: {report_map.display_unit.axis_label}",
        map_values,
        map_colors,
        report_map.color_limits,
    )
    _draw_array_figure(
        painter, count_target, "Samples / pixel", count_values, count_colors, count_limits
    )
    painter.setFont(body_font)
    painter.drawText(trace_target.left(), trace_target.top() + 12, "Raw time trace with anchors")
    trace_image = _render_widget(trace_widget, trace_target.width(), trace_target.height() - 18)
    painter.drawImage(
        QtCore.QRect(
            trace_target.left(),
            trace_target.top() + 18,
            trace_target.width(),
            trace_target.height() - 18,
        ),
        trace_image,
    )
    painter.end()
    writer = QtGui.QPdfWriter(str(path))
    writer.setResolution(150)
    writer.setPageLayout(layout)
    pdf_painter = QtGui.QPainter(writer)
    if not pdf_painter.isActive():
        raise ValueError("Could not create PDF report.")
    pdf_painter.drawImage(printable, first_page)
    writer.newPage()
    pdf_painter.drawImage(printable, figures_page)
    pdf_painter.end()
