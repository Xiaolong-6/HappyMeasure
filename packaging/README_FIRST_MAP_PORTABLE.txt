Map Reconstruction portable Windows build
==========================================

Map Reconstruction is the companion post-processing tool to HappyMeasure.
This standalone package runs on its own:

Run:
    MapReconstruction.exe

You do NOT need:
    - HappyMeasure.exe next to it;
    - a Python installation;
    - a Keithley instrument.

It loads HappyMeasure single-v2 CSV exports and self-contained .hmmap
projects for offline analysis:

    Signal Preparation -> Reconstruction -> Map Analysis

Derived maps are display/analysis products; the embedded raw source data in
a .hmmap archive stays authoritative. See the bundled MAP_PROJECT_FORMAT.md
for the project contract.

Do not move only MapReconstruction.exe out of this folder. The _internal
folder and bundled DLL/resources are part of the portable app.

If Windows SmartScreen appears, proceed only when you trust and can verify
the origin of the build; do not bypass a warning merely because of the
file name.
