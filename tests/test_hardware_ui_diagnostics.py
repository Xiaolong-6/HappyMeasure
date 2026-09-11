from __future__ import annotations

from pathlib import Path

from keith_ivt.diagnostics.hardware_self_test import (
    FAIL,
    MANUAL,
    PASS,
    run_hardware_self_test,
)


class _FakeKeithley:
    def __init__(
        self,
        *,
        events: list[str],
        idn: str = "KEITHLEY INSTRUMENTS INC.,MODEL 2401,B02",
        output_state: str = "0",
        beep_error: Exception | None = None,
        **_kwargs,
    ) -> None:
        self.events = events
        self.idn = idn
        self.output_state = output_state
        self.beep_error = beep_error

    def __enter__(self):
        self.events.append("connect")
        return self

    def __exit__(self, exc_type, exc, tb):
        self.events.append("close")
        return False

    def output_off(self) -> None:
        self.events.append("output_off")

    def identify(self) -> str:
        self.events.append("identify")
        return self.idn

    def query(self, command: str) -> str:
        self.events.append(f"query:{command}")
        if command == ":OUTP?":
            return self.output_state
        raise AssertionError(f"unexpected query: {command}")

    def beep(self) -> None:
        self.events.append("beep")
        if self.beep_error is not None:
            raise self.beep_error


def _factory(
    events: list[str],
    *,
    idn: str = "KEITHLEY INSTRUMENTS INC.,MODEL 2401,B02",
    output_state: str = "0",
    beep_error: Exception | None = None,
):
    def create(**kwargs):
        return _FakeKeithley(
            events=events,
            idn=idn,
            output_state=output_state,
            beep_error=beep_error,
            **kwargs,
        )

    return create


def test_safe_hardware_diagnostic_never_enables_or_configures_output() -> None:
    events: list[str] = []
    report = run_hardware_self_test(
        "COM7",
        57600,
        instrument_factory=_factory(events),
    )

    assert report.overall == PASS
    assert events.count("connect") == 2
    assert events.count("close") == 2
    assert events.count("output_off") >= 4
    assert events.count("beep") == 1
    assert "query::OUTP?" in events
    assert any(check.status == MANUAL and check.name == "Physical beep" for check in report.checks)

    source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "keith_ivt"
        / "diagnostics"
        / "hardware_self_test.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        '":READ?"',
        '":SOUR:',
        ".output_on(",
        ".configure_for_sweep(",
        ".reset(",
    ):
        assert forbidden not in source


def test_hardware_diagnostic_fails_if_output_cannot_be_verified_off() -> None:
    events: list[str] = []
    report = run_hardware_self_test(
        "COM7",
        57600,
        instrument_factory=_factory(events, output_state="1"),
    )

    assert report.overall == FAIL
    check = next(c for c in report.checks if c.name == "Output-state verification")
    assert check.status == FAIL
    assert events.count("output_off") >= 2
    assert "beep" not in events


def test_hardware_diagnostic_refuses_unvalidated_identity_before_beep() -> None:
    events: list[str] = []
    report = run_hardware_self_test(
        "COM7",
        57600,
        instrument_factory=_factory(events, idn="OTHER,VIRTUAL METER,1"),
    )

    assert report.overall == FAIL
    identity = next(c for c in report.checks if c.name == "Instrument identity")
    assert identity.status == FAIL
    assert "beep" not in events
    assert events.count("output_off") >= 2


def test_beeper_failure_is_warning_not_loss_of_output_cleanup() -> None:
    events: list[str] = []
    report = run_hardware_self_test(
        "COM7",
        57600,
        instrument_factory=_factory(events, beep_error=RuntimeError("silent")),
    )

    assert report.overall != FAIL
    beep = next(c for c in report.checks if c.name == "Beeper command")
    assert beep.status != PASS
    assert events.count("output_off") >= 4


def test_settings_wires_separate_developer_tools_and_both_diagnostics() -> None:
    root = Path(__file__).resolve().parents[1]
    settings_panel = (root / "src" / "keith_ivt" / "ui" / "settings_panel.py").read_text(
        encoding="utf-8"
    )
    diagnostics = (
        root / "src" / "keith_ivt" / "ui" / "diagnostics_panel.py"
    ).read_text(encoding="utf-8")
    mixins = (root / "src" / "keith_ivt" / "ui" / "app_mixins.py").read_text(
        encoding="utf-8"
    )

    assert "SettingsPanelMixin" in mixins
    assert "Show developer tools" in settings_panel
    assert "Use debug simulator" in settings_panel
    assert "Run UI Diagnostics..." in settings_panel
    assert "Run Hardware Diagnostics..." in settings_panel
    assert "UI font" in settings_panel and "UI theme" in settings_panel
    assert "if not bool(developer_tools.get())" in settings_panel
    assert settings_panel.index('"UI font"') < settings_panel.index(
        "if not bool(developer_tools.get())"
    )
    assert "I confirm no DUT or analog test leads are connected." in diagnostics
    assert "Source output will not be enabled." in diagnostics
