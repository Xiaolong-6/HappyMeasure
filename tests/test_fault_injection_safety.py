from __future__ import annotations

import pytest

from keith_ivt.core.sweep_runner import SweepRunner
from keith_ivt.drivers.base import DriverCapabilities, DriverReadback, MeasureMode, SourceMode
from keith_ivt.instrument.simulator import SimulatedKeithley, SimulatorFaultProfile
from keith_ivt.models import SweepConfig, SweepKind, SweepMode
from keith_ivt.services.measurement_service import MeasurementService
from keith_ivt.sweeps.plan import SweepExecutionKind, SweepPlan
from keith_ivt.ui.app_state import AppAction, AppState, ConnectionState, RunState


def _config(**kwargs) -> SweepConfig:
    params = dict(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0.0,
        stop=3.0,
        step=1.0,
        compliance=0.01,
        nplc=0.01,
        sweep_kind=SweepKind.STEP,
        output_off_after_run=True,
    )
    params.update(kwargs)
    return SweepConfig(**params)


def test_fault_injection_connect_failure_is_deterministic():
    inst = SimulatedKeithley(fault_profile=SimulatorFaultProfile(connect_error="simulated connect timeout"))

    with pytest.raises(RuntimeError, match="simulated connect timeout"):
        inst.connect()

    assert inst.events == ["connect"]
    assert inst._is_open is False


def test_fault_injection_read_failure_enters_safety_output_off_path(monkeypatch):
    import keith_ivt.instrument.simulator as sim

    monkeypatch.setattr(sim.time, "sleep", lambda _s: None)
    inst = SimulatedKeithley(fault_profile=SimulatorFaultProfile(read_error_at=2))

    with pytest.raises(RuntimeError, match="simulated read failure at point 2"):
        SweepRunner(inst).run(_config())

    assert "output_on" in inst.events
    assert "output_off" in inst.events
    assert inst.events.index("output_off") > inst.events.index("read")
    assert inst._output is False


def test_non_finite_simulator_readback_is_rejected_and_safed(monkeypatch):
    import keith_ivt.instrument.simulator as sim

    monkeypatch.setattr(sim.time, "sleep", lambda _s: None)
    inst = SimulatedKeithley(fault_profile=SimulatorFaultProfile(nan_read_at=1))

    with pytest.raises(RuntimeError, match="Non-finite measurement readback"):
        SweepRunner(inst).run(_config())

    assert "output_off" in inst.events
    assert inst._output is False


def test_output_off_failure_preserves_non_finite_root_cause(monkeypatch):
    import keith_ivt.instrument.simulator as sim

    monkeypatch.setattr(sim.time, "sleep", lambda _s: None)
    inst = SimulatedKeithley(
        fault_profile=SimulatorFaultProfile(
            inf_read_at=1,
            output_off_error="simulated output-off timeout",
        )
    )

    with pytest.raises(RuntimeError) as err:
        SweepRunner(inst).run(_config())

    message = str(err.value)
    assert "Non-finite measurement readback" in message
    assert "simulated output-off timeout" in message
    assert err.value.__cause__ is not None


class FaultyDriver:
    capabilities = DriverCapabilities(name="Faulty driver")

    def __init__(self, *, read: DriverReadback | None = None, fail_read: bool = False, fail_output_off: bool = False) -> None:
        self.readback = read or DriverReadback(source_value=0.0, measured_value=1.0)
        self.fail_read = fail_read
        self.fail_output_off = fail_output_off
        self.events: list[str] = []
        self.output_enabled = False

    def connect(self, profile):
        self.events.append("connect")

    def disconnect(self):
        self.events.append("disconnect")

    def identify(self) -> str:
        return "FAULTY"

    def reset(self) -> None:
        self.events.append("reset")

    def configure_source_measure(self, **kwargs) -> None:
        self.events.append("configure")

    def output_on(self) -> None:
        self.output_enabled = True
        self.events.append("output_on")

    def set_source(self, source_mode, value: float) -> None:
        self.events.append(f"set:{value}")

    def read(self) -> DriverReadback:
        self.events.append("read")
        if self.fail_read:
            raise RuntimeError("driver read timeout")
        return self.readback

    def output_off(self) -> None:
        self.events.append("output_off")
        if self.fail_output_off:
            raise RuntimeError("driver output-off timeout")
        self.output_enabled = False

    def close(self) -> None:
        self.events.append("close")


def _plan() -> SweepPlan:
    return SweepPlan(
        execution_kind=SweepExecutionKind.STEP,
        source_mode=SourceMode.VOLTAGE,
        measure_mode=MeasureMode.CURRENT,
        values=[0.0, 1.0],
        compliance=0.01,
        nplc=0.01,
        autorange=True,
    )


def test_measurement_service_rejects_non_finite_driver_readback():
    driver = FaultyDriver(read=DriverReadback(source_value=0.0, measured_value=float("nan")))

    with pytest.raises(RuntimeError, match="Non-finite measurement readback"):
        MeasurementService(driver).run_plan(_plan())

    assert "output_off" in driver.events
    assert driver.output_enabled is False


def test_measurement_service_preserves_read_error_when_output_off_fails():
    driver = FaultyDriver(fail_read=True, fail_output_off=True)

    with pytest.raises(RuntimeError) as err:
        MeasurementService(driver).run_plan(_plan())

    message = str(err.value)
    assert "driver read timeout" in message
    assert "driver output-off timeout" in message
    assert err.value.__cause__ is not None


def test_app_state_can_restart_after_aborted_when_still_connected():
    state = AppState()
    assert state.dispatch(AppAction.CONNECT_SIMULATED, device_id="sim", device_model="Debug simulator")
    assert state.dispatch(AppAction.START_SWEEP)
    assert state.dispatch(AppAction.ABORT_SWEEP)

    assert state.run_state is RunState.ABORTED
    assert state.connection_state is ConnectionState.SIMULATED
    assert state.can_start_sweep() is True
