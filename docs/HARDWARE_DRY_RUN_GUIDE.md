# Hardware Dry-Run Guide

Target: first safe HappyMeasure check with a real Keithley 2400/2450-style source meter.

## Safety principle

Do not run a sweep first. Confirm communication and force output off first.

## Step 0 — physical setup

1. Put the instrument in a known idle state.
2. Remove or protect sensitive DUTs for the first communication test.
3. Confirm the front/rear terminal selection on the instrument matches the UI setting.
4. Confirm the serial cable/adapter is visible in Windows Device Manager.
5. Note the COM port and baud rate. Keithley 2400 units commonly use 9600 baud, but verify the instrument menu.

## Step 1 — simulator gate

```powershell
python tests/run_full_validation.py
```

Do not continue if this fails.

## Step 2 — hardware preflight

Edit `tools\hardware\Real_Hardware_Preflight.bat` if your COM port is not `COM3`, then run it.

Equivalent command:

```powershell
python -m keith_ivt.hardware_preflight COM3 --baud 9600
```

Expected behavior:

```text
Opening serial port COM3 at 9600 baud
*IDN? -> KEITHLEY INSTRUMENTS INC.,MODEL 2400,...
Output OFF command sent successfully
PASS hardware preflight
```

This path sends only:

```text
*IDN?
:OUTP OFF
```

It does not source voltage or current.

## Step 3 — UI connection check

1. Start HappyMeasure.
2. Turn Debug off.
3. Select the detected COM port.
4. Click Connect.
5. Confirm the detected model appears under Hardware and in the status bar.
6. Click Disconnect and confirm the status returns to disconnected.

## Step 4 — first real sweep recommendation

Use a resistor or dummy load first.

Recommended starting point:

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

Watch the instrument output indicator. Press EMERGENCY STOP if anything looks wrong.

## Stop/Abort expectation

The alpha path requests stop from the UI thread and the worker runner sends output off through the instrument context manager. The new serial safety layer retries transient serial failures and uses a best-effort output-off guard, but real hardware output-off must still be visually confirmed on the instrument.

## Record results

After the test, save:

```text
logs/console_last_run.log
logs/error.log
logs/log.txt
exported CSV
screenshot of UI status bar
instrument model/firmware from *IDN?
```
