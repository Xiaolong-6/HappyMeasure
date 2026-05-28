from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from keith_ivt.instrument.base import SourceMeter
from keith_ivt.models import SweepConfig
from keith_ivt.drivers.adapter import SourceMeterAdapter
from keith_ivt.drivers.base import ConnectionProfile, DriverReadback, MeasureMode, SourceMode


class DummyMeter(SourceMeter):
    def __init__(self):
        self.connected = False
        self.closed = False
        self.output_on_count = 0
        self.output_off_count = 0

    def connect(self) -> None:
        self.connected = True

    def close(self) -> None:
        self.closed = True

    def identify(self) -> str:
        return "DUMMY"

    def reset(self) -> None:
        pass

    def configure_for_sweep(self, config: SweepConfig) -> None:
        pass

    def set_source(self, source_cmd: str, value: float) -> None:
        pass

    def read_source_and_measure(self) -> tuple[float, float]:
        return (1.0, 0.001)

    def output_on(self) -> None:
        self.output_on_count += 1

    def output_off(self) -> None:
        self.output_off_count += 1


def test_source_meter_base_autorange_not_supported() -> None:
    meter = DummyMeter()
    import pytest
    with pytest.raises(NotImplementedError, match="not supported"):
        meter.get_current_autorange()
    with pytest.raises(NotImplementedError, match="not supported"):
        meter.set_current_autorange(True)
    with pytest.raises(NotImplementedError, match="not supported"):
        meter.get_current_range()
    with pytest.raises(NotImplementedError, match="not supported"):
        meter.set_current_range(1e-3)


def test_source_meter_context_manager() -> None:
    meter = DummyMeter()
    with meter:
        assert meter.connected is True
    assert meter.output_off_count == 1
    assert meter.closed is True


def test_source_meter_context_manager_with_exception() -> None:
    meter = DummyMeter()
    try:
        with meter:
            raise ValueError("test")
    except ValueError:
        pass
    assert meter.output_off_count == 1
    assert meter.closed is True


def test_source_meter_adapter_capabilities() -> None:
    meter = DummyMeter()
    adapter = SourceMeterAdapter(meter)
    caps = adapter.capabilities
    assert caps.name == "Legacy SourceMeter (adapted)"
    assert caps.supports_voltage_source is True
    assert caps.supports_current_source is True


def test_source_meter_adapter_connect_and_identify() -> None:
    meter = DummyMeter()
    adapter = SourceMeterAdapter(meter)
    adapter.connect(ConnectionProfile())
    assert meter.connected is True
    assert adapter.identify() == "DUMMY"


def test_source_meter_adapter_reset() -> None:
    meter = DummyMeter()
    adapter = SourceMeterAdapter(meter)
    adapter.connect(ConnectionProfile())
    adapter.reset()


def test_source_meter_adapter_configure() -> None:
    meter = DummyMeter()
    adapter = SourceMeterAdapter(meter)
    adapter.connect(ConnectionProfile())
    adapter.configure_source_measure(
        SourceMode.VOLTAGE,
        MeasureMode.CURRENT,
        compliance=1.0,
        nplc=1.0,
    )


def test_source_meter_adapter_read() -> None:
    meter = DummyMeter()
    adapter = SourceMeterAdapter(meter)
    adapter.connect(ConnectionProfile())
    result = adapter.read()
    assert isinstance(result, DriverReadback)
    assert result.source_value == 1.0


def test_source_meter_adapter_output_on_off() -> None:
    meter = DummyMeter()
    adapter = SourceMeterAdapter(meter)
    adapter.connect(ConnectionProfile())
    adapter.output_on()
    adapter.output_off()
    assert meter.output_on_count == 1
    assert meter.output_off_count == 1


def test_source_meter_adapter_close() -> None:
    meter = DummyMeter()
    adapter = SourceMeterAdapter(meter)
    adapter.connect(ConnectionProfile())
    adapter.close()
    assert meter.output_off_count == 1
    assert meter.closed is True


def test_source_meter_adapter_disconnect() -> None:
    meter = DummyMeter()
    adapter = SourceMeterAdapter(meter)
    adapter.disconnect()


def test_source_meter_adapter_context_manager() -> None:
    meter = DummyMeter()
    adapter = SourceMeterAdapter(meter)
    with adapter:
        assert meter.connected is True
    assert meter.closed is True


def test_source_meter_adapter_set_source() -> None:
    meter = DummyMeter()
    adapter = SourceMeterAdapter(meter)
    adapter.connect(ConnectionProfile())
    adapter.set_source(SourceMode.VOLTAGE, 2.5)


def test_services_lazy_import() -> None:
    import keith_ivt.services as svc
    ms = svc.MeasurementService
    assert ms is not None


def test_services_lazy_import_unknown() -> None:
    import keith_ivt.services as svc
    import pytest
    with pytest.raises(AttributeError):
        _ = svc.UnknownAttribute
