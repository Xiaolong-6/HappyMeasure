from __future__ import annotations

from dataclasses import dataclass

from keith_ivt.models import SweepConfig, SweepKind

FAST_NPLC = 0.1
FAST_TRIGGER_DELAY_S = 0.0
FAST_BENCHMARK_NOTE = (
    "Keithley 2401 / RS-232 57600 benchmark: host-driven fast path was typically "
    "about 14-16 ms/sample; actual rate depends on instrument, transport, adapter, and PC."
)


@dataclass(frozen=True, slots=True)
class TimeAcquisitionSettings:
    """Resolved Constant-Time acquisition behavior used by runner and driver.

    ``apply_instrument_overrides`` is False for the historical Standard path so
    existing non-fast measurements keep the instrument's reset/default behavior.
    Fast and Custom profiles make every listed acquisition knob explicit.
    """

    nplc: float
    software_delay_s: float
    as_fast_as_possible: bool
    apply_instrument_overrides: bool
    zero_refresh_before_run: bool
    autozero_during_run: bool
    digital_filter: bool
    digital_filter_count: int
    concurrent_measurement: bool
    display_during_run: bool
    measurement_only_read: bool
    range_telemetry: bool
    source_write_each_sample: bool
    trigger_delay_s: float


def fast_profiles_available(
    *, connected: bool, simulator: bool, supports_fast_acquisition: bool
) -> bool:
    """Return whether Fast/Custom profiles may be offered for a connection.

    Disconnected sessions keep the existing options (no run is possible
    anyway); connected real instruments must advertise validated Fast support.
    """

    if not connected or simulator:
        return True
    return bool(supports_fast_acquisition)


def resolve_time_acquisition(config: SweepConfig) -> TimeAcquisitionSettings:
    """Resolve Standard/Fast/Custom Constant-Time settings without touching UI state."""

    if config.sweep_kind is not SweepKind.CONSTANT_TIME:
        return TimeAcquisitionSettings(
            nplc=float(config.nplc),
            software_delay_s=float(config.delay_s),
            as_fast_as_possible=False,
            apply_instrument_overrides=False,
            zero_refresh_before_run=False,
            autozero_during_run=True,
            digital_filter=False,
            digital_filter_count=2,
            concurrent_measurement=True,
            display_during_run=True,
            measurement_only_read=False,
            range_telemetry=True,
            source_write_each_sample=False,
            trigger_delay_s=0.0,
        )

    if bool(config.fast_acquisition):
        return TimeAcquisitionSettings(
            nplc=FAST_NPLC,
            software_delay_s=0.0,
            as_fast_as_possible=True,
            apply_instrument_overrides=True,
            zero_refresh_before_run=True,
            autozero_during_run=False,
            digital_filter=False,
            digital_filter_count=2,
            concurrent_measurement=False,
            display_during_run=True,
            measurement_only_read=True,
            range_telemetry=False,
            source_write_each_sample=False,
            trigger_delay_s=FAST_TRIGGER_DELAY_S,
        )

    if bool(config.custom_acquisition):
        return TimeAcquisitionSettings(
            nplc=float(config.nplc),
            software_delay_s=float(config.delay_s),
            as_fast_as_possible=False,
            apply_instrument_overrides=True,
            zero_refresh_before_run=bool(config.zero_refresh_before_run),
            autozero_during_run=bool(config.autozero_during_run),
            digital_filter=bool(config.digital_filter),
            digital_filter_count=int(config.digital_filter_count),
            concurrent_measurement=bool(config.concurrent_measurement),
            display_during_run=bool(config.display_during_run),
            measurement_only_read=bool(config.measurement_only_read),
            range_telemetry=bool(config.range_telemetry),
            source_write_each_sample=bool(config.source_write_each_sample),
            trigger_delay_s=float(config.trigger_delay_s),
        )

    # Standard intentionally preserves the historical device configuration.
    return TimeAcquisitionSettings(
        nplc=float(config.nplc),
        software_delay_s=float(config.delay_s),
        as_fast_as_possible=False,
        apply_instrument_overrides=False,
        zero_refresh_before_run=False,
        autozero_during_run=True,
        digital_filter=False,
        digital_filter_count=2,
        concurrent_measurement=True,
        display_during_run=True,
        measurement_only_read=False,
        range_telemetry=True,
        source_write_each_sample=False,
        trigger_delay_s=0.0,
    )
