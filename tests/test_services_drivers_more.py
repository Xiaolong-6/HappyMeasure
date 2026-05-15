from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_simulated_smu_driver_iv_cv_and_context(monkeypatch):
    import keith_ivt.drivers.simulated_smu as sim
    from keith_ivt.drivers.base import ConnectionProfile, MeasureMode, SourceMode

    monkeypatch.setattr(sim.time, "sleep", lambda _s: None)
    monkeypatch.setattr(sim.random, "gauss", lambda _mu, _sigma: 0.0)
    drv = sim.SimulatedSMUDriver(resistance_ohm=1000, capacitance_f=2e-9, noise_fraction=0)
    with drv:
        assert drv.connected is True
        assert "HAPPYMEASURE" in drv.identify()
        drv.configure_source_measure(SourceMode.VOLTAGE, MeasureMode.CURRENT, compliance=1, nplc=1)
        drv.output_on(); assert drv.output_enabled is True
        drv.set_source(SourceMode.VOLTAGE, 2.0)
        r = drv.read()
        assert r.source_value == 2.0
        assert r.measured_value == pytest.approx(2e-3)
        drv.configure_source_measure(SourceMode.VOLTAGE, MeasureMode.CAPACITANCE, compliance=1, nplc=1)
        assert drv.read().measured_value > 0
    assert drv.connected is False
    assert drv.output_enabled is False


def test_measurement_service_runs_and_turns_output_off(monkeypatch):
    import keith_ivt.services.measurement_service as ms
    from keith_ivt.drivers.base import DriverReadback, MeasureMode, SourceMode
    from keith_ivt.models import SweepConfig, SweepKind, SweepMode
    from keith_ivt.services.measurement_service import MeasurementService
    from keith_ivt.sweeps.plan import SweepExecutionKind, SweepPlan

    monkeypatch.setattr(ms.time, "sleep", lambda _s: None)

    class FakeDriver:
        def __init__(self):
            self.calls = []
            self.current = 0.0
        def reset(self): self.calls.append("reset")
        def configure_source_measure(self, **kwargs): self.calls.append(("configure", kwargs))
        def output_on(self): self.calls.append("on")
        def output_off(self): self.calls.append("off")
        def set_source(self, source_mode, value): self.calls.append(("set", value)); self.current = value
        def read(self): return DriverReadback(self.current, self.current * 2)

    drv = FakeDriver()
    plan = SweepPlan(
        execution_kind=SweepExecutionKind.STEP,
        values=[0.0, 1.0, 2.0],
        source_mode=SourceMode.VOLTAGE,
        measure_mode=MeasureMode.CURRENT,
        compliance=1.0,
        nplc=0.01,
        autorange=True,
    )
    reads = MeasurementService(drv).run_plan(plan)
    assert [r.measured_value for r in reads] == [0.0, 2.0, 4.0]
    assert drv.calls[0] == "reset"
    assert drv.calls[-1] == "off"

    cfg = SweepConfig(mode=SweepMode.VOLTAGE_SOURCE, start=0, stop=1, step=1, compliance=1, nplc=0.01, sweep_kind=SweepKind.STEP)
    result = MeasurementService(FakeDriver()).run_legacy_config(cfg)
    assert len(result.points) == 2

    manual = SweepPlan(
        execution_kind=SweepExecutionKind.MANUAL_OUTPUT,
        values=[0.0],
        source_mode=SourceMode.VOLTAGE,
        measure_mode=MeasureMode.CURRENT,
        compliance=1.0,
        nplc=0.01,
        autorange=True,
    )
    with pytest.raises(ValueError):
        MeasurementService(FakeDriver()).run_plan(manual)


def test_keithley_driver_adapter_uses_serial_backend(monkeypatch):
    from keith_ivt.drivers import keithley2400_adapter as mod
    from keith_ivt.drivers.base import ConnectionProfile, MeasureMode, SourceMode

    class FakeSerial:
        instances = []
        def __init__(self, port, baud_rate):
            self.port = port; self.baud_rate = baud_rate; self.config = None; self.closed = False
            FakeSerial.instances.append(self)
        def connect(self): pass
        def close(self): self.closed = True
        def identify(self): return "KEITHLEY,MODEL 2400,1,2"
        def reset(self): pass
        def configure_for_sweep(self, cfg): self.config = cfg
        def set_source(self, source_cmd, value): self.source = (source_cmd, value)
        def read_source_and_measure(self): return (1.0, 2.0)
        def output_on(self): self.on = True
        def output_off(self): self.off = True

    monkeypatch.setattr(mod, "Keithley2400Serial", FakeSerial)
    drv = mod.Keithley2400Driver()
    drv.connect(ConnectionProfile(resource="COM8", baud_rate=19200, debug=False))
    assert drv.identify().startswith("KEITHLEY")
    drv.configure_source_measure(SourceMode.CURRENT, MeasureMode.VOLTAGE, compliance=3, nplc=1, autorange=False, source_range=0.01, measure_range=10)
    fake = FakeSerial.instances[-1]
    assert fake.config.port == "COM8"
    assert fake.config.baud_rate == 19200
    drv.set_source(SourceMode.CURRENT, 1e-3)
    assert drv.read().measured_value == 2.0
    drv.output_on(); drv.output_off(); drv.close()
    assert fake.closed is True
    with pytest.raises(RuntimeError):
        drv.identify()


def test_serial_2400_with_fake_serial(monkeypatch):
    from keith_ivt.instrument import serial_2400 as mod
    from keith_ivt.models import SweepConfig, SweepMode

    class FakePort:
        EIGHTBITS = 8; PARITY_NONE = "N"; STOPBITS_ONE = 1
        def __init__(self):
            self.commands = []
            self.responses = [b"KEITHLEY,MODEL 2400,1,2\n", b"1.0,0.002\n"]
            self.is_open = True
        def write(self, data): self.commands.append(data.decode().strip())
        def readline(self): return self.responses.pop(0)
        def close(self): self.is_open = False
    port = FakePort()
    class FakeSerialModule:
        EIGHTBITS = FakePort.EIGHTBITS; PARITY_NONE = FakePort.PARITY_NONE; STOPBITS_ONE = FakePort.STOPBITS_ONE
        def Serial(self, **kwargs): return port
    monkeypatch.setattr(mod, "serial", FakeSerialModule())
    inst = mod.Keithley2400Serial("COM1", retry_policy=mod.SerialRetryPolicy(max_attempts=1))
    inst.connect()
    assert inst.identify().startswith("KEITHLEY")
    cfg = SweepConfig(mode=SweepMode.VOLTAGE_SOURCE, start=0, stop=0, step=1, compliance=0.01, nplc=1)
    inst.configure_for_sweep(cfg)
    inst.set_source("VOLT", 1.0)
    assert inst.read_source_and_measure() == (1.0, 0.002)
    inst.output_on(); inst.output_off(); inst.close()
    assert any(cmd == ":OUTP OFF" for cmd in port.commands)
    assert port.is_open is False


def test_formatting_helpers():
    from keith_ivt.utils.formatting import format_current, format_resistance, format_si, format_voltage
    assert format_si(0, "V") == "0 V"
    assert "mV" in format_voltage(1e-3)
    assert "µA" in format_current(2e-6)
    assert "kΩ" in format_resistance(1200)
    assert format_si("bad", "V") == "bad V"
