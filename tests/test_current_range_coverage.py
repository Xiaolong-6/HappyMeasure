from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from keith_ivt.core.current_range import (
    CURRENT_RANGE_OPTIONS_A,
    CurrentRangeAction,
    CurrentRangeControl,
    CurrentRangeState,
    current_range_labels,
    format_current_range,
    parse_current_range_label,
)


def test_format_current_range_none_returns_unknown() -> None:
    assert format_current_range(None) == "Unknown"


def test_format_current_range_milliamperes() -> None:
    result = format_current_range(1e-3)
    assert "mA" in result
    assert "1" in result


def test_format_current_range_microamperes() -> None:
    result = format_current_range(5e-6)
    assert "uA" in result


def test_format_current_range_nanoamperes() -> None:
    result = format_current_range(100e-9)
    assert "nA" in result


def test_format_current_range_picoamperes() -> None:
    result = format_current_range(1e-12)
    assert "pA" in result


def test_format_current_range_fractional_not_round() -> None:
    result = format_current_range(1.5e-3)
    assert "mA" in result
    assert "1.5" in result


def test_format_current_range_amperes_fallback() -> None:
    result = format_current_range(5.0)
    assert result.endswith("A")


def test_current_range_labels_returns_list() -> None:
    labels = current_range_labels()
    assert isinstance(labels, list)
    assert len(labels) == len(CURRENT_RANGE_OPTIONS_A)
    for label in labels:
        assert "A" in label


def test_parse_current_range_label_exact_match() -> None:
    for value in CURRENT_RANGE_OPTIONS_A:
        label = format_current_range(value) + f" ({value:.0e} A)"
        result = parse_current_range_label(label)
        assert result == value


def test_parse_current_range_label_numeric_fallback() -> None:
    result = parse_current_range_label("0.001")
    assert result == 0.001


def test_parse_current_range_label_invalid_returns_none() -> None:
    result = parse_current_range_label("not_a_number")
    assert result is None


def test_current_range_state_headline_autorange_true() -> None:
    state = CurrentRangeState(autorange=True, actual_range_A=1e-6)
    assert "AUTO" in state.headline()
    assert "1 uA" in state.headline()


def test_current_range_state_headline_autorange_false() -> None:
    state = CurrentRangeState(autorange=False, fixed_range_A=10e-9, actual_range_A=1e-9)
    headline = state.headline()
    assert "FIXED" in headline
    assert "10 nA" in headline


def test_current_range_state_headline_autorange_none() -> None:
    state = CurrentRangeState(autorange=None, actual_range_A=1e-3)
    assert "Unknown" in state.headline()
    assert "1 mA" in state.headline()


def test_current_range_state_status_fragment_autorange_true() -> None:
    state = CurrentRangeState(autorange=True, actual_range_A=1e-9)
    assert state.status_fragment() == "Auto/1 nA"


def test_current_range_state_status_fragment_autorange_false() -> None:
    state = CurrentRangeState(autorange=False, fixed_range_A=10e-9, actual_range_A=1e-9)
    assert state.status_fragment() == "Fixed/10 nA"


def test_current_range_state_status_fragment_none() -> None:
    state = CurrentRangeState(autorange=None)
    assert state.status_fragment() == "Unknown"


def test_last_change_text_none() -> None:
    state = CurrentRangeState()
    assert state.last_change_text() == "none"


def test_last_change_text_with_monotonic() -> None:
    state = CurrentRangeState(last_change_monotonic_s=100.0)
    result = state.last_change_text(now_s=105.0)
    assert "5.0 s ago" in result


def test_last_change_text_negative_clamped() -> None:
    state = CurrentRangeState(last_change_monotonic_s=200.0)
    result = state.last_change_text(now_s=100.0)
    assert "0.0 s ago" in result


def test_last_change_text_uses_monotonic_by_default() -> None:
    import time
    state = CurrentRangeState(last_change_monotonic_s=time.monotonic() - 1.0)
    result = state.last_change_text()
    assert "ago" in result


def test_current_range_control_snapshot() -> None:
    ctrl = CurrentRangeControl()
    snap = ctrl.snapshot()
    assert isinstance(snap, CurrentRangeState)
    assert snap.autorange is None


def test_current_range_control_update_state_detects_change() -> None:
    ctrl = CurrentRangeControl()
    ctrl.update_state(CurrentRangeState(actual_range_A=1e-9))
    result = ctrl.update_state(CurrentRangeState(actual_range_A=10e-9))
    assert result.last_change_monotonic_s is not None


def test_current_range_control_update_state_no_change() -> None:
    ctrl = CurrentRangeControl()
    ctrl.update_state(CurrentRangeState(actual_range_A=1e-9))
    result = ctrl.update_state(CurrentRangeState(actual_range_A=1e-9))
    assert result.last_change_monotonic_s is None


def test_current_range_control_with_warning() -> None:
    ctrl = CurrentRangeControl()
    result = ctrl.with_warning("test warning")
    assert result.warning == "test warning"
    assert ctrl.snapshot().warning == "test warning"


def test_current_range_control_request_autorange() -> None:
    ctrl = CurrentRangeControl()
    ctrl.request_autorange(True)
    actions = ctrl.drain_actions()
    assert len(actions) == 1
    assert actions[0].kind == "autorange"
    assert actions[0].value is True


def test_current_range_control_request_fixed_range() -> None:
    ctrl = CurrentRangeControl()
    ctrl.request_fixed_range(1e-6)
    actions = ctrl.drain_actions()
    assert len(actions) == 1
    assert actions[0].kind == "fixed_range"
    assert actions[0].value == 1e-6


def test_current_range_control_request_lock_current() -> None:
    ctrl = CurrentRangeControl()
    ctrl.request_lock_current()
    actions = ctrl.drain_actions()
    assert len(actions) == 1
    assert actions[0].kind == "lock_current"
    assert actions[0].value is None


def test_drain_actions_returns_empty_when_nothing_pending() -> None:
    ctrl = CurrentRangeControl()
    assert ctrl.drain_actions() == []


def test_current_range_action_frozen() -> None:
    action = CurrentRangeAction(kind="autorange", value=True)
    assert action.kind == "autorange"
    assert action.value is True
