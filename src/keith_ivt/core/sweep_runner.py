from __future__ import annotations

from collections.abc import Callable
import time
import sys
from datetime import datetime

from keith_ivt.instrument.base import SourceMeter
from keith_ivt.models import SweepConfig, SweepKind, SweepPoint, SweepResult, make_constant_time_values, make_source_values, validate_config
from keith_ivt.core.adaptive_logic import adaptive_values_from_logic

PointCallback = Callable[[SweepPoint, int, int], None]
StopCallback = Callable[[], bool]
PauseCallback = Callable[[], bool]


def _interruptible_sleep(seconds: float, should_stop: StopCallback | None = None) -> None:
    deadline = time.monotonic() + max(0.0, float(seconds))
    while time.monotonic() < deadline:
        if should_stop is not None and should_stop():
            return
        time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))


class SweepRunner:
    def __init__(self, instrument: SourceMeter):
        self.instrument = instrument

    def run(
        self,
        config: SweepConfig,
        on_point: PointCallback | None = None,
        should_stop: StopCallback | None = None,
        should_pause: PauseCallback | None = None,
    ) -> SweepResult:
        validate_config(config)
        if config.sweep_kind is SweepKind.MANUAL_OUTPUT:
            raise ValueError("MANUAL_OUTPUT is not a SweepRunner sweep. Use the UI safety-interlock path.")
        if config.sweep_kind is SweepKind.CONSTANT_TIME and not config.continuous_time:
            values = make_constant_time_values(config.constant_value, config.duration_s, config.interval_s)
        elif config.sweep_kind is SweepKind.CONSTANT_TIME and config.continuous_time:
            values = []
        elif config.sweep_kind is SweepKind.ADAPTIVE:
            values = adaptive_values_from_logic(config.adaptive_logic)
        else:
            values = make_source_values(config.start, config.stop, config.step)
        points: list[SweepPoint] = []
        t0 = time.monotonic()
        stopped_by_operator = False

        def _should_stop() -> bool:
            nonlocal stopped_by_operator
            if should_stop is not None and should_stop():
                stopped_by_operator = True
                return True
            return False

        self.instrument.reset()
        self.instrument.configure_for_sweep(config)
        self.instrument.output_on()

        try:
            if config.sweep_kind is SweepKind.CONSTANT_TIME and config.continuous_time:
                index = 0
                self.instrument.set_source(config.source_scpi, config.constant_value)
                while not _should_stop():
                    while should_pause is not None and should_pause():
                        if _should_stop():
                            break
                        _interruptible_sleep(0.05, _should_stop)
                    if _should_stop():
                        break
                    index += 1
                    reported_source, measured = self.instrument.read_source_and_measure()
                    point = SweepPoint(source_value=reported_source, measured_value=measured, elapsed_s=time.monotonic() - t0, timestamp=datetime.now().isoformat(timespec="milliseconds"))
                    points.append(point)
                    if on_point is not None:
                        on_point(point, index, 0)
                    _interruptible_sleep(max(0.0, config.interval_s), _should_stop)
            else:
                total = len(values)
                for index, source_value in enumerate(values, start=1):
                    if _should_stop():
                        break
                    while should_pause is not None and should_pause():
                        if _should_stop():
                            break
                        _interruptible_sleep(0.05, _should_stop)
                    if _should_stop():
                        break
                    self.instrument.set_source(config.source_scpi, source_value)
                    reported_source, measured = self.instrument.read_source_and_measure()
                    point = SweepPoint(source_value=reported_source, measured_value=measured, elapsed_s=time.monotonic() - t0, timestamp=datetime.now().isoformat(timespec="milliseconds"))
                    points.append(point)
                    if on_point is not None:
                        on_point(point, index, total)
                    if config.sweep_kind is SweepKind.CONSTANT_TIME and index < total:
                        _interruptible_sleep(max(0.0, config.interval_s), _should_stop)
        finally:
            if config.output_off_after_run or stopped_by_operator:
                self._safe_output_off_preserving_error()

        return SweepResult(config=config, points=points)

    def _safe_output_off_preserving_error(self) -> None:
        """Turn output off without hiding the original measurement failure.

        A failed output-off command is serious and should still fail the run, but
        if the measurement already raised an exception we preserve that root
        cause in the replacement exception message and exception chain.
        """
        active_exc = sys.exc_info()[1]
        try:
            self.instrument.output_off()
        except Exception as off_exc:
            if active_exc is not None:
                raise RuntimeError(
                    "Measurement failed, and the safety output-off command also failed. "
                    f"Original error: {active_exc}; output-off error: {off_exc}"
                ) from active_exc
            raise
