from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass

from keith_ivt.drivers.base import (
    ConnectionProfile,
    DriverCapabilities,
    DriverReadback,
    MeasureMode,
    SourceMode,
)
from keith_ivt.instrument.base import SourceMeter
from keith_ivt.models import SweepConfig


@dataclass(frozen=True)
class DebugDeviceModel:
    name: str
    resistance_ohm: float = 10_000.0
    noise_fraction: float = 0.002
    kind: str = "linear"


DEBUG_DEVICE_MODELS: dict[str, DebugDeviceModel] = {
    "Linear resistor 10 kΩ": DebugDeviceModel("Linear resistor 10 kΩ", 10_000.0, 0.002, "linear"),
    "Low resistance 100 Ω": DebugDeviceModel("Low resistance 100 Ω", 100.0, 0.003, "linear"),
    "High resistance 10 MΩ": DebugDeviceModel("High resistance 10 MΩ", 10_000_000.0, 0.01, "linear"),
    "Noisy photodetector": DebugDeviceModel("Noisy photodetector", 250_000.0, 0.05, "photodetector"),
    "Diode-like nonlinear": DebugDeviceModel("Diode-like nonlinear", 1_000.0, 0.01, "diode"),
}


def debug_model_names() -> list[str]:
    return list(DEBUG_DEVICE_MODELS.keys())


