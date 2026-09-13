from __future__ import annotations

from pathlib import Path

import pytest

from keith_ivt.core.sweep_runner import SweepRunner
from keith_ivt.data.dataset_store import DatasetStore
from keith_ivt.instrument.serial_2400 import Keithley2400Serial
from keith_ivt.models import SweepConfig, SweepMode, SweepPoint, validate_config
from keith_ivt.services.hardware_preflight import _output_is_off, run_keithley_preflight
from keith_ivt.ui.shutdown_safety import ShutdownSafetyMixin


def _config(**changes) -> SweepConfig:
    values = dict(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=-1.0,
        stop=1.0,
        step=1.0,
        compliance=0.01,
        nplc=0.1,
    )
    values.update(changes)
    return SweepConfig(**values)


def test_fixed_source_range_rejects_requested_setpoint_outside_range() -> None:
    with pytest.raises(ValueError, match="exceeds fixed source range"):
        validate_config(_config(auto_source_range=False, source_range=0.5))


def test_fixed_source_range_accepts_setpoint_on_range_boundary() -> None:
    validate_config(_config(auto_source_range=False, source_range=1.0))


class _OrderMeter:
    def __init__(self) -> None:
        self.events: list[str] = []
        self.value = 0.0

    def reset(self) -> None:
        self.events.append("reset")

    def configure_for_sweep(self, _config) -> None:
        self.events.append("configure")

    def set_source(self, _source_cmd: str, value: float) -> None:
        self.value = float(value)
        self.events.append(f"set:{value}")

    def output_on(self) -> None:
        self.events.append("on")

    def output_off(self) -> None:
        self.events.append("off")

    def read_source_and_measure(self) -> tuple[float, float]:
        self.events.append("read")
        return self.value, self.value * 1e-3


def test_runner_loads_first_setpoint_before_output_on() -> None:
    meter = _OrderMeter()
    result = SweepRunner(meter).run(_config(start=0.1, stop=0.2, step=0.1))
    assert len(result.points) == 2
    assert meter.events.index("set:0.1") < meter.events.index("on")
    assert meter.events.index("on") < meter.events.index("read")


def test_identify_stamps_2401_fast_capability() -> None:
    meter = Keithley2400Serial("COM_FAKE")
    meter.query = lambda _command: "KEITHLEY INSTRUMENTS INC.,MODEL 2401,123,B02"  # type: ignore[method-assign]
    meter.identify()
    assert meter.capabilities.supports_fast_acquisition is True


def test_identify_keeps_2400_standard_only() -> None:
    meter = Keithley2400Serial("COM_FAKE")
    meter.query = lambda _command: "KEITHLEY INSTRUMENTS INC.,MODEL 2400,123,B02"  # type: ignore[method-assign]
    meter.identify()
    assert meter.capabilities.supports_fast_acquisition is False


def test_preflight_output_state_parser_handles_text_and_invalid_reply() -> None:
    assert _output_is_off("OFF") is True
    assert _output_is_off("FALSE") is True
    assert _output_is_off("unexpected") is False


def test_preflight_logger_records_verified_output_state(monkeypatch) -> None:
    class FakeInstrument:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def connect(self) -> None:
            pass

        def output_off(self) -> None:
            pass

        def query(self, command: str) -> str:
            assert command == ":OUTP?"
            return "OFF"

        def identify(self) -> str:
            return "KEITHLEY INSTRUMENTS INC.,MODEL 2401,123,B02"

        def close(self) -> None:
            pass

    monkeypatch.setattr("keith_ivt.services.hardware_preflight.Keithley2400Serial", FakeInstrument)
    messages: list[str] = []
    result = run_keithley_preflight("COM9", logger=messages.append)
    assert result.output_off_confirmed is True
    assert any("Output OFF verified" in message for message in messages)


class _TextVar:
    def __init__(self) -> None:
        self.value = ""

    def set(self, value: str) -> None:
        self.value = value


class _RescueHarness(ShutdownSafetyMixin):
    def __init__(self) -> None:
        self._live_config = _config(device_name="sample")
        self._live_points = [SweepPoint(0.1, 1e-6, elapsed_s=0.2)]
        self._datasets = DatasetStore()
        self._last_result = None
        self._last_backup_path = None
        self._selected_trace_id = None
        self.backup_text = _TextVar()
        self.logs: list[str] = []
        self.refreshed = False
        self.last_save = ""

    def _refresh_trace_list(self) -> None:
        self.refreshed = True

    def _mark_last_save(self, value: str) -> None:
        self.last_save = value

    def log_event(self, message: str) -> None:
        self.logs.append(message)


def test_measurement_error_rescues_partial_points(monkeypatch) -> None:
    app = _RescueHarness()
    monkeypatch.setattr(
        "keith_ivt.ui.shutdown_safety.autosave_result",
        lambda _result: Path("partial-backup.csv"),
    )
    result = app._rescue_partial_result(RuntimeError("read timeout"))
    assert result is not None
    assert len(result.points) == 1
    assert "read timeout" in result.warnings[0]
    assert len(app._datasets.all()) == 1
    assert app.refreshed is True
    assert app.backup_text.value == "Backup: partial-backup.csv"
    assert app.last_save == "error-backup"
