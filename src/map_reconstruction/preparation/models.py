"""Immutable, serialisable configuration for signal preparation.

The preparation layer deliberately contains no Qt or plotting imports.  It is
therefore safe to use from project loading, tests and worker threads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

import numpy as np


class DarkCorrectionMode(str, Enum):
    NONE = "none"
    CONSTANT = "constant"
    MANUAL_REGIONS = "manual_regions"
    ROLLING_QUANTILE = "rolling_quantile"


class ManualRegionFit(str, Enum):
    CONSTANT = "constant"
    LINEAR = "linear"
    QUADRATIC = "quadratic"


class RollingTrend(str, Enum):
    PIECEWISE_LINEAR = "piecewise_linear"
    LINEAR = "linear"
    QUADRATIC = "quadratic"


class PhotocurrentPolarity(str, Enum):
    NEGATIVE = "negative"
    POSITIVE = "positive"


class OutputConvention(str, Enum):
    MEASURED_MINUS_DARK = "measured_minus_dark"
    DARK_MINUS_MEASURED = "dark_minus_measured"


@dataclass(frozen=True, slots=True)
class DarkRegion:
    """A half-open time interval selected as a dark-current candidate."""

    start_s: float
    end_s: float

    def __post_init__(self) -> None:
        start = float(self.start_s)
        end = float(self.end_s)
        if not np.isfinite(start) or not np.isfinite(end) or not start < end:
            raise ValueError("Dark regions require finite start_s < end_s.")
        object.__setattr__(self, "start_s", start)
        object.__setattr__(self, "end_s", end)

    @property
    def center_s(self) -> float:
        return (self.start_s + self.end_s) / 2.0


@dataclass(frozen=True, slots=True)
class SignalPreparationConfig:
    """Scientific preparation settings, independent of widget state."""

    dark_correction_mode: DarkCorrectionMode = DarkCorrectionMode.NONE
    constant_baseline: float = 0.0
    manual_dark_regions: tuple[DarkRegion, ...] = field(default_factory=tuple)
    manual_region_fit: ManualRegionFit = ManualRegionFit.CONSTANT
    rolling_quantile: float = 0.9
    rolling_window_s: float = 10.0
    rolling_trend: RollingTrend = RollingTrend.PIECEWISE_LINEAR
    response_direction: PhotocurrentPolarity = PhotocurrentPolarity.NEGATIVE
    value_gate_enabled: bool = False
    value_gate_min: float = -np.inf
    value_gate_max: float = np.inf
    output_convention: OutputConvention = OutputConvention.MEASURED_MINUS_DARK
    # The two explicit operation flags are the current public semantics.  The
    # legacy convention remains stored and accepted so v3 projects keep their
    # exact numerical meaning.
    apply_baseline: bool | None = None
    invert_signal: bool | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "dark_correction_mode", DarkCorrectionMode(self.dark_correction_mode)
        )
        object.__setattr__(self, "manual_region_fit", ManualRegionFit(self.manual_region_fit))
        object.__setattr__(self, "rolling_trend", RollingTrend(self.rolling_trend))
        object.__setattr__(
            self, "response_direction", PhotocurrentPolarity(self.response_direction)
        )
        object.__setattr__(self, "output_convention", OutputConvention(self.output_convention))
        # Baseline correction is meaningless without a baseline model. Force
        # it off so UI state "Subtract B(t)" cannot be persisted as a no-op.
        if self.dark_correction_mode is DarkCorrectionMode.NONE:
            apply_baseline = False
            invert_signal = bool(self.invert_signal) if self.invert_signal is not None else False
        else:
            legacy_active = True
            apply_baseline = legacy_active if self.apply_baseline is None else bool(self.apply_baseline)
            invert_signal = (
                legacy_active and self.output_convention is OutputConvention.DARK_MINUS_MEASURED
                if self.invert_signal is None
                else bool(self.invert_signal)
            )
        # Keep the compatibility field coherent for callers and old metadata.
        object.__setattr__(
            self,
            "output_convention",
            (
                OutputConvention.DARK_MINUS_MEASURED
                if invert_signal
                else OutputConvention.MEASURED_MINUS_DARK
            ),
        )
        object.__setattr__(self, "apply_baseline", apply_baseline)
        object.__setattr__(self, "invert_signal", invert_signal)
        baseline = float(self.constant_baseline)
        if not np.isfinite(baseline):
            raise ValueError("constant_baseline must be finite.")
        object.__setattr__(self, "constant_baseline", baseline)
        regions = tuple(
            region if isinstance(region, DarkRegion) else DarkRegion(*region)
            for region in self.manual_dark_regions
        )
        object.__setattr__(self, "manual_dark_regions", regions)
        quantile = float(self.rolling_quantile)
        if not np.isfinite(quantile) or not 0.0 <= quantile <= 1.0:
            raise ValueError("rolling_quantile must be between 0 and 1.")
        object.__setattr__(self, "rolling_quantile", quantile)
        window = float(self.rolling_window_s)
        if not np.isfinite(window) or window <= 0:
            raise ValueError("rolling_window_s must be greater than zero.")
        object.__setattr__(self, "rolling_window_s", window)
        gate_min = float(self.value_gate_min)
        gate_max = float(self.value_gate_max)
        if self.value_gate_enabled and (
            not np.isfinite(gate_min) or not np.isfinite(gate_max) or gate_min > gate_max
        ):
            raise ValueError("Value-gate limits must be finite with min <= max.")
        object.__setattr__(self, "value_gate_min", gate_min)
        object.__setattr__(self, "value_gate_max", gate_max)
        object.__setattr__(self, "value_gate_enabled", bool(self.value_gate_enabled))

    @property
    def is_identity(self) -> bool:
        return not self.apply_baseline and not self.invert_signal

    @property
    def has_nondefault_state(self) -> bool:
        """Return whether any persisted field differs from the default.

        ``is_identity`` describes the current mathematical no-op state, but a
        configuration with fitted baseline regions and ``apply_baseline=False``
        must still be persisted as v3 so the workflow can be restored.
        """

        return self != SignalPreparationConfig()

    @property
    def baseline_model(self) -> DarkCorrectionMode:
        """Mathematical name for the legacy persisted baseline-model field."""

        return self.dark_correction_mode

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON-friendly representation used by project v3."""

        gate: dict[str, float] | None = None
        if self.value_gate_enabled:
            gate = {"min": self.value_gate_min, "max": self.value_gate_max}
        dark_correction = {
            "mode": self.dark_correction_mode.value,
            "quantile": self.rolling_quantile * 100.0,
            "window_s": self.rolling_window_s,
            "trend": self.rolling_trend.value,
            "manual_regions": [
                {"start_s": region.start_s, "end_s": region.end_s}
                for region in self.manual_dark_regions
            ],
            "manual_region_fit": self.manual_region_fit.value,
        }
        return {
            "mode": self.dark_correction_mode.value,
            "dark_correction": dark_correction,
            "constant_baseline": self.constant_baseline,
            "manual_region_fit": self.manual_region_fit.value,
            "manual_regions": [
                {"start_s": region.start_s, "end_s": region.end_s}
                for region in self.manual_dark_regions
            ],
            "rolling_quantile": self.rolling_quantile,
            "rolling_window_s": self.rolling_window_s,
            "rolling_trend": self.rolling_trend.value,
            "response_direction": self.response_direction.value,
            "value_gate": gate,
            "output_convention": self.output_convention.value,
            "baseline_model": self.baseline_model.value,
            "apply_baseline": self.apply_baseline,
            "invert_signal": self.invert_signal,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SignalPreparationConfig":
        nested = payload.get("dark_correction")
        if isinstance(nested, Mapping):
            payload = {**nested, **payload}
            if "quantile" in nested and "rolling_quantile" not in payload:
                payload["rolling_quantile"] = float(nested["quantile"]) / 100.0
            if "window_s" in nested and "rolling_window_s" not in payload:
                payload["rolling_window_s"] = nested["window_s"]
            if "trend" in nested and "rolling_trend" not in payload:
                payload["rolling_trend"] = nested["trend"]
        gate = payload.get("value_gate")
        if gate is None:
            gate_enabled, gate_min, gate_max = False, -np.inf, np.inf
        elif isinstance(gate, Mapping):
            gate_enabled = True
            raw_min = gate.get("min")
            raw_max = gate.get("max")
            if raw_min is None or raw_max is None:
                raise ValueError("Invalid preparation.value_gate.")
            gate_min = float(raw_min)
            gate_max = float(raw_max)
        else:
            raise ValueError("Invalid preparation.value_gate.")
        raw_regions = payload.get("manual_regions", ())
        if not isinstance(raw_regions, (list, tuple)):
            raise ValueError("Invalid preparation.manual_regions.")
        regions = tuple(
            (
                DarkRegion(float(item["start_s"]), float(item["end_s"]))
                if isinstance(item, Mapping)
                else DarkRegion(*item)
            )
            for item in raw_regions
        )
        baseline_model = payload.get("baseline_model", payload.get("mode", DarkCorrectionMode.NONE))
        return cls(
            dark_correction_mode=baseline_model,
            constant_baseline=payload.get("constant_baseline", 0.0),
            manual_dark_regions=regions,
            manual_region_fit=payload.get("manual_region_fit", ManualRegionFit.CONSTANT),
            rolling_quantile=payload.get("rolling_quantile", 0.9),
            rolling_window_s=payload.get("rolling_window_s", 10.0),
            rolling_trend=payload.get("rolling_trend", RollingTrend.PIECEWISE_LINEAR),
            response_direction=payload.get("response_direction", PhotocurrentPolarity.NEGATIVE),
            value_gate_enabled=gate_enabled,
            value_gate_min=gate_min,
            value_gate_max=gate_max,
            output_convention=payload.get(
                "output_convention", OutputConvention.MEASURED_MINUS_DARK
            ),
            apply_baseline=payload.get("apply_baseline"),
            invert_signal=payload.get("invert_signal"),
        )


@dataclass(frozen=True, slots=True)
class PreparedSignal:
    """Prepared scientific trace with immutable, read-only NumPy arrays."""

    time_s: np.ndarray
    values: np.ndarray
    source_signal: str
    baseline: np.ndarray | None = None
    warnings: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        time = np.array(self.time_s, dtype=float, copy=True)
        values = np.array(self.values, dtype=float, copy=True)
        if time.ndim != 1 or values.ndim != 1 or time.size != values.size:
            raise ValueError("Prepared signal time_s and values must be matching 1-D arrays.")
        if not np.all(np.isfinite(time)) or not np.all(np.isfinite(values)):
            raise ValueError("Prepared signal arrays must contain only finite values.")
        baseline: np.ndarray | None
        if self.baseline is None:
            baseline = None
        else:
            baseline = np.array(self.baseline, dtype=float, copy=True)
            if baseline.shape != time.shape or not np.all(np.isfinite(baseline)):
                raise ValueError("Prepared baseline must match time_s and be finite.")
            baseline.setflags(write=False)
        time.setflags(write=False)
        values.setflags(write=False)
        object.__setattr__(self, "time_s", time)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "baseline", baseline)
        object.__setattr__(self, "source_signal", str(self.source_signal))
        object.__setattr__(self, "warnings", tuple(str(item) for item in self.warnings))
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def sample_count(self) -> int:
        return int(self.time_s.size)
