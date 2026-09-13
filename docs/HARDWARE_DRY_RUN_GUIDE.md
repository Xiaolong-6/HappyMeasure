# Hardware Dry-Run Guide

Target: first safe HappyMeasure check with a real Keithley 2400/2450-style source meter.

## Safety principle

Do not run a sweep first. Confirm communication, force output off, and verify the reported output state before any sourced measurement.

## Step 0 — physical setup

1. Put the instrument in a known idle state.
2. Keep the DUT and analog test leads disconnected for the first communication test.
3. Confirm the front/rear terminal selection on the instrument matches the intended UI setting.
4. Confirm the serial cable/adapter is visible in Windows Device Manager.
5. Note the COM port and baud rate. Keithley 2400 units commonly use 9600 baud, but verify the instrument menu.

## Step 1 — source/simulator gate

Before real hardware work, the automated source gate should be green. A local core check is:

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q tests/common tests/happymeasure
```

Map Reconstruction has a separate Qt gate and is not required merely to perform the no-DUT hardware dry run. For the complete release validation environment, follow `RELEASE_CHECKLIST.md`.

## Step 2 — hardware preflight

Edit `tools\hardware\Real_Hardware_Preflight.bat` if your COM port is not `COM3`, then run it.

Equivalent command:

```powershell
python -m happymeasure.hardware_preflight COM3 --baud 9600
```

The compatibility namespace remains supported:

```powershell
python -m keith_ivt.hardware_preflight COM3 --baud 9600
```

Expected behavior includes:

```text
Opening serial port COM3 at 9600 baud
Output OFF verified by :OUTP? -> 0
*IDN? -> KEITHLEY INSTRUMENTS INC.,MODEL 2400,...
PASS hardware preflight
Output OFF confirmed: True
```

This path sends only the communication/output-off commands documented in `HARDWARE_PREFLIGHT.md`; it does not source voltage/current, issue `READ?`, or run a sweep.

If preflight does not pass, do not proceed to a sweep. Confirm physical output-off on the instrument front panel before touching wiring or a DUT.

## Step 3 — UI connection check

1. Start HappyMeasure.
2. Turn Debug off.
3. Select the detected COM port.
4. Click Connect.
5. Confirm the detected model appears under Hardware and in the status bar.
6. Click Disconnect and confirm the status returns to disconnected.
7. Confirm the instrument output is physically OFF.

The built-in **Hardware Diagnostics** may also be used for its explicit no-DUT/output-off communication check. It is not a substitute for the staged release protocol.

## Step 4 — first sourced measurement

Use a resistor or other known passive dummy load before a real DUT.

Recommended conservative starting point:

```text
Mode: VOLTAGE source
Sweep: STEP
Start: 0 V
Stop: 0.1 V
Step: 0.01 V
Compliance: 1e-4 A or safer for your load
NPLC: 1
Auto source range: on
Auto measure range: on
Terminal: match the instrument
Sense: 2-wire unless using a real Kelvin fixture
```

Before pressing Start, calculate the expected current from the known load and confirm it is comfortably below compliance.

## STOP / error / close expectation

The HappyMeasure **STOP** control is cooperative. It requests sweep termination and output-off cleanup, but it cannot interrupt a serial transaction already in progress. Active instrument I/O must return before software cleanup can complete.

For an immediate physical hazard response, use the instrument front-panel OUTPUT OFF control rather than relying on the desktop STOP button.

After normal completion, STOP, Abort/error, disconnect, and closing the application after an active run, visually confirm physical/front-panel `OUTPUT OFF` during the hardware validation stage.

A real-driver `OUTPUT OFF` write failure is surfaced as an error; secondary cleanup guards may make another best-effort attempt, but software must not report a hardware-safe pass when output-off cannot be verified.

## Record results

After the test, save the relevant logs, exported CSV, UI status screenshot, and instrument model/firmware from `*IDN?` as described in `HARDWARE_VALIDATION_PROTOCOL.md`.
