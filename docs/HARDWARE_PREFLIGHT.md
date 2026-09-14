# Hardware Preflight

HappyMeasure includes a minimal serial preflight for Keithley 2400-family instruments.

## Purpose

The preflight verifies serial communication, forces source output off, and requires the instrument to report that output is actually off before any real measurement is attempted.

## GUI Detect COM behavior

The Hardware-page **Detect COM** button is deliberately passive:

1. enumerate COM ports reported by Windows/pyserial;
2. update the COM choices;
3. if only one port is present, select it;
4. send **no SCPI command**;
5. do **not** guess or scan baud rates.

The operator selects the instrument baud rate. Model identification happens during normal Connect using that selected COM + baud.

This design avoids repeatedly sending malformed serial data at guessed baud rates, which can make a Keithley report communication/parser errors such as `-101 Invalid character`.

## CLI automatic COM discovery

The command-line preflight may discover which detected COM port hosts a supported Keithley, but it uses **one operator-selected baud only**. It never scans alternate baud rates.

```text
1. Enumerate detected COM ports
2. At the selected --baud, send one short *IDN? probe per candidate port
3. Accept only a supported Keithley 2400-family identity
4. Never retry using a different baud
```

Wrong baud/framing can still produce an instrument communication error, so explicit COM + baud is preferred when those settings are already known.

## Preflight sequence

After the port is selected/discovered:

```text
1. Open serial port
2. Send OUTPUT OFF
3. Query :OUTP?
4. Require OFF/0
5. Query *IDN?
6. Send OUTPUT OFF again during cleanup
7. Close port
```

The preflight does not source voltage/current, issue `READ?`, run a sweep, or reset/configure the SMU.

## Commands

Explicit known settings are the clearest form:

```powershell
.\.venv\Scripts\python.exe -m happymeasure.hardware_preflight COM3 --baud 57600
```

Automatic COM discovery at one selected baud:

```powershell
.\.venv\Scripts\python.exe -m happymeasure.hardware_preflight --auto --baud 57600
```

Omitting the port also selects automatic COM discovery at the supplied/default baud.

Legacy compatibility namespace remains available:

```powershell
.\.venv\Scripts\python.exe -m keith_ivt.hardware_preflight COM3 --baud 57600
```

## Expected pass

A pass requires both a supported identity and verified output-off state, for example:

```text
Opening serial port COM3 at 57600 baud
Output OFF verified by :OUTP? -> 0
*IDN? -> KEITHLEY INSTRUMENTS INC.,MODEL 2401,...
PASS hardware preflight
Output OFF confirmed: True
```

Do not store the physical instrument serial number in repository documentation or tests.

## Failure behavior

A failure is not evidence that output is physically off. Use the instrument front-panel OUTPUT control to verify a safe state before changing wiring or touching a DUT.

If communication fails, verify the Windows COM port and the instrument's own RS-232 settings (baud, data bits/parity and terminator as applicable) rather than repeatedly probing alternate baud rates.
