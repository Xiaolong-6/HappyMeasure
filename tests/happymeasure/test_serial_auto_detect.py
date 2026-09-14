from __future__ import annotations

from serial.tools import list_ports

from keith_ivt import hardware_preflight
from keith_ivt.services import serial_discovery
from keith_ivt.services.serial_discovery import (
    SerialDiscoveryResult,
    available_serial_ports,
    discover_supported_serial_hardware,
    probe_serial_identity,
    supported_2400_identity,
)
from keith_ivt.ui import serial_auto_detect
from keith_ivt.ui.serial_auto_detect import SerialAutoDetectMixin


class _Var:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value) -> None:
        self.value = value


class _Widget:
    def __init__(self) -> None:
        self.options: dict[str, object] = {}

    def configure(self, **kwargs) -> None:
        self.options.update(kwargs)

    def winfo_exists(self) -> bool:
        return True


class _Root:
    def __init__(self) -> None:
        self.update_calls = 0

    def update_idletasks(self) -> None:
        self.update_calls += 1


class _Delegate:
    def connect_or_disconnect(self) -> None:
        self.delegate_calls += 1


class _AutoDetectHarness(SerialAutoDetectMixin, _Delegate):
    def __init__(self) -> None:
        self._connected = False
        self._run_state = "idle"
        self.debug = _Var(False)
        self.port = _Var("COM3")
        self.baud_rate = _Var(9600)
        self.hardware_profile_text = _Var("--")
        self.detect_btn = _Widget()
        self.port_combo = _Widget()
        self.root = _Root()
        self.logs: list[str] = []
        self.delegate_calls = 0

    def log_event(self, message: str) -> None:
        self.logs.append(message)

    def _safe_configure(self, attr: str, **kwargs) -> None:
        widget = getattr(self, attr, None)
        if widget is not None:
            widget.configure(**kwargs)

    def _refresh_port_choices(self) -> list[str]:
        return [str(self.port.get())]

    def _update_run_button_states(self) -> None:
        pass


def test_available_serial_ports_filters_blanks_and_degrades(monkeypatch) -> None:
    class Port:
        def __init__(self, device: str) -> None:
            self.device = device

    monkeypatch.setattr(list_ports, "comports", lambda: [Port("COM7"), Port(""), Port("COM9")])
    assert available_serial_ports() == ["COM7", "COM9"]

    def fail():
        raise RuntimeError("enumeration unavailable")

    monkeypatch.setattr(list_ports, "comports", fail)
    assert available_serial_ports() == []


