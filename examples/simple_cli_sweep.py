from keith_ivt.core.sweep_runner import SweepRunner
from keith_ivt.data.exporters import save_csv
from keith_ivt.instrument.simulator import SimulatedKeithley
from keith_ivt.models import SweepConfig, SweepMode

config = SweepConfig(
    mode=SweepMode.VOLTAGE_SOURCE,
    start=-0.1,
    stop=0.1,
    step=0.01,
    compliance=0.01,
    nplc=1.0,
    debug=True,
)

with SimulatedKeithley() as smu:
    result = SweepRunner(smu).run(config, on_point=lambda p, i, n: print(i, n, p))

save_csv(result, "example_sweep.csv")
print("Saved example_sweep.csv")
