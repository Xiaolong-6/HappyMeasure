from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math


class SweepMode(str, Enum):
    VOLTAGE_SOURCE = "VOLT"  # source voltage, measure current
    CURRENT_SOURCE = "CURR"  # source current, measure voltage


class Terminal(str, Enum):
    FRONT = "FRON"
    REAR = "REAR"


class SenseMode(str, Enum):
    TWO_WIRE = "2W"
    FOUR_WIRE = "4W"


class SweepKind(str, Enum):
    STEP = "STEP"
    CONSTANT_TIME = "TIME"
    MANUAL_OUTPUT = "MANUAL_OUTPUT"
    ADAPTIVE = "ADAPTIVE"


@dataclass(frozen=True)
class SweepConfig:
    mode: SweepMode
    start: float
    stop: float
    step: float
    compliance: float
    nplc: float = 1.0
    delay_s: float = 0.0
    port: str = "COM3"
    baud_rate: int = 9600
    terminal: Terminal = Terminal.REAR
    sense_mode: SenseMode = SenseMode.TWO_WIRE
    device_name: str = "Device_1"
    operator: str = ""
    debug: bool = False
    output_off_after_run: bool = True
    sweep_kind: SweepKind = SweepKind.STEP
    hysteresis: bool = False
    constant_value: float = 0.0
    duration_s: float = 10.0
    continuous_time: bool = False
    interval_s: float = 0.5
    autorange: bool = True
    auto_source_range: bool = True
    auto_measure_range: bool = True
    source_range: float = 0.0
    measure_range: float = 0.0
    range_settle_delay_ms: int = 300
    discard_after_range_change: int = 2
    adaptive_logic: str = "values = logspace(1e-3, 1, 31)"
    adaptive_segments: str = ""
    adaptive_remove_duplicates: bool = True
    debug_model: str = "Linear resistor 10 kΩ"

    # Constant-Time acquisition profile. Standard preserves historical behavior;
    # Fast applies the benchmark-backed 2400/2401 host-query preset; Custom
    # exposes each instrument/data-transfer knob separately.
    fast_acquisition: bool = False
    custom_acquisition: bool = False
    zero_refresh_before_run: bool = True
    autozero_during_run: bool = False
    digital_filter: bool = False
    digital_filter_count: int = 2
    concurrent_measurement: bool = False
    display_during_run: bool = True
    measurement_only_read: bool = True
    range_telemetry: bool = False
    source_write_each_sample: bool = False
    trigger_delay_s: float = 0.0

    @property
    def source_scpi(self) -> str:
        return self.mode.value

    @property
    def measure_scpi(self) -> str:
        return "CURR" if self.mode is SweepMode.VOLTAGE_SOURCE else "VOLT"

    @property
    def source_label(self) -> str:
        return "Voltage (V)" if self.mode is SweepMode.VOLTAGE_SOURCE else "Current (A)"

    @property
    def measure_label(self) -> str:
        return "Current (A)" if self.mode is SweepMode.VOLTAGE_SOURCE else "Voltage (V)"

    @property
    def csv_headers(self) -> tuple[str, str]:
        if self.mode is SweepMode.VOLTAGE_SOURCE:
            return "Voltage_V", "Current_A"
        return "Current_A", "Voltage_V"


@dataclass(frozen=True)
class SweepPoint:
    source_value: float
    measured_value: float
    elapsed_s: float = 0.0
    timestamp: str = ""


@dataclass(frozen=True)
class SweepResult:
    config: SweepConfig
    points: list[SweepPoint]


def make_source_values(start: float, stop: float, step: float) -> list[float]:
    """Generate source values using ``step`` as a positive magnitude."""
    if not all(math.isfinite(float(value)) for value in (start, stop, step)):
        raise ValueError("Start, stop, and step must be finite.")
    if step == 0:
        raise ValueError("Step cannot be zero.")
    if start == stop:
        return [float(start)]

    values: list[float] = []
    x = start
    step_magnitude = abs(step)
    directed_step = step_magnitude if start < stop else -step_magnitude
    eps = step_magnitude * 1e-9 + 1e-15
    if directed_step > 0:
        while x <= stop + eps:
            values.append(float(x))
            x += directed_step
    else:
        while x >= stop - eps:
            values.append(float(x))
            x += directed_step
    return values


def make_hysteresis_values(values: list[float]) -> list[float]:
    if not values:
        return []
    if len(values) == 1:
        return [float(values[0])]
    return [float(v) for v in values] + [float(v) for v in reversed(values[:-1])]


def source_values_for_config(config: SweepConfig) -> list[float]:
    if config.sweep_kind is SweepKind.CONSTANT_TIME:
        if config.continuous_time:
            return []
        return make_constant_time_values(
            config.constant_value, config.duration_s, config.interval_s
        )
    if config.sweep_kind is SweepKind.ADAPTIVE:
        if config.adaptive_segments.strip():
            from keith_ivt.sweeps.table_sweep import parse_segment_text

            values = parse_segment_text(
                config.adaptive_segments,
                remove_duplicates=config.adaptive_remove_duplicates,
            )
        else:
            from keith_ivt.core.adaptive_logic import adaptive_values_from_logic

            values = adaptive_values_from_logic(
                config.adaptive_logic,
                remove_duplicates=config.adaptive_remove_duplicates,
            )
        return make_hysteresis_values(values) if config.hysteresis else values
    values = make_source_values(config.start, config.stop, config.step)
    return make_hysteresis_values(values) if config.hysteresis else values


