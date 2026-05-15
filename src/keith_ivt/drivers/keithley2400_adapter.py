from __future__ import annotations

from keith_ivt.drivers.base import (
    ConnectionProfile,
    DriverCapabilities,
    DriverReadback,
    MeasureMode,
    SourceMode,
)
from keith_ivt.instrument.serial_2400 import Keithley2400Serial
from keith_ivt.models import SenseMode, SweepConfig, SweepKind, SweepMode, Terminal


class Keithley2400Driver:
    """Adapter from the old Keithley-2400 serial class to the new SMUDriver boundary."""

    capabilities = DriverCapabilities(
        name="Keithley 2400/2401 serial",
        vendor="Keithley",
        model_family="2400",
        supports_cv=False,
        supports_front_rear=True,
        supports_4wire=True,
    )

    def __init__(self) -> None:
        self._profile = ConnectionProfile(debug=False)
        self._config: SweepConfig | None = None
        self._driver: Keithley2400Serial | None = None
        self._source_mode = SourceMode.VOLTAGE
        self._measure_mode = MeasureMode.CURRENT

    def connect(self, profile: ConnectionProfile) -> None:
        self._profile = profile
        self._driver = Keithley2400Serial(port=profile.resource, baud_rate=profile.baud_rate)
        self._driver.connect()

    def disconnect(self) -> None:
        self.close()

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def identify(self) -> str:
        self._require_driver()
        return self._driver.identify()  # type: ignore[union-attr]

    def reset(self) -> None:
        self._require_driver()
        self._driver.reset()  # type: ignore[union-attr]

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
        self._require_driver()
        if measure_mode is MeasureMode.CAPACITANCE:
            raise NotImplementedError("Keithley 2400 adapter does not support CV mode.")
        self._source_mode = source_mode
        self._measure_mode = measure_mode
        cfg = SweepConfig(
            mode=SweepMode.VOLTAGE_SOURCE if source_mode is SourceMode.VOLTAGE else SweepMode.CURRENT_SOURCE,
            start=0.0,
            stop=0.0,
            step=1.0,
            compliance=float(compliance),
            nplc=float(nplc),
            port=self._profile.resource,
            baud_rate=self._profile.baud_rate,
            terminal=Terminal(self._profile.terminal.value),
            sense_mode=SenseMode(self._profile.sense_wiring.value),
            sweep_kind=SweepKind.STEP,
            autorange=autorange,
            auto_source_range=autorange,
            auto_measure_range=autorange,
            source_range=float(source_range or 0.0),
            measure_range=float(measure_range or 0.0),
        )
        self._config = cfg
        self._driver.configure_for_sweep(cfg)  # type: ignore[union-attr]

    def set_source(self, source_mode: SourceMode, value: float) -> None:
        self._require_driver()
        self._driver.set_source(source_mode.value, value)  # type: ignore[union-attr]

    def read(self) -> DriverReadback:
        self._require_driver()
        source, measured = self._driver.read_source_and_measure()  # type: ignore[union-attr]
        return DriverReadback(source_value=source, measured_value=measured)

    def output_on(self) -> None:
        self._require_driver()
        self._driver.output_on()  # type: ignore[union-attr]

    def output_off(self) -> None:
        self._require_driver()
        self._driver.output_off()  # type: ignore[union-attr]

    def _require_driver(self) -> None:
        if self._driver is None:
            raise RuntimeError("Keithley2400Driver is not connected.")

    def __enter__(self) -> "Keithley2400Driver":
        self.connect(self._profile)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if self._driver is not None:
                self.output_off()
        finally:
            self.close()
