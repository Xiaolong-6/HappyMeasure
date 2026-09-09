"""Headless map-value processing primitives for the optional map workspace."""

from map_reconstruction.processing.models import (
    BaselineMode,
    ColorRangeMode,
    MapProcessingConfig,
    NormalizationMode,
    ProcessedMap,
    ValueScale,
    ValueTransform,
)
from map_reconstruction.processing.pipeline import (
    ColorLimits,
    compute_color_limits,
    process_map,
)

__all__ = [
    "BaselineMode",
    "ColorLimits",
    "ColorRangeMode",
    "MapProcessingConfig",
    "NormalizationMode",
    "ProcessedMap",
    "ValueScale",
    "ValueTransform",
    "compute_color_limits",
    "process_map",
]
