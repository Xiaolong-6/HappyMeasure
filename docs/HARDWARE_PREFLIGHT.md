# Hardware Preflight

HappyMeasure includes a minimal serial preflight for Keithley 2400-family instruments.

## Purpose

The preflight is a safety gate before the first real sweep after installing or updating the app. It verifies that the serial resource is reachable, forces source output off, and requires the instrument to report that output is actually off.

HappyMeasure can also auto-detect the COM port and baud rate used by a supported Keithley 2400-family instrument. Discovery is deliberately narrow: it sends `*IDN?` only and does not source, measure, reset, or change instrument configuration.

## What it does

With automatic discovery enabled (or when no port is supplied):

```text
1. Enumerate Windows serial ports
2. Try the current/preferred COM and baud first
3. Probe HappyMeasure-supported baud rates using *IDN? only
4. Accept only a supported Keithley 2400-family identity
```

The actual preflight then performs:

```text
1. Open the detected/selected serial port
2. Send OUTPUT OFF
3. Query :OUTP?
4. Require an OFF/0 state
5. Query *IDN?
6. Send OUTPUT OFF again during cleanup
7. Close the port
```

The order is deliberate: the preflight forces and verifies output-off before identity work.

## What it does not do

```text
It does not source voltage.
It does not source current.
It does not issue READ?.
It does not run a sweep.
It does not reset/configure the SMU.
It does not modify user presets.
```

## Commands

Recommended automatic form:

```bat
python -m happymeasure.hardware_preflight
```

Equivalent explicit automatic form:

```bat
python -m happymeasure.hardware_preflight --auto
```

Manual override remains supported:

```bat
python -m happymeasure.hardware_preflight COM3 --baud 9600
```

Legacy compatibility namespace remains supported as well:

```bat
python -m keith_ivt.hardware_preflight COM3 --baud 9600
```

HappyMeasure currently auto-scans the baud rates exposed by the acquisition UI: `9600`, `19200`, `38400`, and `57600`.

## GUI connection behavior

For a real-hardware connection, the existing **Connect** action now performs the same lightweight discovery first. It tries the currently selected COM/baud combination first, then other detected COM ports and supported baud rates. When a supported Keithley is found, HappyMeasure updates the COM and baud fields and continues through the normal connection/identity/beep path.

If no supported instrument is found, manual connection behavior remains available using the selected COM/baud settings.

## Expected pass behavior

A successful automatic run logs the equivalent of:

```text
Auto-detected Keithley 2401 on COM3 at 57600 baud
Opening serial port COM3 at 57600 baud
Output OFF verified by :OUTP? -> 0
*IDN? -> KEITHLEY INSTRUMENTS INC.,MODEL 2401,...
PASS hardware preflight
Output OFF confirmed: True
```

Exact wrapper/CLI formatting may add the initial safety notice, but a pass requires `output_off_confirmed=True` from the verified `:OUTP?` state.

## Expected failure behavior

The preflight must fail if:

- automatic discovery cannot find a supported instrument and no manual settings are used;
- the serial port cannot be opened;
- `OUTPUT OFF` cannot be sent;
- `:OUTP?` fails;
- `:OUTP?` reports a non-off state; or
- ordinary serial/resource operations fail.

A failed preflight is **not** evidence that output is physically off. Use the instrument front panel to force/verify output off before touching a DUT or changing wiring.

## Manual safety notes

Before real hardware testing:

- Keep the DUT and analog test leads disconnected for the first preflight.
- Confirm the instrument front panel also shows output off after preflight.
- If automatic discovery fails, confirm COM and baud against the instrument menu and retry manually.
- Do not run a real sweep until preflight passes.
- If immediate physical output-off is required, use the instrument front-panel control; software STOP cannot interrupt a serial transaction already in progress.
