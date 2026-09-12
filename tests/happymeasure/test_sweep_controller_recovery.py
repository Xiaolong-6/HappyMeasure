from __future__ import annotations

import threading

import pytest

from keith_ivt.core.current_range import CurrentRangeControl, CurrentRangeState
from keith_ivt.models import SweepConfig, SweepKind, SweepMode
from keith_ivt.ui.app_state import AppAction, AppState, RunState
from keith_ivt.ui.sweep_controller import SweepControllerMixin


class _ClearableBuffer:
    def __init__(self) -> None:
        self.cleared = False

    def clear(self) -> None:
        self.cleared = True


class _ControllerHarness(SweepControllerMixin):
    def __init__(self, config: SweepConfig) -> None:
        self.config = config
        self.app_state = AppState()
        self.app_state.dispatch(AppAction.CONNECT_SIMULATED, device_id="sim")
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._x_data = [1.0]
        self._y_data = [2.0]
        self._live_points = [object()]
        self._live_config = config
        self._measurement_xy = _ClearableBuffer()
        self._current_range_control = CurrentRangeControl(
            CurrentRangeState(autorange=True, actual_range_A=1e-6)
        )
        self.logs: list[str] = []
        self.start_enabled = False
        self.popup_closed = False
        self.redraw_count = 0

    @property
    def _connected(self) -> bool:
        return self.app_state.is_connected

    @property
    def _run_state(self) -> str:
        return self.app_state.run_state_text

    def _make_config(self) -> SweepConfig:
        return self.config

    def _set_run_state(self, state: str) -> None:
        action = {
            "preparing": AppAction.PREPARE_SWEEP,
            "running": AppAction.START_SWEEP,
        }[state]
        assert self.app_state.dispatch(action)
        self._update_run_button_states()

    def _update_run_button_states(self) -> None:
        self.start_enabled = self.app_state.can_start_sweep()

    def _refresh_run_status_from_state(self) -> None:
        pass

    def _reset_live_measurement_status(self) -> None:
        pass

    def _close_auto_front_panel_popup(self) -> None:
        self.popup_closed = True

    def _open_front_panel_for_sweep_start(self) -> None:
        pass

    def _redraw_all_plots(self, *args, **kwargs) -> None:
        self.redraw_count += 1

    def log_event(self, message: str) -> None:
        self.logs.append(message)


def _config(**changes) -> SweepConfig:
    values = dict(
        mode=SweepMode.VOLTAGE_SOURCE,
        start=1.0,
        stop=-1.0,
        step=0.1,
        compliance=0.01,
        nplc=0.01,
        sweep_kind=SweepKind.STEP,
    )
    values.update(changes)
    return SweepConfig(**values)


def test_invalid_config_is_rejected_before_worker_and_valid_retry_starts(
    monkeypatch,
) -> None:
    app = _ControllerHarness(_config(step=0.0))
    dialogs: list[tuple[str, str]] = []
    started_threads: list[object] = []

    class _FakeThread:
        def __init__(self, *args, **kwargs) -> None:
            started_threads.append(self)

        def start(self) -> None:
            started_threads.append("started")

    monkeypatch.setattr(
        "keith_ivt.ui.sweep_controller.messagebox.showerror",
        lambda title, message: dialogs.append((title, message)),
    )
    monkeypatch.setattr("keith_ivt.ui.sweep_controller.threading.Thread", _FakeThread)

    app.start_sweep()

    assert dialogs == [("Invalid sweep configuration", "Step cannot be zero.")]
    assert started_threads == []
    assert app.app_state.run_state is RunState.IDLE
    assert app.start_enabled is True

    app.config = _config()
    app.start_sweep()

    assert len(started_threads) == 2
    assert started_threads[-1] == "started"
    assert app.app_state.run_state is RunState.SWEEPING


def test_short_continuous_interval_is_not_rejected_by_serial_estimate(monkeypatch) -> None:
    app = _ControllerHarness(
        _config(
            sweep_kind=SweepKind.CONSTANT_TIME,
            continuous_time=True,
            constant_value=0.1,
            interval_s=0.01,
            nplc=0.1,
            baud_rate=9600,
        )
    )
    dialogs: list[tuple[str, str]] = []
    started_threads: list[object] = []

    class _FakeThread:
        def __init__(self, *args, **kwargs) -> None:
            started_threads.append(self)

        def start(self) -> None:
            started_threads.append("started")

    monkeypatch.setattr(
        "keith_ivt.ui.sweep_controller.messagebox.showerror",
        lambda title, message: dialogs.append((title, message)),
    )
    monkeypatch.setattr("keith_ivt.ui.sweep_controller.threading.Thread", _FakeThread)

    app.start_sweep()

    assert dialogs == []
    assert started_threads[-1] == "started"
    assert app.app_state.run_state is RunState.SWEEPING


@pytest.mark.parametrize(
    "changes",
    [
        {"step": 0.0},
        {"start": float("inf")},
        {"compliance": float("nan")},
        {"compliance": 0.0},
        {"auto_source_range": False, "source_range": 0.0},
        {"auto_measure_range": False, "measure_range": 0.0},
        {"nplc": 11.0},
        {"delay_s": -0.1},
        {"range_settle_delay_ms": -1},
        {"discard_after_range_change": -1},
        {"sweep_kind": SweepKind.ADAPTIVE, "adaptive_segments": "invalid"},
        {
            "sweep_kind": SweepKind.CONSTANT_TIME,
            "duration_s": 0.0,
            "interval_s": 0.2,
        },
    ],
)
def test_preflight_validation_edges_never_construct_worker(monkeypatch, changes) -> None:
    app = _ControllerHarness(_config(**changes))
    worker_constructed = False

    class _UnexpectedThread:
        def __init__(self, *args, **kwargs) -> None:
            nonlocal worker_constructed
            worker_constructed = True

    monkeypatch.setattr("keith_ivt.ui.sweep_controller.messagebox.showerror", lambda *_args: None)
    monkeypatch.setattr("keith_ivt.ui.sweep_controller.threading.Thread", _UnexpectedThread)

    app.start_sweep()

    assert worker_constructed is False
    assert app.app_state.run_state is RunState.IDLE
    assert app.app_state.can_start_sweep() is True


def test_runtime_error_is_transient_and_recovers_connected_ui_to_idle(monkeypatch) -> None:
    app = _ControllerHarness(_config())
    assert app.app_state.dispatch(AppAction.START_SWEEP)
    app._stop_event.set()
    app._pause_event.set()
    app._current_range_control.request_fixed_range(1e-3)
    states_seen_by_dialog: list[RunState] = []
    monkeypatch.setattr(
        "keith_ivt.ui.sweep_controller.messagebox.showerror",
        lambda *_args: states_seen_by_dialog.append(app.app_state.run_state),
    )

    app._handle_error(RuntimeError("simulated worker failure"))

    assert states_seen_by_dialog == [RunState.ERROR]
    assert app.app_state.last_error == "simulated worker failure"
    assert app.app_state.run_state is RunState.IDLE
    assert app.app_state.can_start_sweep() is True
    assert app.start_enabled is True
    assert app._live_config is None
    assert app._live_points == []
    assert app._x_data == []
    assert app._y_data == []
    assert app._measurement_xy.cleared is True
    assert not app._stop_event.is_set()
    assert not app._pause_event.is_set()
    assert app._current_range_control.snapshot() == CurrentRangeState()
    assert app._current_range_control.drain_actions() == []
    assert app.popup_closed is True
    assert "simulated worker failure" in app.logs[-1]
