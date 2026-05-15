from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from keith_ivt.core.sweep_runner import SweepRunner
from keith_ivt.instrument.simulator import SimulatedKeithley
from keith_ivt.models import SweepConfig, SweepKind, SweepMode


def run_linear(config: SweepConfig):
    with SimulatedKeithley(resistance_ohm=10_000.0, noise_fraction=0.0, model_name=None) as inst:
        return SweepRunner(inst).run(config)


def test_linear_resistor_voltage_and_current_modes_are_linear(monkeypatch):
    import keith_ivt.instrument.simulator as sim
    monkeypatch.setattr(sim.time, "sleep", lambda _s: None)

    vcfg = SweepConfig(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=-1.0,
        stop=1.0,
        step=0.5,
        compliance=1.0,
        nplc=0.01,
        sweep_kind=SweepKind.STEP,
    )
    vres = run_linear(vcfg)
    assert [round(p.measured_value / p.source_value, 8) for p in vres.points if p.source_value] == [0.0001] * 4

    icfg = SweepConfig(
        mode=SweepMode.CURRENT_SOURCE,
        start=1e-3,
        stop=-1e-3,
        step=-5e-4,
        compliance=20.0,
        nplc=0.01,
        sweep_kind=SweepKind.STEP,
    )
    ires = run_linear(icfg)
    assert [round(p.measured_value / p.source_value, 3) for p in ires.points if p.source_value] == [10000.0] * 4


def test_simulator_compliance_and_fixed_ranges_have_effect(monkeypatch):
    import keith_ivt.instrument.simulator as sim
    monkeypatch.setattr(sim.time, "sleep", lambda _s: None)

    cfg = SweepConfig(
        mode=SweepMode.CURRENT_SOURCE,
        start=-2e-3,
        stop=2e-3,
        step=2e-3,
        compliance=5.0,
        nplc=0.01,
        auto_source_range=False,
        source_range=1e-3,
        auto_measure_range=False,
        measure_range=4.0,
    )
    result = run_linear(cfg)
    # Source is clipped to +/-1 mA before measuring; measurement range then clips voltage to +/-4 V.
    assert [round(p.source_value, 6) for p in result.points] == [-0.001, 0.0, 0.001]
    assert [round(p.measured_value, 6) for p in result.points] == [-4.0, 0.0, 4.0]

    ccfg = SweepConfig(
        mode=SweepMode.CURRENT_SOURCE,
        start=2e-3,
        stop=2e-3,
        step=1e-3,
        compliance=3.0,
        nplc=0.01,
    )
    cres = run_linear(ccfg)
    assert cres.points[0].measured_value == 3.0


def test_higher_nplc_reduces_simulated_noise(monkeypatch):
    import keith_ivt.instrument.simulator as sim
    monkeypatch.setattr(sim.time, "sleep", lambda _s: None)

    def sample_std(nplc: float) -> float:
        cfg = SweepConfig(
            mode=SweepMode.VOLTAGE_SOURCE,
            start=1.0,
            stop=1.0,
            step=1.0,
            compliance=1.0,
            nplc=nplc,
            sweep_kind=SweepKind.STEP,
        )
        random.seed(123)
        vals = []
        with SimulatedKeithley(resistance_ohm=10_000.0, noise_fraction=0.2, model_name=None) as inst:
            inst.reset(); inst.configure_for_sweep(cfg); inst.output_on(); inst.set_source(cfg.source_scpi, 1.0)
            for _ in range(200):
                vals.append(inst.read_source_and_measure()[1])
        mean = sum(vals) / len(vals)
        return (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5

    assert sample_std(10.0) < sample_std(0.01) * 0.25
