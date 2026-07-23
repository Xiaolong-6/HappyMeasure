from __future__ import annotations

import pytest

from keith_ivt.ui.widget_helpers import WidgetHelperMixin


class FakeNumericVar:
    def __init__(self, name: str, value: float | int | str) -> None:
        self.name = name
        self.value = value

    def __str__(self) -> str:
        return self.name

    def get(self):
        if self.value in {"", "not-a-number"}:
            raise ValueError("invalid numeric value")
        return self.value

    def set(self, value) -> None:
        self.value = value


def test_empty_numeric_value_restores_captured_default() -> None:
    helper = WidgetHelperMixin()
    delay = FakeNumericVar("delay", 0.25)

    helper._capture_numeric_entry_defaults((delay,))
    delay.value = ""

    assert helper._restore_numeric_entry_default(delay) is True
    assert delay.value == pytest.approx(0.25)


@pytest.mark.parametrize("invalid_value", ["not-a-number", float("nan"), float("inf")])
def test_invalid_or_nonfinite_value_restores_default(invalid_value) -> None:
    helper = WidgetHelperMixin()
    nplc = FakeNumericVar("nplc", 1.0)

    helper._capture_numeric_entry_defaults((nplc,))
    nplc.value = invalid_value

    assert helper._restore_numeric_entry_default(nplc) is True
    assert nplc.value == pytest.approx(1.0)


def test_valid_numeric_value_is_preserved() -> None:
    helper = WidgetHelperMixin()
    compliance = FakeNumericVar("compliance", 0.01)

    helper._capture_numeric_entry_defaults((compliance,))
    compliance.value = 0.02

    assert helper._restore_numeric_entry_default(compliance) is False
    assert compliance.value == pytest.approx(0.02)


def test_recapturing_defaults_ignores_an_invalid_live_value() -> None:
    helper = WidgetHelperMixin()
    source_range = FakeNumericVar("source-range", 1.0)

    helper._capture_numeric_entry_defaults((source_range,))
    source_range.value = ""
    helper._capture_numeric_entry_defaults((source_range,))

    assert helper._restore_numeric_entry_default(source_range) is True
    assert source_range.value == pytest.approx(1.0)
