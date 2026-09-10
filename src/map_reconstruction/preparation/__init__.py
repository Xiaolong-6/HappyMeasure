"""Qt-free signal-preparation models and deterministic baseline correction."""

from .models import (
    DarkCorrectionMode,
    DarkRegion,
    ManualRegionFit,
    OutputConvention,
    PhotocurrentPolarity,
    PreparedSignal,
    RollingTrend,
    SignalPreparationConfig,
)
from .pipeline import prepare_signal

__all__ = [
    "DarkCorrectionMode",
    "DarkRegion",
    "ManualRegionFit",
    "OutputConvention",
    "PhotocurrentPolarity",
    "PreparedSignal",
    "RollingTrend",
    "SignalPreparationConfig",
    "prepare_signal",
]
