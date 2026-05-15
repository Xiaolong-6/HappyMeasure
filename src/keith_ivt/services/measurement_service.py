from __future__ import annotations

from collections.abc import Callable
import time

from keith_ivt.drivers.base import DriverReadback, SMUDriver
from keith_ivt.models import SweepPoint, SweepResult, SweepConfig
from keith_ivt.sweeps.plan import SweepExecutionKind, SweepPlan, plan_from_config

PlanPointCallback = Callable[[DriverReadback, int, int], None]
StopCallback = Callable[[], bool]
PauseCallback = Callable[[], bool]


class MeasurementService:
    """Hardware-independent execution service for future IV/CV workflows.

    The UI should eventually call this service with a SweepPlan. Existing code can
    keep using SweepRunner/SweepConfig while migration continues.
    """

    def __init__(self, driver: SMUDriver):
        self.driver = driver

    def run_plan(
        self,
        plan: SweepPlan,
        on_point: PlanPointCallback | None = None,
        should_stop: StopCallback | None = None,
        should_pause: PauseCallback | None = None,
    ) -> list[DriverReadback]:
        if plan.execution_kind is SweepExecutionKind.MANUAL_OUTPUT:
            raise ValueError("Manual output is not a normal measurement plan.")
        self.driver.reset()
        self.driver.configure_source_measure(
            source_mode=plan.source_mode,
            measure_mode=plan.measure_mode,
            compliance=plan.compliance,
            nplc=plan.nplc,
            autorange=plan.autorange,
            source_range=plan.source_range,
            measure_range=plan.measure_range,
        )
        self.driver.output_on()
        reads: list[DriverReadback] = []
        try:
            total = plan.point_count
            for index, value in enumerate(plan.values, start=1):
                if should_stop is not None and should_stop():
                    break
                while should_pause is not None and should_pause():
                    if should_stop is not None and should_stop():
                        break
                    time.sleep(0.05)
                if should_stop is not None and should_stop():
                    break
                self.driver.set_source(plan.source_mode, value)
                read = self.driver.read()
                reads.append(read)
                if on_point is not None:
                    on_point(read, index, total)
                if plan.execution_kind is SweepExecutionKind.CONSTANT_TIME and index < total:
                    time.sleep(max(0.0, plan.interval_s or 0.0))
        finally:
            self.driver.output_off()
        return reads

    def run_legacy_config(
        self,
        config: SweepConfig,
        on_point: Callable[[SweepPoint, int, int], None] | None = None,
        should_stop: StopCallback | None = None,
        should_pause: PauseCallback | None = None,
    ) -> SweepResult:
        plan = plan_from_config(config)
        def _bridge(read: DriverReadback, index: int, total: int) -> None:
            if on_point is not None:
                on_point(SweepPoint(source_value=read.source_value, measured_value=read.measured_value), index, total)
        reads = self.run_plan(plan, _bridge, should_stop, should_pause)
        return SweepResult(
            config=config,
            points=[SweepPoint(source_value=r.source_value, measured_value=r.measured_value) for r in reads],
        )
