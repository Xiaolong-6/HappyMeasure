# Hardware Preflight

HappyMeasure includes a minimal serial preflight for Keithley 2400-family instruments.

## Purpose

The preflight is a safety gate before the first real sweep after installing or updating the app. It verifies that the serial resource is reachable and that an output-off command can be sent.

## What it does

```text
1. Open serial port
2. Query *IDN?
3. Send output OFF
4. Close the port
```

## What it does not do

```text
It does not source voltage.
It does not source current.
It does not run a sweep.
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

## Expected pass output

```text
Safety: this preflight queries *IDN? and sends OUTPUT OFF only; it does not source voltage/current or run a sweep.
Opening serial port COM3 at 9600 baud
*IDN? -> KEITHLEY INSTRUMENTS INC.,MODEL 2400,...
Output OFF command sent successfully
PASS hardware preflight
Output OFF confirmed: True
```

## Expected failure behavior

Failures should print `FAIL hardware preflight`, a readable reason, and a recovery action. They should not produce a raw traceback for ordinary serial/resource failures.

## Manual safety notes

Before real hardware testing:

- Confirm the SMU output wiring is safe.
- Prefer a dummy load or disconnected output for first preflight.
- Confirm the instrument front panel also shows output off after preflight.
- Do not run a real sweep until preflight passes.
