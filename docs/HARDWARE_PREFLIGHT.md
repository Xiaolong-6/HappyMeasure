# Hardware Preflight

HappyMeasure includes a minimal serial preflight for Keithley 2400-family instruments.

## Purpose

The preflight is a safety gate before the first real sweep after installing or updating the app. It verifies that the serial resource is reachable, forces source output off, and requires the instrument to report that output is actually off.

## What it does

```text
1. Open serial port
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

## Command

Public namespace:

```bat
python -m happymeasure.hardware_preflight COM3 --baud 9600
```

Legacy compatibility namespace:

```bat
python -m keith_ivt.hardware_preflight COM3 --baud 9600
```

## Expected pass behavior

A successful run logs the equivalent of:

```text
Opening serial port COM3 at 9600 baud
Output OFF verified by :OUTP? -> 0
*IDN? -> KEITHLEY INSTRUMENTS INC.,MODEL 2400,...
PASS hardware preflight
Output OFF confirmed: True
```

Exact wrapper/CLI formatting may add the initial safety notice, but a pass requires `output_off_confirmed=True` from the verified `:OUTP?` state.

## Expected failure behavior

The preflight must fail if:

- the serial port cannot be opened;
- `OUTPUT OFF` cannot be sent;
- `:OUTP?` fails;
- `:OUTP?` reports a non-off state; or
- ordinary serial/resource operations fail.

A failed preflight is **not** evidence that output is physically off. Use the instrument front panel to force/verify output off before touching a DUT or changing wiring.

## Manual safety notes

Before real hardware testing:

- Keep the DUT and analog test leads disconnected for the first preflight.
- Confirm the serial port and baud rate against the instrument menu.
- Confirm the instrument front panel also shows output off after preflight.
- Do not run a real sweep until preflight passes.
- If immediate physical output-off is required, use the instrument front-panel control; software STOP cannot interrupt a serial transaction already in progress.
