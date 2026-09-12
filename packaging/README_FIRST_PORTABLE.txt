HappyMeasure portable Windows build
===================================

Run:
    HappyMeasure.exe

Before real hardware:
    1. Start in Debug/simulator mode and run a short simulator sweep.
    2. Exercise Start/Pause/Resume/STOP and confirm the UI can start another run.
    3. Check CSV export/import and logs.
    4. With no DUT or analog test leads connected, run the built-in Hardware
       Diagnostics communication/output-off check if available for the instrument.
    5. Connect/disconnect the real Keithley with no DUT and verify Output OFF on
       the instrument front panel.
    6. Use the repository hardware preflight/no-DUT smoke tools when validating a
       release from a source checkout.
    7. Test a known resistor/dummy load with conservative source/compliance before
       any real device.

For a first dummy-load sweep:
    - COM port: the detected serial resource.
    - Baud/terminal: match the actual instrument configuration.
    - Sense wiring: 2-wire unless the fixture is intentionally wired for 4-wire.
    - Use conservative source values and compliance appropriate to the resistor.
    - Confirm the expected current (approximately V/R) remains comfortably below
      compliance before starting.

Pause may leave the current source state active; it is not an output-off action.
Use STOP when you need HappyMeasure to request output off, and physically confirm
Output OFF on the instrument front panel after completion, STOP, error, disconnect,
and close during release validation.

Do not move only HappyMeasure.exe out of this folder. The _internal folder and
bundled DLL/resources are part of the portable app.

The bundled HARDWARE_VALIDATION_PROTOCOL.md and HARDWARE_DRY_RUN_GUIDE.md describe
the staged safety gate. Simulator/CI success is not real-hardware verification.

If Windows SmartScreen appears, proceed only when you trust and can verify the
origin of the build; do not bypass a warning merely because the file is named
HappyMeasure.exe.
