HappyMeasure portable Windows build
===================================

Run:
    HappyMeasure.exe

Recommended first-run checks before real hardware:
    1. Start in Debug/simulator mode.
    2. Run diode/resistor/open/short simulator sweeps.
    3. Check CSV export and logs.
    4. Connect to the real Keithley without DUT attached.
    5. Verify Output remains OFF after connect/disconnect.
    6. Run hardware preflight from the source tree if available.
    7. Test a resistor dummy load before any real device.

For front-panel dummy resistor checks, start conservatively:
    - COM port: the detected USB serial port, often COM3.
    - Terminal: FRONT.
    - Sense wiring: 2-wire unless the fixture is wired for 4-wire.
    - Mode: voltage source, current measure.
    - Compliance: 100 nA for high-value dummy resistors.
    - Sweep: -1 V to +1 V, small step such as 0.25 V.

Pause keeps the current source state active. It does not turn output off.
Use STOP when you want the app to request output off, and confirm Output OFF on
the instrument front panel.

Do not move only HappyMeasure.exe out of this folder. The _internal folder and
bundled DLL/resources are part of the portable app.

If Windows SmartScreen appears, choose More info -> Run anyway only if this build
was created by you from the source package.
