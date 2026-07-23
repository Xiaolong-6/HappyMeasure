from __future__ import annotations

from collections.abc import Callable
import time
import sys
import math
from datetime import datetime

from keith_ivt.core.current_range import CurrentRangeControl, CurrentRangeState
from keith_ivt.instrument.base import SourceMeter
from keith_ivt.models import SweepConfig, SweepKind, SweepPoint, SweepResult, validate_config, source_values_for_config

PointCallback = Callable[[SweepPoint, int, int], None]
StopCallback = Callable[[], bool]
PauseCallback = Callable[[], bool]
StableRead = tuple[float, float] | None

MIN_RANGE_STABILIZATION_ATTEMPTS = 50


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
        current_range_control: CurrentRangeControl | None = None,
    ) -> SweepResult:
        validate_config(config)
        if config.sweep_kind is SweepKind.MANUAL_OUTPUT:
            raise ValueError("MANUAL_OUTPUT is not a SweepRunner sweep. Use the UI safety-interlock path.")
        values = source_values_for_config(config)
        points: list[SweepPoint] = []
        t0 = time.monotonic()
        stopped_by_operator = False
        discard_remaining = 0
        last_actual_range_A: float | None = None

        def _should_stop() -> bool:
            nonlocal stopped_by_operator
            if should_stop is not None and should_stop():
                stopped_by_operator = True
                return True
            return False

        try:
            self.instrument.reset()
            self.instrument.configure_for_sweep(config)
            if current_range_control is not None:
                state = self._refresh_current_range_state(current_range_control)
                last_actual_range_A = state.actual_range_A
            self.instrument.output_on()

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
                    _interruptible_sleep(config.delay_s, _should_stop)
                    if _should_stop():
                        break
                    stable_read, discard_remaining, last_actual_range_A = self._read_stable_at_source(
                        config,
                        current_range_control,
                        discard_remaining,
                        last_actual_range_A,
                        _should_stop,
                    )
                    if stable_read is None:
                        break
                    reported_source, measured = stable_read
                    index += 1
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
                    _interruptible_sleep(config.delay_s, _should_stop)
                    if _should_stop():
                        break
                    stable_read, discard_remaining, last_actual_range_A = self._read_stable_at_source(
                        config,
                        current_range_control,
                        discard_remaining,
                        last_actual_range_A,
                        _should_stop,
                    )
                    if stable_read is None:
                        break
                    reported_source, measured = stable_read
                    point = SweepPoint(source_value=reported_source, measured_value=measured, elapsed_s=time.monotonic() - t0, timestamp=datetime.now().isoformat(timespec="milliseconds"))
                    points.append(point)
                    if on_point is not None:
                        on_point(point, index, total)
                    if config.sweep_kind is SweepKind.CONSTANT_TIME and index < total:
                        _interruptible_sleep(max(0.0, config.interval_s), _should_stop)
        finally:
            run_failed = sys.exc_info()[1] is not None
            if config.output_off_after_run or stopped_by_operator or run_failed:
                self._safe_output_off_preserving_error()

        return SweepResult(config=config, points=points)

    def _read_stable_at_source(
        self,
        config: SweepConfig,
        control: CurrentRangeControl | None,
        discard_remaining: int,
        last_actual_range_A: float | None,
        should_stop: StopCallback | None,
    ) -> tuple[StableRead, int, float | None]:
        """Read repeatedly at one source setpoint until current range settles.

        Discarding a transient readback must not advance the outer sweep. Doing
        so silently removes requested source voltages from the result whenever
        autorange changes.
        """
        max_attempts = max(
            MIN_RANGE_STABILIZATION_ATTEMPTS,
            int(config.discard_after_range_change) + 5,
        )
        for _attempt in range(max_attempts):
            if should_stop is not None and should_stop():
                return None, discard_remaining, last_actual_range_A
            discard_remaining = self._apply_current_range_actions(
                config,
                control,
                discard_remaining,
                should_stop,
            )
            if should_stop is not None and should_stop():
                return None, discard_remaining, last_actual_range_A
            reported_source, measured = self.instrument.read_source_and_measure()
            reported_source, measured = self._validated_readback(reported_source, measured)
            discard_remaining, last_actual_range_A, should_discard = (
                self._range_discard_decision(
                    config,
                    control,
                    discard_remaining,
                    last_actual_range_A,
                    should_stop,
                )
            )
            if not should_discard:
                return (reported_source, measured), discard_remaining, last_actual_range_A
        raise RuntimeError(
            "Current range did not stabilize at the active source setpoint "
            f"after {max_attempts} reads."
        )

    def _refresh_current_range_state(self, control: CurrentRangeControl) -> CurrentRangeState:
        previous = control.snapshot()
        warning = None
        autorange = None
        actual = None
        try:
            autorange = bool(self.instrument.get_current_autorange())
        except Exception as exc:
            warning = f"Current autorange query failed: {exc}"
        try:
            actual = float(self.instrument.get_current_range())
        except Exception as exc:
            warning = f"Current range query failed: {exc}"
        return control.update_state(CurrentRangeState(
            autorange=autorange,
            actual_range_A=actual,
            fixed_range_A=None if autorange else actual,
            last_change_monotonic_s=previous.last_change_monotonic_s,
            warning=warning,
        ))

    def _mark_range_change(self, control: CurrentRangeControl | None, range_A: float | None = None) -> None:
        if control is None:
            return
        state = control.snapshot()
        control.update_state(CurrentRangeState(
            autorange=state.autorange,
            actual_range_A=range_A if range_A is not None else state.actual_range_A,
            fixed_range_A=state.fixed_range_A,
            last_change_monotonic_s=time.monotonic(),
            warning=state.warning,
        ))

    def _apply_current_range_actions(
        self,
        config: SweepConfig,
        control: CurrentRangeControl | None,
        discard_remaining: int,
        should_stop: StopCallback | None,
    ) -> int:
        if control is None:
            return discard_remaining
        for action in control.drain_actions():
            try:
                if action.kind == "autorange":
                    self.instrument.set_current_autorange(bool(action.value))
                elif action.kind == "fixed_range":
                    if action.value is None:
                        raise ValueError("Fixed current range action is missing a range value.")
                    self.instrument.set_current_autorange(False)
                    self.instrument.set_current_range(float(action.value))
                elif action.kind == "lock_current":
                    actual = float(self.instrument.get_current_range())
                    self.instrument.set_current_autorange(False)
                    self.instrument.set_current_range(actual)
            except Exception as exc:
                control.with_warning(f"Current range control failed: {exc}")
                continue
            state = self._refresh_current_range_state(control)
            self._mark_range_change(control, state.actual_range_A)
            _interruptible_sleep(float(config.range_settle_delay_ms) / 1000.0, should_stop)
            discard_remaining = max(discard_remaining, int(config.discard_after_range_change))
        return discard_remaining

    def _range_discard_decision(
        self,
        config: SweepConfig,
        control: CurrentRangeControl | None,
        discard_remaining: int,
        last_actual_range_A: float | None,
        should_stop: StopCallback | None,
    ) -> tuple[int, float | None, bool]:
        if control is None:
            return discard_remaining, last_actual_range_A, False
        state = self._refresh_current_range_state(control)
        actual = state.actual_range_A
        changed = (
            last_actual_range_A is not None
            and actual is not None
            and abs(actual - last_actual_range_A) > max(1e-15, abs(last_actual_range_A) * 1e-6)
        )
        if changed:
            self._mark_range_change(control, actual)
            _interruptible_sleep(float(config.range_settle_delay_ms) / 1000.0, should_stop)
            discard_remaining = max(discard_remaining, int(config.discard_after_range_change))
        last_actual_range_A = actual if actual is not None else last_actual_range_A
        if discard_remaining > 0:
            return discard_remaining - 1, last_actual_range_A, True
        return discard_remaining, last_actual_range_A, False


    @staticmethod
    def _validated_readback(source_value: float, measured_value: float) -> tuple[float, float]:
        """Reject non-finite instrument readbacks before they enter datasets.

        Real instruments and simulator fault-injection paths can surface NaN or
        infinite values after timeouts, range failures, or parser errors.  Treat
        those as measurement failures so the runner enters the normal error path
        and still executes safety cleanup.
        """
        source = float(source_value)
        measured = float(measured_value)
        if not math.isfinite(source) or not math.isfinite(measured):
            raise RuntimeError(f"Non-finite measurement readback: source={source!r}, measured={measured!r}")
        return source, measured

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
