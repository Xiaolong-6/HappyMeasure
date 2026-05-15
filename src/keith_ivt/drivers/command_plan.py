from __future__ import annotations

from keith_ivt.models import SenseMode, SweepConfig


def build_keithley2400_sweep_command_plan(config: SweepConfig, *, include_output: bool = True) -> list[str]:
    """Return the conservative SCPI plan expected for a Keithley 2400 sweep.

    This is intentionally side-effect free.  It is used before hardware bring-up
    to compare expected command intent against mock-serial command recordings.
    """
    src = config.source_scpi
    meas = config.measure_scpi
    commands: list[str] = [
        "*RST",
        ":OUTP OFF",
        f":ROUT:TERM {config.terminal.value}",
        ":SYST:RSEN ON" if config.sense_mode is SenseMode.FOUR_WIRE else ":SYST:RSEN OFF",
        f":SOUR:FUNC {src}",
        f":SENS:FUNC '{meas}'",
        f":SENS:{meas}:PROT {config.compliance:.12g}",
        f":SENS:{meas}:NPLC {config.nplc:.12g}",
    ]
    if config.auto_source_range:
        commands.append(f":SOUR:{src}:RANG:AUTO ON")
    else:
        commands.extend([f":SOUR:{src}:RANG:AUTO OFF", f":SOUR:{src}:RANG {config.source_range:.12g}"])
    if config.auto_measure_range:
        commands.append(f":SENS:{meas}:RANG:AUTO ON")
    else:
        commands.extend([f":SENS:{meas}:RANG:AUTO OFF", f":SENS:{meas}:RANG {config.measure_range:.12g}"])
    commands.append(f":FORM:ELEM {src},{meas}")
    if include_output:
        commands.append(":OUTP ON")
        commands.append(":OUTP OFF")
    return commands
