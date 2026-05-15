from __future__ import annotations

import time
from typing import Optional

from keith_ivt.instrument.base import SourceMeter
from keith_ivt.services.serial_safety import OutputOffGuard, SerialRetryPolicy
from keith_ivt.models import SenseMode, SweepConfig, Terminal

try:
    import serial
except ImportError as exc:  # pragma: no cover
    serial = None
    _SERIAL_IMPORT_ERROR = exc
else:
    _SERIAL_IMPORT_ERROR = None


class Keithley2400Serial(SourceMeter):
    """Minimal RS-232 driver for Keithley 2400-series SourceMeter units."""

    def __init__(self, port: str, baud_rate: int = 9600, timeout: float = 20.0, retry_policy: SerialRetryPolicy | None = None):
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.retry_policy = retry_policy or SerialRetryPolicy()
        self._ser: Optional["serial.Serial"] = None

    def connect(self) -> None:
        if serial is None:
            raise RuntimeError("pyserial is not installed. Run: pip install pyserial") from _SERIAL_IMPORT_ERROR
        self._ser = serial.Serial(
            port=self.port,
            baudrate=self.baud_rate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=self.timeout,
            write_timeout=self.timeout,
        )

    def close(self) -> None:
        if self._ser is not None and self._ser.is_open:
            self._ser.close()

    def _write_once(self, command: str) -> None:
        if self._ser is None:
            raise RuntimeError("Serial port is not open.")
        self._ser.write((command + "\r\n").encode("ascii"))

    def write(self, command: str) -> None:
        self.retry_policy.run(lambda: self._write_once(command), label=f"write {command!r}")

    def _query_once(self, command: str) -> str:
        self._write_once(command)
        if self._ser is None:
            raise RuntimeError("Serial port is not open.")
        raw = self._ser.readline().decode("ascii", errors="replace").strip()
        if not raw:
            raise TimeoutError(f"No response for command: {command}")
        return raw

    def query(self, command: str) -> str:
        return self.retry_policy.run(lambda: self._query_once(command), label=f"query {command!r}")

    def identify(self) -> str:
        return self.query("*IDN?")

    def reset(self) -> None:
        self.write("*RST")
        time.sleep(1.0)
        self.write(":OUTP OFF")

    def configure_for_sweep(self, config: SweepConfig) -> None:
        src = config.source_scpi
        meas = config.measure_scpi
        self.write(f":ROUT:TERM {config.terminal.value}")
        self.write(":SYST:RSEN ON" if config.sense_mode is SenseMode.FOUR_WIRE else ":SYST:RSEN OFF")
        self.write(f":SOUR:FUNC {src}")
        self.write(f":SENS:FUNC '{meas}'")
        self.write(f":SENS:{meas}:PROT {config.compliance:.12g}")
        self.write(f":SENS:{meas}:NPLC {config.nplc:.12g}")
        if config.auto_source_range:
            self.write(f":SOUR:{src}:RANG:AUTO ON")
        else:
            self.write(f":SOUR:{src}:RANG:AUTO OFF")
            self.write(f":SOUR:{src}:RANG {config.source_range:.12g}")
        if config.auto_measure_range:
            self.write(f":SENS:{meas}:RANG:AUTO ON")
        else:
            self.write(f":SENS:{meas}:RANG:AUTO OFF")
            self.write(f":SENS:{meas}:RANG {config.measure_range:.12g}")
        self.write(f":FORM:ELEM {src},{meas}")

    def set_source(self, source_cmd: str, value: float) -> None:
        self.write(f":SOUR:{source_cmd} {value:.12g}")

    def read_source_and_measure(self) -> tuple[float, float]:
        raw = self.query(":READ?")
        # Keithley returns comma-separated ASCII values when FORM:ELEM has two fields.
        parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
        numbers = [float(p) for p in parts[:2]]
        if len(numbers) < 2:
            raise ValueError(f"Could not parse source/measure pair from response: {raw!r}")
        return numbers[0], numbers[1]

    def output_on(self) -> None:
        self.write(":OUTP ON")

    def output_off(self) -> None:
        OutputOffGuard().turn_off(lambda: self.write(":OUTP OFF"), context="Keithley2400Serial.output_off")
