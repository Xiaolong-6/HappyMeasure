"""Deterministic NumPy-only signal preparation algorithms."""

from __future__ import annotations

import numpy as np

from map_reconstruction.models import TimeSeriesData

from .models import (
    DarkCorrectionMode,
    ManualRegionFit,
    OutputConvention,
    PhotocurrentPolarity,
    PreparedSignal,
    RollingTrend,
    SignalPreparationConfig,
)


def _eligible(values: np.ndarray, config: SignalPreparationConfig) -> np.ndarray:
    if not config.value_gate_enabled:
        return np.ones(values.shape, dtype=bool)
    return (values >= config.value_gate_min) & (values <= config.value_gate_max)


def _apply_convention(
    values: np.ndarray, baseline: np.ndarray, config: SignalPreparationConfig
) -> np.ndarray:
    if config.output_convention is OutputConvention.MEASURED_MINUS_DARK:
        return values - baseline
    return baseline - values


def _manual_baseline(
    time: np.ndarray, values: np.ndarray, config: SignalPreparationConfig
) -> tuple[np.ndarray, list[str], int]:
    estimates: list[tuple[float, float]] = []
    warnings: list[str] = []
    eligible = _eligible(values, config)
    for index, region in enumerate(config.manual_dark_regions, start=1):
        mask = (time >= region.start_s) & (time < region.end_s) & eligible
        if not np.any(mask):
            warnings.append(f"Dark region {index} contains no eligible samples and was skipped.")
            continue
        estimates.append((region.center_s, float(np.median(values[mask]))))
    degree = {
        ManualRegionFit.CONSTANT: 0,
        ManualRegionFit.LINEAR: 1,
        ManualRegionFit.QUADRATIC: 2,
    }[config.manual_region_fit]
    if len(estimates) < degree + 1:
        raise ValueError(
            f"{config.manual_region_fit.value.title()} dark fit requires at least {degree + 1} valid regions."
        )
    anchors_t = np.asarray([item[0] for item in estimates], dtype=float)
    anchors_b = np.asarray([item[1] for item in estimates], dtype=float)
    if degree == 0:
        baseline = np.full(time.shape, float(np.median(anchors_b)), dtype=float)
    elif config.manual_region_fit is ManualRegionFit.LINEAR:
        baseline = np.polyval(np.polyfit(anchors_t, anchors_b, 1), time)
    else:
        baseline = np.polyval(np.polyfit(anchors_t, anchors_b, 2), time)
    return baseline, warnings, len(estimates)


def _rolling_dark_quantile(config: SignalPreparationConfig) -> float:
    """Return the envelope quantile implied by the photocurrent direction.

    Negative photocurrent means illumination moves the measured signal downward,
    so dark current is estimated from the upper envelope. Positive photocurrent
    uses the corresponding lower envelope. ``rolling_quantile`` therefore
    describes the confidence away from the illuminated tail for either sign.
    """

    if config.response_direction is PhotocurrentPolarity.NEGATIVE:
        return config.rolling_quantile
    return 1.0 - config.rolling_quantile


def _rolling_baseline(
    time: np.ndarray, values: np.ndarray, config: SignalPreparationConfig
) -> tuple[np.ndarray, list[str], int]:
    eligible = _eligible(values, config)
    start, stop = float(time[0]), float(time[-1])
    edges = np.arange(start, stop + config.rolling_window_s, config.rolling_window_s)
    if edges.size < 2 or edges[-1] < stop:
        edges = np.append(edges, stop)
    anchor_t: list[float] = []
    anchor_b: list[float] = []
    warnings: list[str] = []
    effective_quantile = _rolling_dark_quantile(config)
    for left, right in zip(edges[:-1], edges[1:]):
        mask = (time >= left) & ((time < right) if right < stop else (time <= right)) & eligible
        if not np.any(mask):
            warnings.append(f"No eligible dark candidates in time bin {left:g}–{right:g} s.")
            continue
        anchor_t.append(float(np.median(time[mask])))
        anchor_b.append(float(np.quantile(values[mask], effective_quantile)))
    if not anchor_t:
        raise ValueError("Rolling quantile produced no eligible dark-current candidates.")
    t_anchor = np.asarray(anchor_t, dtype=float)
    b_anchor = np.asarray(anchor_b, dtype=float)
    if config.rolling_trend is RollingTrend.PIECEWISE_LINEAR or t_anchor.size == 1:
        baseline = np.interp(time, t_anchor, b_anchor, left=b_anchor[0], right=b_anchor[-1])
    else:
        degree = 1 if config.rolling_trend is RollingTrend.LINEAR else 2
        if t_anchor.size < degree + 1:
            raise ValueError(
                f"{config.rolling_trend.value.title()} rolling trend requires at least {degree + 1} populated bins."
            )
        baseline = np.polyval(np.polyfit(t_anchor, b_anchor, degree), time)
        # Polynomial trends are intentionally clamped to constant endpoints.
        baseline[time < t_anchor[0]] = b_anchor[0]
        baseline[time > t_anchor[-1]] = b_anchor[-1]
    return baseline, warnings, len(anchor_t)


def prepare_signal(
    data: TimeSeriesData, signal: str, config: SignalPreparationConfig | None = None
) -> PreparedSignal:
    """Prepare one imported trace without mutating ``data``.

    ``None`` mode is a strict identity copy: no baseline and no sign conversion
    are applied. Active modes produce a finite baseline and apply the explicit
    output convention selected by the operator.
    """

    config = config or SignalPreparationConfig()
    if signal not in data.signals:
        raise ValueError(f"Unknown signal {signal!r}.")
    time = np.array(data.time_s, dtype=float, copy=True)
    values = np.array(data.signals[signal], dtype=float, copy=True)
    if time.size == 0:
        raise ValueError("Cannot prepare an empty signal.")
    if config.dark_correction_mode is DarkCorrectionMode.NONE:
        return PreparedSignal(time, values, signal, None, (), {"mode": "none"})
    warnings: list[str] = []
    if config.dark_correction_mode is DarkCorrectionMode.CONSTANT:
        baseline = np.full(values.shape, config.constant_baseline, dtype=float)
        candidate_count = int(np.count_nonzero(_eligible(values, config)))
    elif config.dark_correction_mode is DarkCorrectionMode.MANUAL_REGIONS:
        baseline, warnings, candidate_count = _manual_baseline(time, values, config)
    else:
        baseline, warnings, candidate_count = _rolling_baseline(time, values, config)
    prepared = _apply_convention(values, baseline, config)
    metadata = {
        "mode": config.dark_correction_mode.value,
        "output_convention": config.output_convention.value,
        "candidate_count": candidate_count,
        "baseline_start": float(baseline[0]),
        "baseline_end": float(baseline[-1]),
    }
    if config.dark_correction_mode is DarkCorrectionMode.ROLLING_QUANTILE:
        metadata.update(
            {
                "response_direction": config.response_direction.value,
                "effective_dark_quantile": _rolling_dark_quantile(config),
            }
        )
    return PreparedSignal(time, prepared, signal, baseline, tuple(warnings), metadata)
