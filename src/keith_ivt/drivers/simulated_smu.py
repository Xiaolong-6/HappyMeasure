from __future__ import annotations

import random
import time

from keith_ivt.drivers.base import (
    ConnectionProfile,
    DriverCapabilities,
    DriverReadback,
    MeasureMode,
    SMUDriver,
    SourceMode,
)


class SimulatedSMUDriver:
    """Generic simulator for UI, sweep, and import/export testing.

    It intentionally implements several source/measure pairings so future UI
    work can test IV/CV-oriented flows without hardware.
    """

    capabilities = DriverCapabilities(
        name="Debug simulator",
        vendor="HappyMeasure",
        model_family="generic-sim",
        supports_cv=True,
        supports_front_rear=True,
        supports_4wire=True,
    )

    def __init__(self, resistance_ohm: float = 10_000.0, capacitance_f: float = 1e-9, noise_fraction: float = 0.002):
        self.resistance_ohm = float(resistance_ohm)
        self.capacitance_f = float(capacitance_f)
        self.noise_fraction = float(noise_fraction)
        self.profile = ConnectionProfile()
        self.connected = False
        self.output_enabled = False
        self.source_mode = SourceMode.VOLTAGE
        self.measure_mode = MeasureMode.CURRENT
        self.source_value = 0.0
        self.compliance = 0.01
        self.nplc = 1.0

    def connect(self, profile: ConnectionProfile) -> None:
        self.profile = profile
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def close(self) -> None:
        self.disconnect()

    def identify(self) -> str:
        return "SIMULATED,GENERIC-HAPPYMEASURE,DEBUG,0.1"

    def reset(self) -> None:
        self.output_enabled = False
        self.source_value = 0.0

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
        self.source_mode = source_mode
        self.measure_mode = measure_mode
        self.compliance = float(compliance)
        self.nplc = float(nplc)

    def set_source(self, source_mode: SourceMode, value: float) -> None:
        self.source_mode = source_mode
        self.source_value = float(value)

    def read(self) -> DriverReadback:
        # Keep simulator slow enough to expose UI state issues, but fast enough for tests.
        time.sleep(min(0.005 + self.nplc * 0.001, 0.03))
        x = self.source_value
        if self.measure_mode is MeasureMode.CURRENT:
            ideal = x / self.resistance_ohm
            sigma = abs(ideal) * self.noise_fraction + 1e-9
        elif self.measure_mode is MeasureMode.VOLTAGE:
            ideal = x * self.resistance_ohm
            sigma = abs(ideal) * self.noise_fraction + 1e-6
        elif self.measure_mode is MeasureMode.CAPACITANCE:
            # Soft bias dependence gives CV-like simulator data.
            ideal = self.capacitance_f * (1.0 + 0.15 / (1.0 + abs(x)))
            sigma = ideal * self.noise_fraction
        else:
            ideal = self.resistance_ohm
            sigma = ideal * self.noise_fraction
        return DriverReadback(source_value=x, measured_value=ideal + random.gauss(0.0, sigma), timestamp_s=time.time())

    def output_on(self) -> None:
        self.output_enabled = True

    def output_off(self) -> None:
        self.output_enabled = False

    def __enter__(self) -> "SimulatedSMUDriver":
        self.connect(self.profile)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            self.output_off()
        finally:
            self.close()