def test_probe_serial_identity_uses_one_short_read_only_session(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeKeithley:
        def __init__(self, **kwargs) -> None:
            captured.update(kwargs)

        def __enter__(self):
            captured["entered"] = True
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            captured["closed"] = True

        def identify(self) -> str:
            return "KEITHLEY INSTRUMENTS INC.,MODEL 2400,123,1.0"

    monkeypatch.setattr(serial_discovery, "Keithley2400Serial", FakeKeithley)
    idn = probe_serial_identity("COM5", 19200)

    assert "MODEL 2400" in idn
    assert captured["port"] == "COM5"
    assert captured["baud_rate"] == 19200
    assert captured["timeout"] == serial_discovery.DISCOVERY_TIMEOUT_S
    assert captured["retry_policy"].max_attempts == 1
    assert captured["entered"] is True
    assert captured["closed"] is True


def test_discovery_prefers_current_selection_and_returns_supported_model() -> None:
    calls: list[tuple[str, int]] = []

    def probe(port: str, baud: int) -> str:
        calls.append((port, baud))
        if (port, baud) == ("COM9", 57600):
            return "KEITHLEY INSTRUMENTS INC.,MODEL 2401,123,1.0"
        raise TimeoutError("no response")

    result = discover_supported_serial_hardware(
        preferred_port="COM9",
        preferred_baud=57600,
        ports=["COM3", "COM9"],
        baud_rates=[9600, 57600],
        probe=probe,
    )

    assert result == SerialDiscoveryResult(
        port="COM9",
        baud_rate=57600,
        idn="KEITHLEY INSTRUMENTS INC.,MODEL 2401,123,1.0",
        model="2401",
    )
    assert calls == [("COM9", 57600)]


def test_discovery_skips_wrong_baud_and_unsupported_instrument() -> None:
    replies = {
        ("COM4", 9600): "TEKTRONIX,OTHER,123,1.0",
        ("COM4", 19200): "KEITHLEY INSTRUMENTS INC.,MODEL 2450,123,1.0",
        ("COM7", 9600): "KEITHLEY INSTRUMENTS INC.,MODEL 2400,123,1.0",
    }

    def probe(port: str, baud: int) -> str:
        if (port, baud) not in replies:
            raise TimeoutError("no response")
        return replies[(port, baud)]

    result = discover_supported_serial_hardware(
        ports=["COM4", "COM7"],
        baud_rates=[9600, 19200],
        probe=probe,
    )

    assert result is not None
    assert (result.port, result.baud_rate, result.model) == ("COM7", 9600, "2400")
    assert supported_2400_identity(replies[("COM4", 19200)]) == (False, "2450")


def test_discovery_uses_enumerated_ports_and_can_return_none(monkeypatch) -> None:
    monkeypatch.setattr(serial_discovery, "available_serial_ports", lambda: ["", "COM6"])
    calls: list[tuple[str, int]] = []

    def probe(port: str, baud: int) -> str:
        calls.append((port, baud))
        return "NOT-KEITHLEY,OTHER,0,0"

    result = discover_supported_serial_hardware(baud_rates=[9600], probe=probe)

    assert result is None
    assert calls == [("COM6", 9600)]


def test_manual_auto_detect_updates_selectors_and_detected_model(monkeypatch) -> None:
    harness = _AutoDetectHarness()
    match = SerialDiscoveryResult(
        port="COM8",
        baud_rate=38400,
        idn="KEITHLEY INSTRUMENTS INC.,MODEL 2400,123,1.0",
        model="2400",
    )
    monkeypatch.setattr(
        serial_auto_detect,
        "discover_supported_serial_hardware",
        lambda **kwargs: match,
    )

    assert harness.auto_detect_hardware() is True

    assert harness.port.get() == "COM8"
    assert harness.baud_rate.get() == 38400
    assert harness.hardware_profile_text.get() == "Keithley 2400 — detected on COM8 @ 38400"
    assert harness.root.update_calls == 1
    assert harness.detect_btn.options["text"] == "Auto Detect"
    assert any("Auto-detected Keithley 2400" in message for message in harness.logs)


def test_manual_auto_detect_reports_no_match_without_changing_selection(monkeypatch) -> None:
    harness = _AutoDetectHarness()
    warnings: list[tuple[str, str]] = []
    monkeypatch.setattr(
        serial_auto_detect,
        "discover_supported_serial_hardware",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        serial_auto_detect.messagebox,
        "showwarning",
        lambda title, text: warnings.append((title, text)),
    )

    assert harness.auto_detect_hardware() is False

    assert harness.port.get() == "COM3"
    assert harness.baud_rate.get() == 9600
    assert harness.hardware_profile_text.get() == "No supported Keithley detected"
    assert warnings and warnings[0][0] == "Hardware not detected"


def test_connect_auto_detect_updates_port_and_baud_before_delegate(monkeypatch) -> None:
    harness = _AutoDetectHarness()
    match = SerialDiscoveryResult(
        port="COM8",
        baud_rate=38400,
        idn="KEITHLEY INSTRUMENTS INC.,MODEL 2400,123,1.0",
        model="2400",
    )
    monkeypatch.setattr(
        serial_auto_detect,
        "discover_supported_serial_hardware",
        lambda **kwargs: match,
    )

    harness.connect_or_disconnect()

    assert harness.port.get() == "COM8"
    assert harness.baud_rate.get() == 38400
    assert harness.delegate_calls == 1
    assert any("Auto-detected Keithley 2400" in message for message in harness.logs)


def test_connect_auto_detect_preserves_manual_fallback(monkeypatch) -> None:
    harness = _AutoDetectHarness()
    monkeypatch.setattr(
        serial_auto_detect,
        "discover_supported_serial_hardware",
        lambda **kwargs: None,
    )

    harness.connect_or_disconnect()

    assert harness.port.get() == "COM3"
    assert harness.baud_rate.get() == 9600
    assert harness.delegate_calls == 1
    assert any("trying the selected COM/baud" in message for message in harness.logs)


def test_preflight_cli_can_auto_detect_without_positional_port(monkeypatch, capsys) -> None:
    match = SerialDiscoveryResult(
        port="COM11",
        baud_rate=57600,
        idn="KEITHLEY INSTRUMENTS INC.,MODEL 2401,123,1.0",
        model="2401",
    )

    class Result:
        port = "COM11"
        baud_rate = 57600
        idn = match.idn
        output_off_confirmed = True

    monkeypatch.setattr(
        hardware_preflight,
        "discover_supported_serial_hardware",
        lambda **kwargs: match,
    )
    monkeypatch.setattr(
        hardware_preflight,
        "run_keithley_preflight",
        lambda port, baud, logger=None: Result(),
    )

    code = hardware_preflight.main([])
    out = capsys.readouterr().out

    assert code == 0
    assert "Auto-detected Keithley 2401 on COM11 at 57600 baud" in out
    assert "PASS hardware preflight" in out
