from __future__ import annotations

import pytest

from keith_ivt.drivers.command_plan import build_keithley2400_sweep_command_plan
from keith_ivt.instrument import serial_2400
from keith_ivt.instrument.serial_2400 import Keithley2400Serial
from keith_ivt.models import SenseMode, SweepConfig, SweepMode, Terminal


class FakeSerial:
    instances: list["FakeSerial"] = []

    EIGHTBITS = 8
    PARITY_NONE = "N"
    STOPBITS_ONE = 1

    def __init__(self, *args, **kwargs):
        self.commands: list[str] = []
        self.responses: list[bytes] = [b"0.1,0.002\n"]
        self.is_open = True
        FakeSerial.instances.append(self)

    def write(self, data: bytes) -> int:
        self.commands.append(data.decode("ascii").strip())
        return len(data)

    def readline(self) -> bytes:
        return self.responses.pop(0) if self.responses else b"0.1,0.002\n"

    def close(self) -> None:
        self.is_open = False


@pytest.fixture(autouse=True)
def fake_serial_module(monkeypatch):
    FakeSerial.instances.clear()

    class Module:
        Serial = FakeSerial
        EIGHTBITS = FakeSerial.EIGHTBITS
        PARITY_NONE = FakeSerial.PARITY_NONE
        STOPBITS_ONE = FakeSerial.STOPBITS_ONE

    monkeypatch.setattr(serial_2400, "serial", Module)
    yield


def test_voltage_source_command_plan_matches_mock_serial_sequence() -> None:
    cfg = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=-1,
        stop=1,
        step=1,
        compliance=0.01,
        nplc=0.1,
        terminal=Terminal.FRONT,
        sense_mode=SenseMode.FOUR_WIRE,
    )
    meter = Keithley2400Serial("COM_FAKE", retry_policy=None)
    meter.connect()
    meter.reset()
    meter.configure_for_sweep(cfg)
    meter.output_on()
    meter.output_off()

    assert FakeSerial.instances
    assert FakeSerial.instances[-1].commands == build_keithley2400_sweep_command_plan(cfg)


def test_current_source_command_sequence_uses_voltage_compliance_and_measurement() -> None:
    cfg = SweepConfig(
        mode=SweepMode.CURRENT_SOURCE,
        start=-1e-3,
        stop=1e-3,
        step=1e-3,
        compliance=5.0,
        nplc=1.0,
        auto_source_range=False,
        source_range=0.001,
        auto_measure_range=False,
        measure_range=10.0,
    )
    meter = Keithley2400Serial("COM_FAKE", retry_policy=None)
    meter.connect()
    meter.configure_for_sweep(cfg)
    meter.output_on()
    meter.set_source(cfg.source_scpi, 1e-3)
    meter.read_source_and_measure()
    meter.output_off()

    commands = FakeSerial.instances[-1].commands
    assert ":SOUR:FUNC CURR" in commands
    assert ":SENS:FUNC 'VOLT'" in commands
    assert ":SENS:VOLT:PROT 5" in commands
    assert ":SOUR:CURR 0.001" in commands
    assert commands[-2:] == [":READ?", ":OUTP OFF"]