class SimulatedKeithley(SourceMeter):
    """Debug device for UI and workflow testing without hardware."""

    def __init__(self, resistance_ohm: float = 10_000.0, noise_fraction: float = 0.002, model_name: str | None = None):
        model = DEBUG_DEVICE_MODELS.get(model_name or "", DEBUG_DEVICE_MODELS["Linear resistor 10 kΩ"])
        self.model = model
        self.resistance_ohm = resistance_ohm if model_name is None else model.resistance_ohm
        self.noise_fraction = noise_fraction if model_name is None else model.noise_fraction
        self._last_source = 0.0
        self._config: SweepConfig | None = None
        self._is_open = False
        self._output = False

    def connect(self) -> None:
        self._is_open = True

    def close(self) -> None:
        self._is_open = False

    def identify(self) -> str:
        return f"SIMULATED,KEITHLEY-2400,DEBUG,{self.model.name},0.1"

    def reset(self) -> None:
        self._last_source = 0.0
        self._output = False

    def configure_for_sweep(self, config: SweepConfig) -> None:
        self._config = config

    def set_source(self, source_cmd: str, value: float) -> None:
        self._last_source = self._apply_source_range(value)

    def read_source_and_measure(self) -> tuple[float, float]:
        nplc_delay = 0.03
        if self._config is not None:
            nplc_delay = min(0.25, max(0.005, float(self._config.nplc) / 50.0))
        time.sleep(nplc_delay)
        if self._config is None:
            raise RuntimeError("Simulator not configured.")
        if self._config.source_scpi == "VOLT":
            ideal = self._current_from_voltage(self._last_source)
            noise_floor = 1e-9 if self.noise_fraction > 0 else 0.0
            measured = ideal + random.gauss(0.0, abs(ideal) * self._nplc_noise_fraction() + noise_floor / self._nplc_noise_gain())
            measured = self._apply_measure_range(measured)
            measured = self._apply_compliance(measured)
        else:
            ideal = self._voltage_from_current(self._last_source)
            noise_floor = 1e-6 if self.noise_fraction > 0 else 0.0
            measured_raw = ideal + random.gauss(0.0, abs(ideal) * self._nplc_noise_fraction() + noise_floor / self._nplc_noise_gain())
            measured = self._apply_measure_range(measured_raw)
            measured = self._apply_compliance(measured)
            source_readback = self._last_source
            if self.model.kind == "diode":
                # In current-source mode the simulator should still produce a
                # diode I-V curve.  If a requested current is outside what the
                # diode can support before voltage compliance, report the actual
                # diode current at the measured voltage rather than the impossible
                # command current.  Keep linear/photodetector current-source
                # readback compatible with earlier tests: source_value remains the
                # clipped source command and measured_value carries the voltage.
                source_readback = self._current_from_voltage(measured)
            return source_readback, measured
        return self._last_source, measured

    def _nplc_noise_gain(self) -> float:
        if self._config is None:
            return 1.0
        return max(0.1, math.sqrt(max(float(self._config.nplc), 0.01)))

    def _nplc_noise_fraction(self) -> float:
        return self.noise_fraction / self._nplc_noise_gain()

    def _apply_source_range(self, value: float) -> float:
        if self._config is None or self._config.auto_source_range or self._config.source_range <= 0:
            return value
        limit = abs(float(self._config.source_range))
        return max(-limit, min(limit, value))

    def _apply_measure_range(self, value: float) -> float:
        if self._config is None or self._config.auto_measure_range or self._config.measure_range <= 0:
            return value
        limit = abs(float(self._config.measure_range))
        return max(-limit, min(limit, value))

    def _apply_compliance(self, value: float) -> float:
        if self._config is None or self._config.compliance <= 0:
            return value
        limit = abs(float(self._config.compliance))
        return max(-limit, min(limit, value))

    def _diode_current_at_voltage(self, voltage: float) -> float:
        # Smooth toy diode model with a small shunt path.  Keep the exponential
        # numerically safe, but do not clamp the voltage itself: current-source
        # sweeps need the reverse shunt branch to remain invertible until the
        # configured voltage compliance is reached.
        v = float(voltage)
        exponent = max(-50.0, min(50.0, v / 0.055))
        return 1e-9 * (math.exp(exponent) - 1.0) + v / 1_000_000.0

    def _diode_voltage_search_bounds(self) -> tuple[float, float]:
        limit = 10.0
        if self._config is not None and self._config.compliance > 0:
            limit = max(0.1, abs(float(self._config.compliance)))
        return -limit, limit

    def _current_from_voltage(self, voltage: float) -> float:
        if self.model.kind == "diode":
            return self._diode_current_at_voltage(voltage)
        if self.model.kind == "photodetector":
            photocurrent = -2e-6
            return voltage / self.resistance_ohm + photocurrent
        return voltage / self.resistance_ohm

    def _voltage_from_current(self, current: float) -> float:
        if self.model.kind == "diode":
            # Current-source diode simulation must invert the same I(V) curve
            # used by voltage-source mode.  Search only within the configured
            # voltage-compliance window; unreachable command currents are handled
            # by read_source_and_measure() as compliance-limited actual current.
            target = float(current)
            lo, hi = self._diode_voltage_search_bounds()
            for _ in range(80):
                mid = (lo + hi) / 2.0
                if self._diode_current_at_voltage(mid) < target:
                    lo = mid
                else:
                    hi = mid
            return (lo + hi) / 2.0
        if self.model.kind == "photodetector":
            dark_offset = 2e-6
            return (current + dark_offset) * self.resistance_ohm
        return current * self.resistance_ohm

    def output_on(self) -> None:
        self._output = True

    def output_off(self) -> None:
        self._output = False

    # === SMUDriver Protocol Compatibility Methods ===
    # These methods allow SimulatedKeithley to be used with new SMUDriver-based code

    @property
    def capabilities(self) -> DriverCapabilities:
        """SMUDriver compatibility: expose driver capabilities."""
        return DriverCapabilities(
            name="Debug simulator",
            vendor="HappyMeasure",
            model_family="generic-sim",
            supports_voltage_source=True,
            supports_current_source=True,
            supports_cv=False,
            supports_front_rear=False,
            supports_4wire=True,
            supports_fixed_range=True,
            supports_manual_output=True,
        )

    def connect_profile(self, profile: ConnectionProfile) -> None:
        """SMUDriver compatibility: connect with profile (legacy connect() takes no args)."""
        self._is_open = True

    def disconnect(self) -> None:
        """SMUDriver compatibility: disconnect without closing."""
        # Legacy interface doesn't have separate disconnect
        pass

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
        """SMUDriver compatibility: configure with explicit source/measure modes.

        Maps SMUDriver parameters to legacy SweepConfig format internally.
        """
        from keith_ivt.models import SweepMode

        # Map SourceMode to SweepMode
        sweep_mode = SweepMode.VOLTAGE_SOURCE if source_mode == SourceMode.VOLTAGE else SweepMode.CURRENT_SOURCE

        # Create a minimal SweepConfig from SMUDriver parameters
        config = SweepConfig(
            mode=sweep_mode,
            start=0.0,
            stop=0.0,
            step=0.0,
            compliance=compliance,
            nplc=nplc,
            auto_source_range=autorange and (source_range is None or source_range <= 0),
            auto_measure_range=autorange and (measure_range is None or measure_range <= 0),
            source_range=source_range or 0.0,
            measure_range=measure_range or 0.0,
        )
        self.configure_for_sweep(config)

    def read_smudriver(self) -> DriverReadback:
        """SMUDriver compatibility: read returns DriverReadback instead of tuple."""
        source_val, measured_val = self.read_source_and_measure()
        return DriverReadback(
            source_value=source_val,
            measured_value=measured_val,
            timestamp_s=time.time(),
        )
