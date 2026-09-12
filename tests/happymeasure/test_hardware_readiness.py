from __future__ import annotations


def test_serial_retry_policy_retries_then_succeeds(monkeypatch) -> None:
    from keith_ivt.services import serial_safety
    from keith_ivt.services.serial_safety import SerialRetryPolicy

    monkeypatch.setattr(serial_safety.time, "sleep", lambda _s: None)
    attempts = {"n": 0}

    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise TimeoutError("temporary")
        return "ok"

    assert SerialRetryPolicy(max_attempts=3, base_delay_s=0.01).run(flaky) == "ok"
    assert attempts["n"] == 3


def test_output_off_guard_reports_failure() -> None:
    from keith_ivt.services.serial_safety import OutputOffGuard

    messages: list[str] = []
    ok = OutputOffGuard(logger=messages.append).turn_off(
        lambda: (_ for _ in ()).throw(RuntimeError("boom")), context="test"
    )

    assert ok is False
    assert messages and "Output OFF failed" in messages[0]


def test_hardware_preflight_identifies_instrument_and_confirms_output_off(monkeypatch) -> None:
    from keith_ivt.services import hardware_preflight

    calls: list[str] = []

    class FakeInstrument:
        def __init__(self, port, baud_rate):
            calls.append(f"init:{port}:{baud_rate}")

        def connect(self):
            calls.append("connect")

        def identify(self):
            calls.append("identify")
            return "KEITHLEY INSTRUMENTS INC.,MODEL 2400,123,1.0"

        def output_off(self):
            calls.append("output_off")

        def close(self):
            calls.append("close")

    monkeypatch.setattr(hardware_preflight, "Keithley2400Serial", FakeInstrument)

    result = hardware_preflight.run_keithley_preflight("COM9", 9600)

    assert result.port == "COM9"
    assert "MODEL 2400" in result.idn
    assert result.output_off_confirmed is True
    assert calls == ["init:COM9:9600", "connect", "identify", "output_off", "close"]
