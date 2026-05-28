from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from keith_ivt.drivers.base import ConnectionProfile, DriverReadback, MeasureMode, SenseWiring, SourceMode, TerminalRoute
from keith_ivt.drivers.keithley2400_adapter import Keithley2400Driver


def _make_profile() -> ConnectionProfile:
    return ConnectionProfile(
        resource="COM3",
        baud_rate=9600,
        terminal=TerminalRoute.REAR,
        sense_wiring=SenseWiring.TWO_WIRE,
    )


def test_adapter_capabilities() -> None:
    assert Keithley2400Driver.capabilities.name == "Keithley 2400/2401 serial"
    assert Keithley2400Driver.capabilities.supports_front_rear is True
    assert Keithley2400Driver.capabilities.supports_4wire is True
    assert Keithley2400Driver.capabilities.supports_cv is False


def test_adapter_require_driver_raises_when_not_connected() -> None:
    drv = Keithley2400Driver()
    import pytest
    with pytest.raises(RuntimeError, match="not connected"):
        drv.identify()


def test_adapter_close_when_not_connected() -> None:
    drv = Keithley2400Driver()
    drv.close()
    assert drv._driver is None


def test_adapter_disconnect_calls_close() -> None:
    drv = Keithley2400Driver()
    drv.disconnect()
    assert drv._driver is None


def test_adapter_context_manager() -> None:
    drv = Keithley2400Driver()
    mock_driver = MagicMock()
    mock_driver.read_source_and_measure.return_value = (1.0, 0.001)
    drv._driver = mock_driver
    drv._profile = _make_profile()

    with patch.object(drv, "connect"):
        with drv:
            pass

    mock_driver.output_off.assert_called_once()
    mock_driver.close.assert_called_once()


def test_adapter_context_manager_no_output_off_on_error() -> None:
    drv = Keithley2400Driver()
    mock_driver = MagicMock()
    drv._driver = mock_driver
    drv._profile = _make_profile()

    try:
        with patch.object(drv, "connect"):
            with drv:
                raise ValueError("test error")
    except ValueError:
        pass

    mock_driver.output_off.assert_called_once()
    mock_driver.close.assert_called_once()


def test_adapter_configure_source_measure_cv_raises() -> None:
    drv = Keithley2400Driver()
    mock_driver = MagicMock()
    drv._driver = mock_driver
    drv._profile = _make_profile()

    import pytest
    with pytest.raises(NotImplementedError, match="CV mode"):
        drv.configure_source_measure(
            SourceMode.VOLTAGE,
            MeasureMode.CAPACITANCE,
            compliance=1.0,
            nplc=1.0,
        )


def test_adapter_set_source() -> None:
    drv = Keithley2400Driver()
    mock_driver = MagicMock()
    drv._driver = mock_driver
    drv.set_source(SourceMode.VOLTAGE, 2.5)
    mock_driver.set_source.assert_called_once_with("VOLT", 2.5)


def test_adapter_read() -> None:
    drv = Keithley2400Driver()
    mock_driver = MagicMock()
    mock_driver.read_source_and_measure.return_value = (1.5, 0.002)
    drv._driver = mock_driver
    result = drv.read()
    assert isinstance(result, DriverReadback)
    assert result.source_value == 1.5
    assert result.measured_value == 0.002


def test_adapter_output_on_off() -> None:
    drv = Keithley2400Driver()
    mock_driver = MagicMock()
    drv._driver = mock_driver
    drv.output_on()
    mock_driver.output_on.assert_called_once()
    drv.output_off()
    mock_driver.output_off.assert_called_once()


def test_adapter_identify() -> None:
    drv = Keithley2400Driver()
    mock_driver = MagicMock()
    mock_driver.identify.return_value = "KEITHLEY,2400,0.1"
    drv._driver = mock_driver
    assert drv.identify() == "KEITHLEY,2400,0.1"


def test_adapter_reset() -> None:
    drv = Keithley2400Driver()
    mock_driver = MagicMock()
    drv._driver = mock_driver
    drv.reset()
    mock_driver.reset.assert_called_once()
