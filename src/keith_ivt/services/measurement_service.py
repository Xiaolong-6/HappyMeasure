from __future__ import annotations

from collections.abc import Callable
import sys
import time
import math

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
        stopped_by_operator = False

        def _should_stop() -> bool:
            nonlocal stopped_by_operator
            if should_stop is not None and should_stop():
                stopped_by_operator = True
                return True
            return False

        try:
            total = plan.point_count
            for index, value in enumerate(plan.values, start=1):
                if _should_stop():
                    break
                while should_pause is not None and should_pause():
                    if _should_stop():
                        break
                    time.sleep(0.05)
                if _should_stop():
                    break
                self.driver.set_source(plan.source_mode, value)
                read = self._validated_readback(self.driver.read())
                reads.append(read)
                if on_point is not None:
                    on_point(read, index, total)
                if plan.execution_kind is SweepExecutionKind.CONSTANT_TIME and index < total:
                    time.sleep(max(0.0, plan.interval_s or 0.0))
        finally:
            # The driver-level service is conservative: normal completion, user stop,
            # and failures all attempt to place the SMU in a safe output-off state.
            self._safe_output_off_preserving_error()
        return reads


    @staticmethod
    def _validated_readback(read: DriverReadback) -> DriverReadback:
        source = float(read.source_value)
        measured = float(read.measured_value)
        if not math.isfinite(source) or not math.isfinite(measured):
            raise RuntimeError(f"Non-finite measurement readback: source={source!r}, measured={measured!r}")
        return DriverReadback(source_value=source, measured_value=measured, timestamp_s=read.timestamp_s)

    def _safe_output_off_preserving_error(self) -> None:
        active_exc = sys.exc_info()[1]
        try:
            self.driver.output_off()
        except Exception as off_exc:
            if active_exc is not None:
                raise RuntimeError(
                    "Measurement failed, and the safety output-off command also failed. "
                    f"Original error: {active_exc}; output-off error: {off_exc}"
                ) from active_exc
            raise

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
