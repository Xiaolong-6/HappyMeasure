# Hardware Driver Migration Guide (0.5 → 0.6)

This guide explains the hardware abstraction layer unification in HappyMeasure 0.6.0 and how to migrate existing code.

## Overview

HappyMeasure 0.6.0 consolidates two separate hardware interfaces into a single unified `SMUDriver` protocol:

- **Old**: `keith_ivt.instrument.base.SourceMeter` (ABC-based)
- **New**: `keith_ivt.drivers.base.SMUDriver` (Protocol-based, enhanced)

The new interface provides better type safety, richer metadata (capabilities, connection profiles), and supports future expansion for CV/capacitance measurements.

## Why Unify?

1. **Single source of truth**: One interface for all hardware drivers
2. **Better type checking**: Protocol-based design enables static analysis
3. **Richer metadata**: Connection profiles, driver capabilities, structured readbacks
4. **Future-proof**: Easier to add new instrument types (Keysight, NI, etc.)
5. **Cleaner testing**: Single mock interface for all tests

## Migration Path

### Option 1: Use the Adapter (Quick Fix)

If you have existing `SourceMeter` code, wrap it with the adapter:

```python
from keith_ivt.instrument.simulator import SimulatedKeithley
from keith_ivt.drivers import ensure_smu_driver, ConnectionProfile

# Old code
meter = SimulatedKeithley()
meter.connect()
meter.configure_for_sweep(config)
source, measure = meter.read_source_and_measure()

# New code (with adapter)
meter = SimulatedKeithley()
driver = ensure_smu_driver(meter)  # Automatically adapts if needed
driver.connect(ConnectionProfile(resource="COM3"))
driver.configure_source_measure(
    source_mode=SourceMode.VOLTAGE,
    measure_mode=MeasureMode.CURRENT,
    compliance=0.01,
    nplc=1.0,
)
readback = driver.read()  # Returns structured DriverReadback
print(f"Source: {readback.source_value}, Measured: {readback.measured_value}")
```

### Option 2: Native SMUDriver Implementation (Recommended)

For new drivers, implement `SMUDriver` directly:

```python
from keith_ivt.drivers.base import (
    SMUDriver,
    ConnectionProfile,
    DriverCapabilities,
    DriverReadback,
    SourceMode,
    MeasureMode,
)

class MyNewDriver(SMUDriver):
    capabilities = DriverCapabilities(
        name="My Instrument",
        vendor="Acme Corp",
        model_family="acme-smu",
        supports_voltage_source=True,
        supports_current_source=True,
    )

    def __init__(self):
        self._profile: ConnectionProfile | None = None
        self._connected = False

    def connect(self, profile: ConnectionProfile) -> None:
        self._profile = profile
        # Open serial/USB/GPIB connection
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def identify(self) -> str:
        return "ACME,MODEL-123,12345,1.0"

    def reset(self) -> None:
        # Reset instrument to default state
        pass

    def configure_source_measure(
        self,
        source_mode: SourceMode,
        measure_mode: MeasureMode,
        compliance: float,
        nplc: float,
        autorange: bool = True,
        source_range: float | None = None,
        measure_range: float | None = None,
    ) -> None:
        # Configure instrument
        pass

    def set_source(self, source_mode: SourceMode, value: float) -> None:
        # Set source value
        pass

    def read(self) -> DriverReadback:
        # Read and return structured data
        return DriverReadback(
            source_value=...,
            measured_value=...,
            timestamp_s=time.time(),
        )

    def output_on(self) -> None:
        pass

    def output_off(self) -> None:
        pass

    def close(self) -> None:
        self.disconnect()
```

## Key Differences

| Feature | SourceMeter (Old) | SMUDriver (New) |
|---------|------------------|-----------------|
| **Type** | Abstract Base Class | Protocol (structural typing) |
| **Connect** | `connect()` no args | `connect(profile: ConnectionProfile)` |
| **Configure** | `configure_for_sweep(config: SweepConfig)` | `configure_source_measure(...)` explicit params |
| **Read** | Returns `tuple[float, float]` | Returns `DriverReadback` dataclass |
| **Capabilities** | None | `capabilities: DriverCapabilities` |
| **Context Manager** | Yes | Yes |

## Using MeasurementService

The new `MeasurementService` works with `SMUDriver`:

```python
from keith_ivt.drivers import SimulatedSMUDriver, ConnectionProfile
from keith_ivt.services.measurement_service import MeasurementService
from keith_ivt.sweeps.plan import SweepPlan, SweepExecutionKind

# Create driver
driver = SimulatedSMUDriver()
driver.connect(ConnectionProfile(resource="COM3"))

# Create service
service = MeasurementService(driver)

# Execute sweep plan
plan = SweepPlan.step_sweep(
    start=-1.0,
    stop=1.0,
    step=0.1,
    source_mode=SourceMode.VOLTAGE,
    measure_mode=MeasureMode.CURRENT,
    compliance=0.01,
)

def on_point(readback, index, total):
    print(f"Point {index}/{total}: {readback.source_value:.3f}V, {readback.measured_value:.6f}A")

readbacks = service.run_plan(plan, on_point=on_point)
```

## Backward Compatibility

All existing `SourceMeter` implementations continue to work via the adapter:

- `SimulatedKeithley` → Auto-adapted when passed to `ensure_smu_driver()`
- `Keithley2400Serial` → Can be wrapped with `SourceMeterAdapter()`
- `SweepRunner` → Still uses `SourceMeter` (migration ongoing)

## Timeline

- **0.5.x**: Both interfaces coexist; adapter available
- **0.6.0-alpha**: Default to `SMUDriver` for new code
- **0.6.0-beta**: Deprecate `SourceMeter` (warnings issued)
- **0.7.0**: Remove `SourceMeter` entirely

## Testing Your Migration

Run the validation suite:

```bash
python tests/run_full_validation.py
python -m pytest tests/test_hardware_abstraction.py -v
```

## Need Help?

- See `src/keith_ivt/drivers/adapter.py` for adapter implementation details
- Check `src/keith_ivt/drivers/simulated_smu.py` for reference implementation
- Review `docs/HARDWARE_DRY_RUN_GUIDE.md` for hardware testing procedures
