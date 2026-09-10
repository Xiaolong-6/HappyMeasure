from __future__ import annotations

from collections.abc import Callable
import time
import sys
import math
from datetime import datetime

from keith_ivt.acquisition import resolve_time_acquisition
from keith_ivt.core.current_range import CurrentRangeControl, CurrentRangeState
from keith_ivt.instrument.base import SourceMeter
from keith_ivt.models import (
    SweepConfig,
    SweepKind,
    SweepPoint,
    SweepResult,
    validate_config,
    source_values_for_config,
)

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


def wait_until_deadline(
    deadline: float,
    should_stop: StopCallback | None = None,
    should_pause: PauseCallback | None = None,
    *,
    monotonic: Callable[[], float] | None = None,
    sleep: Callable[[float], None] | None = None,
) -> bool:
    """Wait for a Constant Time deadline and report a pause request.

    The wait is bounded in small slices so Stop and Pause remain responsive even
    when the requested interval is long. A pause return lets the caller rebase
    its deadline after the operator resumes instead of trying to catch up on
    every interval that elapsed while paused.
    """
    clock = time.monotonic if monotonic is None else monotonic
    sleeper = time.sleep if sleep is None else sleep
    while True:
        if should_stop is not None and should_stop():
            return False
        if should_pause is not None and should_pause():
            return True
        remaining = deadline - clock()
        if remaining <= 0:
            return False
        before_sleep = clock()
        sleeper(min(0.05, remaining))
        if clock() <= before_sleep:
            return False


def _wait_until_deadline(
    deadline: float,
    should_stop: StopCallback | None = None,
    should_pause: PauseCallback | None = None,
) -> bool:
    return wait_until_deadline(
        deadline,
        should_stop,
        should_pause,
        monotonic=time.monotonic,
        sleep=time.sleep,
    )


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
            raise ValueError(
                "MANUAL_OUTPUT is not a SweepRunner sweep. Use the UI safety-interlock path."
            )
        values = source_values_for_config(config)
        acquisition = resolve_time_acquisition(config)
        points: list[SweepPoint] = []
        t0: float | None = None
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
                state = self._initialize_current_range_state(config, current_range_control)
                last_actual_range_A = state.actual_range_A
            self.instrument.output_on()

            is_continuous_time = (
                config.sweep_kind is SweepKind.CONSTANT_TIME and config.continuous_time
            )
            if config.sweep_kind is SweepKind.CONSTANT_TIME:
                index = 0
                self.instrument.set_source(config.source_scpi, config.constant_value)
                t0 = time.monotonic()
                next_deadline = t0
                total = 0 if is_continuous_time else len(values)
                while not _should_stop() and (is_continuous_time or index < total):
                    was_paused = False
                    while should_pause is not None and should_pause():
                        was_paused = True
                        if _should_stop():
                            break
                        _interruptible_sleep(0.05, _should_stop)
                    if _should_stop():
                        break
                    if was_paused:
                        next_deadline = time.monotonic()
                    if acquisition.source_write_each_sample:
                        self.instrument.set_source(config.source_scpi, config.constant_value)
                    _interruptible_sleep(acquisition.software_delay_s, _should_stop)
                    if _should_stop():
                        break
                    stable_read, discard_remaining, last_actual_range_A = (
                        self._read_stable_at_source(
                            config,
                            current_range_control,
                            discard_remaining,
                            last_actual_range_A,
                            _should_stop,
                        )
                    )
                    if stable_read is None:
                        break
                    reported_source, measured = stable_read
                    index += 1
                    assert t0 is not None
                    point = SweepPoint(
                        source_value=reported_source,
                        measured_value=measured,
                        elapsed_s=time.monotonic() - t0,
                        timestamp=datetime.now().isoformat(timespec="milliseconds"),
                    )
                    points.append(point)
                    if on_point is not None:
                        on_point(point, index, total)
                    if not is_continuous_time and index >= total:
                        break
                    if acquisition.as_fast_as_possible:
                        # No artificial interval: the next :READ? starts as soon
                        # as the host/instrument path is ready. Pause/Stop are
                        # still checked at the top of every iteration.
                        continue
                    next_deadline += max(0.0, config.interval_s)
                    now = time.monotonic()
                    if next_deadline < now:
                        next_deadline = now
                    if _wait_until_deadline(next_deadline, _should_stop, should_pause):
                        continue
            else:
                t0 = time.monotonic()
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
                    stable_read, discard_remaining, last_actual_range_A = (
                        self._read_stable_at_source(
                            config,
                            current_range_control,
                            discard_remaining,
                            last_actual_range_A,
                            _should_stop,
                        )
                    )
                    if stable_read is None:
                        break
                    reported_source, measured = stable_read
                    assert t0 is not None
                    point = SweepPoint(
                        source_value=reported_source,
                        measured_value=measured,
                        elapsed_s=time.monotonic() - t0,
                        timestamp=datetime.now().isoformat(timespec="milliseconds"),
                    )
                    points.append(point)
                    if on_point is not None:
                        on_point(point, index, total)
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
        """Read repeatedly at one source setpoint until current range settles."""
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
            discard_remaining, last_actual_range_A, should_discard = self._range_discard_decision(
                config,
                control,
                discard_remaining,
                last_actual_range_A,
                should_stop,
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
        return control.update_state(
            CurrentRangeState(
                autorange=autorange,
                actual_range_A=actual,
                fixed_range_A=None if autorange else actual,
                last_change_monotonic_s=previous.last_change_monotonic_s,
                warning=warning,
            )
        )

    def _initialize_current_range_state(
        self, config: SweepConfig, control: CurrentRangeControl
    ) -> CurrentRangeState:
        if config.auto_measure_range:
            return self._refresh_current_range_state(control)
        previous = control.snapshot()
        actual = (
            float(config.measure_range)
            if config.measure_scpi == "CURR"
            else previous.actual_range_A
        )
        return control.update_state(
            CurrentRangeState(
                autorange=False,
                actual_range_A=actual,
                fixed_range_A=actual,
                last_change_monotonic_s=previous.last_change_monotonic_s,
                warning=None,
            )
        )

    def _mark_range_change(
        self, control: CurrentRangeControl | None, range_A: float | None = None
    ) -> None:
        if control is None:
            return
        state = control.snapshot()
        control.update_state(
            CurrentRangeState(
                autorange=state.autorange,
                actual_range_A=range_A if range_A is not None else state.actual_range_A,
                fixed_range_A=state.fixed_range_A,
                last_change_monotonic_s=time.monotonic(),
                warning=state.warning,
            )
        )

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
        state = control.snapshot()
        if state.autorange is False:
            if discard_remaining > 0:
                return discard_remaining - 1, last_actual_range_A, True
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
        source = float(source_value)
        measured = float(measured_value)
        if not math.isfinite(source) or not math.isfinite(measured):
            raise RuntimeError(
                f"Non-finite measurement readback: source={source!r}, measured={measured!r}"
            )
        return source, measured

    def _safe_output_off_preserving_error(self) -> None:
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
