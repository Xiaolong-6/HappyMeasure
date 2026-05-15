from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable


class SourceMode(str, Enum):
    VOLTAGE = "VOLT"
    CURRENT = "CURR"


class MeasureMode(str, Enum):
    CURRENT = "CURR"
    VOLTAGE = "VOLT"
    CAPACITANCE = "CAP"
    RESISTANCE = "RES"


class TerminalRoute(str, Enum):
    FRONT = "FRON"
    REAR = "REAR"


class SenseWiring(str, Enum):
    TWO_WIRE = "2W"
    FOUR_WIRE = "4W"


class MeasurementFamily(str, Enum):
    IV = "IV"
    CV = "CV"
    IVCV = "IVCV"


@dataclass(frozen=True)
class ConnectionProfile:
    resource: str = "COM3"
    baud_rate: int = 9600
    timeout_s: float = 5.0
    terminal: TerminalRoute = TerminalRoute.REAR
    sense_wiring: SenseWiring = SenseWiring.TWO_WIRE
    debug: bool = True


@dataclass(frozen=True)
class DriverCapabilities:
    name: str
    vendor: str = "unknown"
    model_family: str = "generic"
    supports_voltage_source: bool = True
    supports_current_source: bool = True
    supports_cv: bool = False
    supports_front_rear: bool = False
    supports_4wire: bool = True
    supports_fixed_range: bool = True
    supports_manual_output: bool = True


@dataclass(frozen=True)
class OutputState:
    enabled: bool
    source_mode: SourceMode | None = None
    source_value: float | None = None


@dataclass(frozen=True)
class DriverReadback:
    source_value: float
    measured_value: float
    timestamp_s: float | None = None


@runtime_checkable
class SMUDriver(Protocol):
    """Small hardware boundary for source-meter-like instruments.

    Future Keithley/Keysight/NI drivers should implement this protocol instead of
    being coupled to Tk widgets or to a specific IV sweep runner.
    """

    capabilities: DriverCapabilities

    def connect(self, profile: ConnectionProfile) -> None: ...
    def disconnect(self) -> None: ...
    def identify(self) -> str: ...
    def reset(self) -> None: ...
    def configure_source_measure(
        self,
        source_mode: SourceMode,
        measure_mode: MeasureMode,
        compliance: float,
        nplc: float,
        autorange: bool = True,
        source_range: float | None = None,
        measure_range: float | None = None,
    ) -> None: ...
    def set_source(self, source_mode: SourceMode, value: float) -> None: ...
    def read(self) -> DriverReadback: ...
    def output_on(self) -> None: ...
    def output_off(self) -> None: ...
    def close(self) -> None: ...

    def __enter__(self) -> "SMUDriver": ...
    def __exit__(self, exc_type, exc, tb) -> None: ...
