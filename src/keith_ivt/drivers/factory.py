"""Factory functions for creating hardware drivers.

This module provides a unified way to create SMUDriver instances, whether from
legacy SourceMeter implementations or new native SMUDriver drivers.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from keith_ivt.drivers.base import ConnectionProfile, SMUDriver
from keith_ivt.drivers.adapter import SourceMeterAdapter

if TYPE_CHECKING:
    from keith_ivt.instrument.base import SourceMeter


def create_driver_from_source_meter(meter: "SourceMeter") -> SMUDriver:
    """Create an SMUDriver adapter from a legacy SourceMeter.

    This is the primary migration path for existing code using SourceMeter.

    Example:
        >>> from keith_ivt.instrument.simulator import SimulatedKeithley
        >>> meter = SimulatedKeithley()
        >>> driver = create_driver_from_source_meter(meter)
        >>> # Now use driver as SMUDriver
        >>> driver.connect(ConnectionProfile(resource="COM3"))
    """
    return SourceMeterAdapter(meter)


def ensure_smu_driver(driver_or_meter) -> SMUDriver:
    """Ensure we have an SMUDriver instance, adapting if necessary.

    This function accepts either:
    - An existing SMUDriver (returned as-is)
    - A legacy SourceMeter (wrapped in SourceMeterAdapter)

    Example:
        >>> # Works with both old and new interfaces
        >>> driver = ensure_smu_driver(hardware_instance)
        >>> driver.connect(ConnectionProfile())
    """
    # Check if it's already an SMUDriver
    if isinstance(driver_or_meter, SMUDriver):
        return driver_or_meter

    # Otherwise, assume it's a legacy SourceMeter and adapt it
    return SourceMeterAdapter(driver_or_meter)
