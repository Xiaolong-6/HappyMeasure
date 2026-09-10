from __future__ import annotations

import math
import time
from importlib import import_module
from typing import Any, Optional

from keith_ivt.acquisition import resolve_time_acquisition
from keith_ivt.instrument.base import SourceMeter
from keith_ivt.services.serial_safety import OutputOffGuard, SerialRetryPolicy
from keith_ivt.models import SenseMode, SweepConfig, SweepKind

_SERIAL_IMPORT_ERROR: ImportError | None
_KEITHLEY_OVERFLOW_SENTINEL = 9.91e37
_KEITHLEY_OVERFLOW_TOLERANCE = 0.01e37
try:
    serial: Any = import_module("serial")
except ImportError as exc:  # pragma: no cover
    serial = None
    _SERIAL_IMPORT_ERROR = exc
else:
    _SERIAL_IMPORT_ERROR = None


class Keithley2400Serial(SourceMeter):
    """Minimal RS-232 driver for Keithley 2400-series SourceMeter units."""

    def __init__(
        self,
        port: str,
        baud_rate: int = 9600,
        timeout: float = 20.0,
        retry_policy: SerialRetryPolicy | None = None,
    ):
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.retry_policy = retry_policy or SerialRetryPolicy()
        self._ser: Optional["serial.Serial"] = None
        self._measurement_only_read = False
        self._range_telemetry = True
        self._cached_source_cmd = "VOLT"
        self._cached_source_value = 0.0
        self._cached_autorange = True
        self._cached_measure_range = 0.0
        self._restore_fast_settings = False

    def connect(self) -> None:
        if serial is None:
            raise RuntimeError(
                "pyserial is not installed. Run: pip install pyserial"
            ) from _SERIAL_IMPORT_ERROR
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
        if self._restore_fast_settings and self._ser is not None and self._ser.is_open:
            self._restore_fast_acquisition_settings()
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

    def beep(self, frequency_hz: float = 1000.0, duration_s: float = 0.1) -> None:
        frequency = float(frequency_hz)
        duration = float(duration_s)
        if not math.isfinite(frequency) or frequency <= 0:
            raise ValueError("Beep frequency must be finite and positive.")
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("Beep duration must be finite and positive.")
        frequency = min(max(frequency, 100.0), 10_000.0)
        duration = min(max(duration, 0.01), 1.0)

        status = self.query(":SYST:BEEP:STAT?").strip().upper()
        if status in {"1", "+1", "ON", "TRUE"}:
            restore_disabled = False
        elif status in {"0", "OFF", "FALSE"}:
            self.write(":SYST:BEEP:STAT ON")
            restore_disabled = True
        else:
            raise ValueError(f"Unexpected beeper status: {status!r}")

        try:
            self.write(f":SYST:BEEP {frequency:.12g},{duration:.12g}")
        finally:
            if restore_disabled:
                self.write(":SYST:BEEP:STAT OFF")

    def reset(self) -> None:
        self.write("*RST")
        time.sleep(1.0)
        self.write(":OUTP OFF")

    def configure_for_sweep(self, config: SweepConfig) -> None:
        src = config.source_scpi
        meas = config.measure_scpi
        acquisition = resolve_time_acquisition(config)
        self._measurement_only_read = bool(acquisition.measurement_only_read)
        self._range_telemetry = bool(acquisition.range_telemetry)
        self._cached_source_cmd = src
        self._cached_source_value = float(config.constant_value)
        self._cached_autorange = bool(config.auto_measure_range)
        self._cached_measure_range = float(config.measure_range)
        self._restore_fast_settings = bool(acquisition.apply_instrument_overrides)

        self.write(f":ROUT:TERM {config.terminal.value}")
        self.write(
            ":SYST:RSEN ON" if config.sense_mode is SenseMode.FOUR_WIRE else ":SYST:RSEN OFF"
        )
        self.write(f":SOUR:FUNC {src}")
        self.write(f":SENS:FUNC '{meas}'")
        self.write(f":SENS:{meas}:PROT {config.compliance:.12g}")
        self.write(f":SENS:{meas}:NPLC {acquisition.nplc:.12g}")
        self.write(":SOUR:DEL:AUTO OFF")
        self.write(":SOUR:DEL 0")
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

        if acquisition.apply_instrument_overrides:
            self.write(f":TRIG:DEL {acquisition.trigger_delay_s:.12g}")
            self.write(
                f":SENS:FUNC:CONC {'ON' if acquisition.concurrent_measurement else 'OFF'}"
            )
            # On a 2400-series SMU, changing concurrent-function state can
            # replace the selected function. Restore the configured quantity
            # after that command; this is setup-only, never a Fast hot-path write.
            self.write(f":SENS:FUNC '{meas}'")
            if acquisition.digital_filter:
                self.write(":SENS:AVER:TCON REP")
                self.write(f":SENS:AVER:COUN {int(acquisition.digital_filter_count)}")
                self.write(":SENS:AVER:STAT ON")
            else:
                self.write(":SENS:AVER:STAT OFF")
            self.write(f":DISP:ENAB {'ON' if acquisition.display_during_run else 'OFF'}")
            if acquisition.zero_refresh_before_run:
                self.write(":SYST:AZER:STAT ONCE")
                self.write("*WAI")
            self.write(f":SYST:AZER:STAT {'ON' if acquisition.autozero_during_run else 'OFF'}")

        if config.sweep_kind is SweepKind.CONSTANT_TIME and acquisition.measurement_only_read:
            self.write(f":FORM:ELEM {meas}")
        else:
            self.write(f":FORM:ELEM {src},{meas}")

        # Telemetry-off mode deliberately snapshots range only at setup. The
        # runner can still call its existing range-state API, but those calls
        # hit the cache rather than adding AUTO?/RANGE? serial queries per point.
        if not self._range_telemetry and config.auto_measure_range:
            try:
                self._cached_measure_range = float(self.query(f":SENS:{meas}:RANG?"))
            except Exception:
                self._cached_measure_range = float(config.measure_range)

    def set_source(self, source_cmd: str, value: float) -> None:
        self._cached_source_cmd = str(source_cmd)
        self._cached_source_value = float(value)
        self.write(f":SOUR:{source_cmd} {value:.12g}")

    def read_source_and_measure(self) -> tuple[float, float]:
        raw = self.query(":READ?")
        parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
        numbers = [float(p) for p in parts]
        if self._measurement_only_read:
            if not numbers:
                raise ValueError(f"Could not parse measurement from response: {raw!r}")
            return self._cached_source_value, self._normalise_measurement(numbers[0])
        if len(numbers) < 2:
            raise ValueError(f"Could not parse source/measure pair from response: {raw!r}")
        return numbers[0], self._normalise_measurement(numbers[1])

    @staticmethod
    def _normalise_measurement(value: float) -> float:
        """Convert only the documented Keithley overflow sentinel to NaN."""

        numeric = float(value)
        if abs(abs(numeric) - _KEITHLEY_OVERFLOW_SENTINEL) <= _KEITHLEY_OVERFLOW_TOLERANCE:
            return math.nan
        return numeric

    def output_on(self) -> None:
        self.write(":OUTP ON")

    def _restore_fast_acquisition_settings(self) -> None:
        if not self._restore_fast_settings:
            return
        for command in (
            ":SENS:AVER:STAT OFF",
            ":SYST:AZER:STAT ON",
            ":DISP:ENAB ON",
        ):
            try:
                self.write(command)
            except Exception:
                pass
        self._restore_fast_settings = False
        self._measurement_only_read = False
        self._range_telemetry = True

    def output_off(self) -> None:
        OutputOffGuard().turn_off(
            lambda: self.write(":OUTP OFF"), context="Keithley2400Serial.output_off"
        )
        self._restore_fast_acquisition_settings()

    def get_current_autorange(self) -> bool:
        if not self._range_telemetry:
            return bool(self._cached_autorange)
        raw = self.query(":SENS:CURR:RANG:AUTO?")
        value = raw.strip().upper() in {"1", "ON", "TRUE"}
        self._cached_autorange = value
        return value

    def set_current_autorange(self, enabled: bool) -> None:
        # A setter stays a single write: range snapshots belong to
        # configure_for_sweep, set_current_range, and get_current_range so the
        # historical command sequence — and the Fast hot path — gain no query.
        self.write(f":SENS:CURR:RANG:AUTO {'ON' if enabled else 'OFF'}")
        self._cached_autorange = bool(enabled)

    def get_current_range(self) -> float:
        if not self._range_telemetry:
            return float(self._cached_measure_range)
        value = float(self.query(":SENS:CURR:RANG?"))
        self._cached_measure_range = value
        return value

    def set_current_range(self, range_A: float) -> None:
        value = float(range_A)
        self.write(f":SENS:CURR:RANG {value:.12g}")
        self._cached_measure_range = value
