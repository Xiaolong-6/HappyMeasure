from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from keith_ivt.drivers.base import (
    ConnectionProfile,
    DriverCapabilities,
    DriverReadback,
    MeasureMode,
    MeasurementFamily,
    OutputState,
    SenseWiring,
    SMUDriver,
    SourceMode,
    TerminalRoute,
)

if TYPE_CHECKING:
    from keith_ivt.drivers.adapter import SourceMeterAdapter
    from keith_ivt.drivers.keithley2400_adapter import Keithley2400Driver
    from keith_ivt.drivers.simulated_smu import SimulatedSMUDriver

_LAZY_EXPORTS = {
    "SimulatedSMUDriver": ("keith_ivt.drivers.simulated_smu", "SimulatedSMUDriver"),
    "Keithley2400Driver": ("keith_ivt.drivers.keithley2400_adapter", "Keithley2400Driver"),
    "SourceMeterAdapter": ("keith_ivt.drivers.adapter", "SourceMeterAdapter"),
    "create_driver_from_source_meter": (
        "keith_ivt.drivers.factory",
        "create_driver_from_source_meter",
    ),
    "ensure_smu_driver": ("keith_ivt.drivers.factory", "ensure_smu_driver"),
}


def __getattr__(name: str) -> Any:
    """Lazily expose adapter implementations without importing them at package load.

    ``instrument.serial_2400`` imports ``keith_ivt.drivers.base`` for capability
    metadata. Importing concrete adapters here eagerly would load
    ``keithley2400_adapter`` which imports ``serial_2400`` again, creating a
    circular import before ``Keithley2400Serial`` has been defined.
    """

    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = target
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY_EXPORTS))


__all__ = [
    "ConnectionProfile",
    "DriverCapabilities",
    "DriverReadback",
    "MeasureMode",
    "MeasurementFamily",
    "OutputState",
    "SenseWiring",
    "SMUDriver",
    "SourceMode",
    "TerminalRoute",
    "SimulatedSMUDriver",
    "Keithley2400Driver",
    "SourceMeterAdapter",
    "create_driver_from_source_meter",
    "ensure_smu_driver",
]
