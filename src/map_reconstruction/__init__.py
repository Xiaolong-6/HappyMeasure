"""Standalone 2-D map reconstruction from HappyMeasure time-series exports.

The package deliberately keeps the importer and numerical core independent of
Qt so they can be used and tested on headless systems.
"""

from __future__ import annotations

__all__ = [
    "DualOffsetParams",
    "ReconstructionResult",
    "ScanPattern",
    "TimeSeriesData",
    "TimingSolution",
]

__version__ = "0.1.0"


def __getattr__(name: str):
    """Load model exports only when requested, keeping GUI extras optional."""

    if name in __all__:
        from . import models

        value = getattr(models, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
