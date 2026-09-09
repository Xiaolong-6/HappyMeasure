from __future__ import annotations

from keith_ivt.ui.sweep_config import SweepConfigMixin


class _FakeVar:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class _FakeWidget:
    def __init__(self):
        self.disabled = False
        self.exists = True

    def winfo_exists(self):
        return self.exists

    def state(self, states):
        if "disabled" in states:
            self.disabled = True
        if "!disabled" in states:
            self.disabled = False


class _Harness(SweepConfigMixin):
    def __init__(self, until_stop: bool = False):
        self.constant_until_stop = _FakeVar(until_stop)
        self.duration_s = _FakeVar(10.0)
        self.duration_row = (_FakeWidget(), _FakeWidget())
        self._connected = True
        self._run_state = "idle"


def test_finite_constant_time_enables_duration_label_and_entry():
    harness = _Harness(until_stop=False)

    harness._update_time_duration_state()

    assert harness.duration_row[0].disabled is False
    assert harness.duration_row[1].disabled is False


def test_constant_until_stop_disables_duration_label_and_entry():
    harness = _Harness(until_stop=True)

    harness._update_time_duration_state()

    assert harness.duration_row[0].disabled is True
    assert harness.duration_row[1].disabled is True


def test_duration_value_survives_toggle_and_dynamic_row_rebuild():
    harness = _Harness(until_stop=False)
    harness.duration_s.set(123.45)

    harness.constant_until_stop.set(True)
    harness._update_time_duration_state()
    rebuilt_row = (_FakeWidget(), _FakeWidget())
    harness.duration_row = rebuilt_row
    harness._update_time_duration_state()

    assert harness.duration_s.get() == 123.45
    assert rebuilt_row[0].disabled is True
    assert rebuilt_row[1].disabled is True

    harness.constant_until_stop.set(False)
    harness._update_time_duration_state()

    assert harness.duration_s.get() == 123.45
    assert rebuilt_row[0].disabled is False
    assert rebuilt_row[1].disabled is False
