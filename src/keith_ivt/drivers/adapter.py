"""Adapter to bridge legacy SourceMeter interface to new SMUDriver protocol.

This module provides backward compatibility during the migration from the old
SourceMeter ABC to the new SMUDriver Protocol. New code should use SMUDriver directly.
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from keith_ivt.drivers.base import (
    ConnectionProfile,
    DriverCapabilities,
    DriverReadback,
    MeasureMode,
    SMUDriver,
    SourceMode,
    TerminalRoute,
    SenseWiring,
)

if TYPE_CHECKING:
    from keith_ivt.instrument.base import SourceMeter
    from keith_ivt.models import SweepConfig


class SourceMeterAdapter(SMUDriver):
    """Adapter that makes a legacy SourceMeter compatible with SMUDriver Protocol.

    This allows existing hardware implementations (Keithley2400Serial, SimulatedKeithley)
    to work with new code expecting the SMUDriver interface without modification.

    Usage:
        legacy_meter = Keithley2400Serial(...)
        adapter = SourceMeterAdapter(legacy_meter)
        # Now use adapter as SMUDriver
        adapter.connect(ConnectionProfile(resource="COM3"))
        adapter.configure_source_measure(...)
    """

    def __init__(self, meter: "SourceMeter"):
        self._meter = meter
        self._profile: ConnectionProfile | None = None
        self._config: SweepConfig | None = None
        self._source_mode = SourceMode.VOLTAGE
        self._measure_mode = MeasureMode.CURRENT

    @property
    def capabilities(self) -> DriverCapabilities:
        """Derive capabilities from the underlying instrument type."""
        # For now, return generic capabilities
        # Future: inspect meter type and set appropriate flags
        return DriverCapabilities(
            name="Legacy SourceMeter (adapted)",
            vendor="unknown",
            model_family="legacy-adapter",
            supports_voltage_source=True,
            supports_current_source=True,
            supports_cv=False,
            supports_front_rear=False,
            supports_4wire=True,
            supports_fixed_range=True,
            supports_manual_output=True,
        )

    def connect(self, profile: ConnectionProfile) -> None:
        """Connect the underlying instrument."""
        self._profile = profile
        # Legacy SourceMeter.connect() takes no arguments
        self._meter.connect()

    def disconnect(self) -> None:
        """Disconnect without closing."""
        # Legacy interface doesn't have separate disconnect
        pass

    def identify(self) -> str:
        """Get instrument identification."""
        return self._meter.identify()

    def reset(self) -> None:
        """Reset the instrument."""
        self._meter.reset()

    def configure_source_measure(
        self,
        source_mode: SourceMode,
        measure_mode: MeasureMode,
        compliance: float,
        nplc: float,
        autorange: bool = True,
        source_range: float | None = None,
        measure_range: float | None = None,
    ) -> None:
        """Configure source and measure parameters.

        Maps SMUDriver parameters to legacy SweepConfig format.
        """
        from keith_ivt.models import SweepConfig, SweepMode, SenseMode, Terminal

        self._source_mode = source_mode
        self._measure_mode = measure_mode

        # Map SourceMode to SweepMode
        sweep_mode = SweepMode.VOLTAGE_SOURCE if source_mode == SourceMode.VOLTAGE else SweepMode.CURRENT_SOURCE

        # Create a SweepConfig from SMUDriver parameters
        # This is a simplified mapping - full implementation would need more context
        self._config = SweepConfig(
            mode=sweep_mode,
            start=0.0,  # Will be set by actual sweep
            stop=0.0,
            step=0.0,
            compliance=compliance,
            nplc=nplc,
            auto_source_range=autorange and source_range is None,
            auto_measure_range=autorange and measure_range is None,
            source_range=source_range or 0.0,
            measure_range=measure_range or 0.0,
            sense_mode=SenseMode.TWO_WIRE,  # Default
            terminal=Terminal.REAR,  # Default
            output_off_after_run=True,
        )

        # Configure the legacy instrument
        self._meter.configure_for_sweep(self._config)

    def set_source(self, source_mode: SourceMode, value: float) -> None:
        """Set source value."""
        self._source_mode = source_mode
        # Legacy interface uses SCPI command string
        scpi_cmd = source_mode.value
        self._meter.set_source(scpi_cmd, value)

    def read(self) -> DriverReadback:
        """Read source and measurement values."""
        source_val, measured_val = self._meter.read_source_and_measure()
        return DriverReadback(
            source_value=source_val,
            measured_value=measured_val,
            timestamp_s=time.time(),
        )

    def output_on(self) -> None:
        """Enable output."""
        self._meter.output_on()

    def output_off(self) -> None:
        """Disable output."""
        self._meter.output_off()

    def close(self) -> None:
        """Close the instrument connection."""
        try:
            self._meter.output_off()
        except Exception:
            pass
        finally:
            self._meter.close()

    def __enter__(self) -> "SourceMeterAdapter":
        self.connect(self._profile or ConnectionProfile())
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
