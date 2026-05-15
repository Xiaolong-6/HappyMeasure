"""Tests for unified hardware abstraction layer."""
import pytest
from keith_ivt.drivers.base import (
    ConnectionProfile,
    DriverReadback,
    MeasureMode,
    SMUDriver,
    SourceMode,
)
from keith_ivt.drivers.adapter import SourceMeterAdapter
from keith_ivt.drivers.factory import create_driver_from_source_meter, ensure_smu_driver
from keith_ivt.instrument.simulator import SimulatedKeithley
from keith_ivt.drivers.simulated_smu import SimulatedSMUDriver


class TestSourceMeterAdapter:
    """Test that legacy SourceMeter can be adapted to SMUDriver."""

    def test_adapter_creates_smu_driver(self):
        """Adapter should produce a valid SMUDriver."""
        meter = SimulatedKeithley()
        driver = SourceMeterAdapter(meter)

        assert isinstance(driver, SMUDriver)
        assert driver.capabilities is not None

    def test_adapter_connect_and_identify(self):
        """Adapter should support basic operations."""
        meter = SimulatedKeithley()
        driver = SourceMeterAdapter(meter)

        profile = ConnectionProfile(resource="COM3")
        driver.connect(profile)

        identity = driver.identify()
        assert "SIMULATED" in identity
        assert "KEITHLEY" in identity

    def test_adapter_configure_and_read(self):
        """Adapter should support configure and read cycle."""
        meter = SimulatedKeithley(resistance_ohm=1000.0)
        driver = SourceMeterAdapter(meter)

        driver.connect(ConnectionProfile())
        driver.configure_source_measure(
            source_mode=SourceMode.VOLTAGE,
            measure_mode=MeasureMode.CURRENT,
            compliance=0.01,
            nplc=1.0,
        )
        driver.output_on()
        driver.set_source(SourceMode.VOLTAGE, 1.0)

        readback = driver.read()
        assert isinstance(readback, DriverReadback)
        assert readback.source_value == pytest.approx(1.0, abs=0.01)
        # I = V/R = 1.0/1000 = 0.001 A
        assert readback.measured_value == pytest.approx(0.001, rel=0.05)

        driver.output_off()
        driver.close()

    def test_adapter_context_manager(self):
        """Adapter should work as context manager."""
        meter = SimulatedKeithley()
        with SourceMeterAdapter(meter) as driver:
            assert driver.capabilities is not None
            identity = driver.identify()
            assert "SIMULATED" in identity


class TestFactoryFunctions:
    """Test factory functions for driver creation."""

    def test_create_driver_from_source_meter(self):
        """Factory should create adapter from SourceMeter."""
        meter = SimulatedKeithley()
        driver = create_driver_from_source_meter(meter)

        assert isinstance(driver, SMUDriver)
        assert isinstance(driver, SourceMeterAdapter)

    def test_ensure_smu_driver_with_native_driver(self):
        """ensure_smu_driver should pass through native SMUDrivers."""
        native_driver = SimulatedSMUDriver()
        result = ensure_smu_driver(native_driver)

        assert result is native_driver  # Same instance

    def test_ensure_smu_driver_with_source_meter(self):
        """ensure_smu_driver should adapt legacy SourceMeters."""
        meter = SimulatedKeithley()
        result = ensure_smu_driver(meter)

        assert isinstance(result, SMUDriver)
        assert result is not meter  # Wrapped in adapter


class TestSimulatedKeithleyDualInterface:
    """Test that SimulatedKeithley supports both old and new interfaces."""

    def test_legacy_interface_still_works(self):
        """Old SourceMeter interface should still function."""
        meter = SimulatedKeithley(resistance_ohm=1000.0)

        meter.connect()
        assert meter.identify().startswith("SIMULATED")

        from keith_ivt.models import SweepConfig, SweepMode
        config = SweepConfig(
            mode=SweepMode.VOLTAGE_SOURCE,
            start=-1.0, stop=1.0, step=0.1,
            compliance=0.01,
            nplc=1.0,
        )
        meter.configure_for_sweep(config)
        meter.set_source("VOLT", 0.5)

        source, measured = meter.read_source_and_measure()
        assert source == pytest.approx(0.5, abs=0.01)
        assert measured == pytest.approx(0.0005, rel=0.05)  # 0.5V / 1000Ω

        meter.output_off()
        meter.close()

    def test_new_smudriver_interface_works(self):
        """New SMUDriver-compatible methods should work."""
        meter = SimulatedKeithley(resistance_ohm=1000.0)

        # Check capabilities property exists
        caps = meter.capabilities
        assert caps.supports_voltage_source is True
        assert caps.supports_current_source is True

        # Test SMUDriver-style methods
        meter.connect()
        meter.configure_source_measure(
            source_mode=SourceMode.VOLTAGE,
            measure_mode=MeasureMode.CURRENT,
            compliance=0.01,
            nplc=1.0,
        )
        meter.set_source(SourceMode.VOLTAGE, 0.5)

        readback = meter.read_smudriver()
        assert isinstance(readback, DriverReadback)
        assert readback.source_value == pytest.approx(0.5, abs=0.01)
        assert readback.measured_value == pytest.approx(0.0005, rel=0.05)

        meter.output_off()
        meter.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
