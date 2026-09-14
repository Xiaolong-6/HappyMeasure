from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from keith_ivt.drivers.base import instrument_model_from_idn
from keith_ivt.instrument.serial_2400 import Keithley2400Serial
from keith_ivt.services.serial_safety import SerialRetryPolicy

# Keep discovery aligned with the baud choices currently exposed by HappyMeasure.
APP_SUPPORTED_BAUD_RATES = (9600, 19200, 38400, 57600)
SUPPORTED_2400_MODELS = frozenset({"2400", "2401", "2410", "2420", "2430", "2440"})
DISCOVERY_TIMEOUT_S = 0.45


@dataclass(frozen=True)
class SerialDiscoveryResult:
    port: str
    baud_rate: int
    idn: str
    model: str


def available_serial_ports() -> list[str]:
    """Return serial device names reported by pyserial without inventing fallbacks."""

    try:
        from serial.tools import list_ports

        return [str(port.device) for port in list_ports.comports() if str(port.device).strip()]
    except Exception:
        return []


def _ordered_unique(values: Iterable[str | int], preferred: str | int | None) -> list:
    ordered: list = []
    if preferred is not None:
        ordered.append(preferred)
    for value in values:
        if value not in ordered:
            ordered.append(value)
    return ordered


def probe_serial_identity(port: str, baud_rate: int) -> str:
    """Perform one short, read-only SCPI identity probe.

    Discovery intentionally sends only ``*IDN?``. It does not reset the
    instrument, alter source configuration, enable output, or acquire a reading.
    """

    retry_policy = SerialRetryPolicy(max_attempts=1, base_delay_s=0.0)
    with Keithley2400Serial(
        port=port,
        baud_rate=int(baud_rate),
        timeout=DISCOVERY_TIMEOUT_S,
        retry_policy=retry_policy,
    ) as inst:
        return inst.identify()


def supported_2400_identity(idn: str) -> tuple[bool, str]:
    text = str(idn or "").upper()
    model = instrument_model_from_idn(idn)
    return "KEITHLEY" in text and model in SUPPORTED_2400_MODELS, model


def discover_supported_serial_hardware(
    *,
    preferred_port: str | None = None,
    preferred_baud: int | None = None,
    ports: Iterable[str] | None = None,
    baud_rates: Iterable[int] = APP_SUPPORTED_BAUD_RATES,
    probe: Callable[[str, int], str] = probe_serial_identity,
) -> SerialDiscoveryResult | None:
    """Find the first supported Keithley 2400-family serial instrument.

    The current user selection is tried first so the normal fast path requires
    only one identity query. Other detected COM ports and HappyMeasure-supported
    baud rates are then scanned deterministically.
    """

    candidates = list(ports) if ports is not None else available_serial_ports()
    ordered_ports = _ordered_unique(candidates, preferred_port)
    ordered_bauds = _ordered_unique(
        [int(value) for value in baud_rates],
        int(preferred_baud) if preferred_baud is not None else None,
    )

    for port in ordered_ports:
        if not str(port).strip():
            continue
        for baud_rate in ordered_bauds:
            try:
                idn = probe(str(port), int(baud_rate))
            except Exception:
                continue
            supported, model = supported_2400_identity(idn)
            if supported:
                return SerialDiscoveryResult(
                    port=str(port),
                    baud_rate=int(baud_rate),
                    idn=idn,
                    model=model,
                )
    return None
