from __future__ import annotations

from keith_ivt import hardware_preflight


def test_preflight_cli_reports_pass(monkeypatch, capsys) -> None:
    class Result:
        port = "COM9"
        baud_rate = 9600
        idn = "KEITHLEY INSTRUMENTS INC.,MODEL 2400,123,1.0"
        output_off_confirmed = True

    monkeypatch.setattr(hardware_preflight, "run_keithley_preflight", lambda port, baud, logger=None: Result())
    code = hardware_preflight.main(["COM9", "--baud", "9600"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Safety:" in out
    assert "PASS hardware preflight" in out
    assert "Output OFF confirmed: True" in out


def test_preflight_cli_reports_fail_without_traceback(monkeypatch, capsys) -> None:
    def fail(port, baud, logger=None):
        raise TimeoutError("no response")

    monkeypatch.setattr(hardware_preflight, "run_keithley_preflight", fail)
    code = hardware_preflight.main(["COM9"])
    out = capsys.readouterr().out
    assert code == 1
    assert "FAIL hardware preflight" in out
    assert "Reason: no response" in out
    assert "Traceback" not in out