def serial_round_trip_seconds(
    baud_rate: int = 9600,
    *,
    source_chars: int = 20,
    query_chars: int = 8,
    response_chars: int = 28,
    framing_bits: int = 10,
    turnaround_s: float = 0.055,
) -> float:
    """Return a practical serial round-trip time estimate for one point."""
    try:
        baud = max(1200.0, float(baud_rate))
    except (TypeError, ValueError):
        baud = 9600.0
    total_chars = (
        max(0, int(source_chars))
        + max(0, int(query_chars))
        + max(0, int(response_chars))
    )
    serial_s = (total_chars * max(1, int(framing_bits))) / baud
    return serial_s + max(0.0, float(turnaround_s))


def minimum_interval_seconds(
    nplc: float,
    line_frequency_hz: float = 50.0,
    overhead_s: float | None = None,
    delay_s: float = 0.0,
    baud_rate: int = 9600,
) -> float:
    aperture_s = max(0.0, float(nplc)) / float(line_frequency_hz)
    serial_s = serial_round_trip_seconds(baud_rate=baud_rate)
    extra_overhead = serial_s if overhead_s is None else max(0.0, float(overhead_s))
    return aperture_s + max(0.0, float(delay_s)) + extra_overhead


def minimum_allowed_interval_seconds(
    nplc: float,
    line_frequency_hz: float = 50.0,
    delay_s: float = 0.0,
) -> float:
    aperture_s = max(0.0, float(nplc)) / float(line_frequency_hz)
    return aperture_s + max(0.0, float(delay_s))


def estimate_point_seconds(
    nplc: float,
    mode: str = "STEP",
    interval_s: float | None = None,
    delay_s: float = 0.0,
    baud_rate: int = 9600,
) -> float:
    base = minimum_interval_seconds(nplc, delay_s=delay_s, baud_rate=baud_rate)
    if mode == SweepKind.CONSTANT_TIME.value and interval_s is not None:
        return max(float(interval_s), base)
    return base


def make_constant_time_values(value: float, duration_s: float, interval_s: float) -> list[float]:
    if not all(math.isfinite(float(item)) for item in (value, duration_s, interval_s)):
        raise ValueError("Constant value, duration, and interval must be finite.")
    if duration_s <= 0:
        raise ValueError("Duration must be positive.")
    if interval_s <= 0:
        raise ValueError("Interval must be positive.")
    count = math.floor(duration_s / interval_s + 1e-12) + 1
    return [float(value)] * max(1, count)


def validate_config(config: SweepConfig) -> None:
    common_values = (
        (config.compliance, "Compliance"),
        (config.nplc, "NPLC"),
        (config.delay_s, "Delay"),
        (config.range_settle_delay_ms, "Range settle delay"),
        (config.discard_after_range_change, "Discard readings after range change"),
        (config.trigger_delay_s, "Trigger delay"),
        (config.digital_filter_count, "Digital filter count"),
    )
    for value, label in common_values:
        if not math.isfinite(float(value)):
            raise ValueError(f"{label} must be finite.")
    if config.fast_acquisition and config.custom_acquisition:
        raise ValueError("Fast and Custom acquisition profiles cannot both be active.")
    if (
        config.fast_acquisition or config.custom_acquisition
    ) and config.sweep_kind is not SweepKind.CONSTANT_TIME:
        raise ValueError("Fast/Custom acquisition profiles are available only for Time sweeps.")
    if config.trigger_delay_s < 0:
        raise ValueError("Trigger delay must be zero or positive.")
    if int(config.digital_filter_count) < 1:
        raise ValueError("Digital filter count must be at least 1.")
    if not config.auto_source_range and not math.isfinite(float(config.source_range)):
        raise ValueError("Fixed source range must be finite when Auto source range is off.")
    if not config.auto_measure_range and not math.isfinite(float(config.measure_range)):
        raise ValueError("Fixed measure range must be finite when Auto measure range is off.")

    if config.sweep_kind is SweepKind.MANUAL_OUTPUT:
        if not math.isfinite(float(config.constant_value)):
            raise ValueError("Manual output value must be finite.")
    elif config.sweep_kind is SweepKind.CONSTANT_TIME:
        if not math.isfinite(float(config.constant_value)):
            raise ValueError("Constant value must be finite.")
        if not config.continuous_time:
            if not math.isfinite(float(config.duration_s)) or config.duration_s <= 0:
                raise ValueError("Duration must be positive and finite.")
        if not config.fast_acquisition:
            if not math.isfinite(float(config.interval_s)) or config.interval_s <= 0:
                raise ValueError("Interval must be positive and finite.")
            if not config.continuous_time:
                source_values_for_config(config)
            min_interval = minimum_allowed_interval_seconds(
                config.nplc, delay_s=config.delay_s
            )
            if config.interval_s < min_interval:
                raise ValueError(
                    f"Interval is too short for NPLC={config.nplc}. "
                    f"Use at least about {min_interval:.3f} s."
                )
    elif config.sweep_kind is SweepKind.ADAPTIVE:
        source_values_for_config(config)
    else:
        source_values_for_config(config)
    if not config.auto_source_range and config.source_range <= 0:
        raise ValueError("Fixed source range must be positive when Auto source range is off.")
    if not config.auto_measure_range and config.measure_range <= 0:
        raise ValueError("Fixed measure range must be positive when Auto measure range is off.")
    if config.compliance <= 0:
        raise ValueError("Compliance must be positive.")
    if not (0.01 <= config.nplc <= 10):
        raise ValueError("NPLC should normally be between 0.01 and 10.")
    if config.delay_s < 0:
        raise ValueError("Delay must be zero or positive.")
    if config.range_settle_delay_ms < 0:
        raise ValueError("Range settle delay must be zero or positive.")
    if config.discard_after_range_change < 0:
        raise ValueError("Discard readings after range change must be zero or positive.")
