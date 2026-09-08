from __future__ import annotations

from collections.abc import Callable
import sys
import time
import math
from typing import TYPE_CHECKING

from keith_ivt.core.sweep_runner import SweepRunner, wait_until_deadline
from keith_ivt.drivers.base import DriverReadback, SMUDriver
from keith_ivt.models import SweepPoint, SweepResult, SweepConfig
from keith_ivt.sweeps.plan import SweepExecutionKind, SweepPlan, plan_from_config

if TYPE_CHECKING:
    from keith_ivt.core.current_range import CurrentRangeControl
    from keith_ivt.instrument.base import SourceMeter

PlanPointCallback = Callable[[DriverReadback, int, int], None]
StopCallback = Callable[[], bool]
PauseCallback = Callable[[], bool]


class MeasurementService:
    """Canonical hardware-independent measurement orchestration boundary.

    Native drivers execute :class:`SweepPlan` objects through ``run_plan``.
    The current UI's legacy instruments enter through ``run_source_meter`` so
    callers no longer depend directly on the legacy runner.
    """

    def __init__(self, driver: SMUDriver):
        self.driver = driver

    @staticmethod
    def run_source_meter(
        meter: "SourceMeter",
        config: SweepConfig,
        on_point: Callable[[SweepPoint, int, int], None] | None = None,
        should_stop: StopCallback | None = None,
        should_pause: PauseCallback | None = None,
        current_range_control: "CurrentRangeControl | None" = None,
    ) -> SweepResult:
        """Run a legacy instrument through the canonical service facade."""
        return SweepRunner(meter).run(
            config,
            on_point=on_point,
            should_stop=should_stop,
            should_pause=should_pause,
            current_range_control=current_range_control,
        )

    def run_plan(
        self,
        plan: SweepPlan,
        on_point: PlanPointCallback | None = None,
        should_stop: StopCallback | None = None,
        should_pause: PauseCallback | None = None,
    ) -> list[DriverReadback]:
        if plan.execution_kind is SweepExecutionKind.MANUAL_OUTPUT:
            raise ValueError("Manual output is not a normal measurement plan.")
        reads: list[DriverReadback] = []
        stopped_by_operator = False

        def _should_stop() -> bool:
            nonlocal stopped_by_operator
            if should_stop is not None and should_stop():
                stopped_by_operator = True
                return True
            return False

        try:
            self.driver.reset()
            try:
                self.driver.configure_source_measure(
                    source_mode=plan.source_mode,
                    measure_mode=plan.measure_mode,
                    compliance=plan.compliance,
                    nplc=plan.nplc,
                    delay_s=plan.delay_s,
                    autorange=plan.autorange,
                    source_range=plan.source_range,
                    measure_range=plan.measure_range,
                )
            except TypeError as exc:
                if "delay_s" not in str(exc):
                    raise
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

            total = plan.point_count
            is_constant_time = (
                plan.execution_kind is SweepExecutionKind.CONSTANT_TIME
                and plan.interval_s is not None
            )
            next_deadline: float | None = None
            for index, value in enumerate(plan.values, start=1):
                if _should_stop():
                    break
                was_paused = False
                while should_pause is not None and should_pause():
                    was_paused = True
                    if _should_stop():
                        break
                    time.sleep(0.05)
                if _should_stop():
                    break
                self.driver.set_source(plan.source_mode, value)
                if is_constant_time and index == 1:
                    # Start acquisition timing after the initial source command,
                    # matching the legacy SweepRunner Constant Time semantics.
                    next_deadline = time.monotonic()
                if was_paused and next_deadline is not None:
                    next_deadline = time.monotonic()
                time.sleep(max(0.0, plan.delay_s))
                read = self._validated_readback(self.driver.read())
                reads.append(read)
                if on_point is not None:
                    on_point(read, index, total)
                if is_constant_time and index < total:
                    assert next_deadline is not None
                    next_deadline += max(0.0, plan.interval_s or 0.0)
                    now = time.monotonic()
                    if next_deadline < now:
                        next_deadline = now
                    if wait_until_deadline(
                        next_deadline,
                        _should_stop,
                        should_pause,
                        monotonic=time.monotonic,
                        sleep=time.sleep,
                    ):
                        # The next loop observes Pause and rebases the deadline
                        # after the operator resumes.
                        continue
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
            raise RuntimeError(
                f"Non-finite measurement readback: source={source!r}, measured={measured!r}"
            )
        return DriverReadback(
            source_value=source, measured_value=measured, timestamp_s=read.timestamp_s
        )

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
                on_point(
                    SweepPoint(source_value=read.source_value, measured_value=read.measured_value),
                    index,
                    total,
                )

        reads = self.run_plan(plan, _bridge, should_stop, should_pause)
        return SweepResult(
            config=config,
            points=[
                SweepPoint(source_value=r.source_value, measured_value=r.measured_value)
                for r in reads
            ],
        )
