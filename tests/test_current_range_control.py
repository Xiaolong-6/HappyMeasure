from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from keith_ivt.core.current_range import CurrentRangeControl, CurrentRangeState
from keith_ivt.core.sweep_runner import SweepRunner
from keith_ivt.data.exporters import save_csv
from keith_ivt.instrument.base import SourceMeter
from keith_ivt.instrument.simulator import SimulatedKeithley
from keith_ivt.models import SweepConfig, SweepKind, SweepMode


def test_current_range_state_formats_autorange_actual_range() -> None:
    state = CurrentRangeState(autorange=True, actual_range_A=1e-9)

    assert state.headline() == "Current range: AUTO, actual 1 nA"
    assert state.status_fragment() == "Auto/1 nA"


class RangeMeter(SourceMeter):
    def __init__(self, *, change_on_read: int | None = None):
        self.events: list[str] = []
        self.range_A = 1e-9
        self.autorange = True
        self.read_count = 0
        self.change_on_read = change_on_read

    def connect(self) -> None: pass
    def close(self) -> None: pass
    def identify(self) -> str: return "RANGE-METER"
    def reset(self) -> None: self.events.append("reset")
    def configure_for_sweep(self, config: SweepConfig) -> None: self.events.append("configure")
    def set_source(self, source_cmd: str, value: float) -> None: self.events.append(f"source:{value}")
    def output_on(self) -> None: self.events.append("output_on")
    def output_off(self) -> None: self.events.append("output_off")
    def get_current_autorange(self) -> bool: return self.autorange
    def set_current_autorange(self, enabled: bool) -> None:
        self.events.append(f"autorange:{enabled}")
        self.autorange = bool(enabled)
    def get_current_range(self) -> float: return self.range_A
    def set_current_range(self, range_A: float) -> None:
        self.events.append(f"range:{range_A}")
        self.range_A = float(range_A)
    def read_source_and_measure(self) -> tuple[float, float]:
        self.read_count += 1
        if self.change_on_read == self.read_count:
            self.range_A = 10e-9
        measured = 100.0 if self.read_count in {2, 3} else float(self.read_count)
        return float(self.read_count), measured


def _time_config(**overrides) -> SweepConfig:
    params = dict(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=0.0,
        stop=3.0,
        step=1.0,
        compliance=1.0,
        nplc=0.1,
        sweep_kind=SweepKind.STEP,
        range_settle_delay_ms=0,
        discard_after_range_change=2,
    )
    params.update(overrides)
    return SweepConfig(**params)


def test_lock_current_range_uses_actual_range_and_disables_autorange() -> None:
    meter = RangeMeter()
    control = CurrentRangeControl()
    control.request_lock_current()

    SweepRunner(meter).run(_time_config(stop=0.0, discard_after_range_change=0), current_range_control=control)

    assert "autorange:False" in meter.events
    assert "range:1e-09" in meter.events
    assert control.snapshot().autorange is False
    assert control.snapshot().fixed_range_A == 1e-9


def test_fixed_range_selection_disables_autorange_before_setting_range() -> None:
    meter = RangeMeter()
    control = CurrentRangeControl()
    control.request_fixed_range(10e-9)

    SweepRunner(meter).run(_time_config(stop=0.0, discard_after_range_change=0), current_range_control=control)

    assert meter.events.index("autorange:False") < meter.events.index("range:1e-08")
    assert control.snapshot().status_fragment() == "Fixed/10 nA"


def test_range_change_discards_bad_points_before_trace_and_csv() -> None:
    meter = RangeMeter(change_on_read=2)
    control = CurrentRangeControl()

    result = SweepRunner(meter).run(_time_config(), current_range_control=control)

    assert [point.measured_value for point in result.points] == [1.0, 4.0]
    path = save_csv(result, ROOT / "logs" / "range_filtered_test.csv")
    rows = [line.split(",") for line in path.read_text(encoding="utf-8").splitlines() if line and not line.startswith("#")][1:]
    measured_values = [float(row[2]) for row in rows]
    assert 100.0 not in measured_values
    assert control.snapshot().actual_range_A == 10e-9
    assert control.snapshot().last_change_monotonic_s is not None


def test_simulator_can_deterministically_trigger_autorange_change(monkeypatch) -> None:
    import keith_ivt.instrument.simulator as sim
    monkeypatch.setattr(sim.time, "sleep", lambda _s: None)

    cfg = _time_config(stop=0.0)
    inst = SimulatedKeithley(resistance_ohm=10_000.0, noise_fraction=0.0, model_name=None)
    inst.connect()
    inst.reset()
    inst.configure_for_sweep(cfg)
    inst.output_on()
    inst.force_autorange_current_range_on_read(1, 1e-9)
    inst.set_source(cfg.source_scpi, 0.0)
    inst.read_source_and_measure()

    assert inst.get_current_autorange() is True
    assert inst.get_current_range() == 1e-9
    assert inst.last_current_range_change_s is not None


def test_front_panel_source_contains_current_range_controls() -> None:
    status_source = (SRC / "keith_ivt" / "ui" / "status_bar.py").read_text(encoding="utf-8")

    assert "Current range" in status_source
    assert "Auto current range" in status_source
    assert "Lock current range" in status_source
    assert "Range settle delay" in status_source
    assert "Irange {self._current_range_status_fragment()}" in status_source
