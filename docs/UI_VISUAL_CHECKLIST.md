# UI Visual Smoke Checklist

Run this manually on Windows before handing the release candidate to another user. This checklist is visual/responsive only; functional smoke belongs in `MANUAL_SMOKE_TESTS.md`.

1. Launch `Run_HappyMeasure.bat`; confirm the default page and bottom operator/status areas render without overlap.
2. Switch all navigation pages; the side rail remains visible and the page content does not retain widgets from the previous page.
3. Test a short/low-height window and common Windows scaling. Settings/Sweep content must remain reachable by scrolling.
4. Enable developer tools, run UI Diagnostics, return to Settings, and confirm both UI/Hardware Diagnostics actions remain reachable.
5. Change UI scale through representative small/default/large values and confirm labels, entries, buttons and scrollbars do not overlap.
6. In Constant Time, expand Advanced Acquisition. Boolean controls must be visually paired with their own labels; dependent controls such as Filter count must not look active when disabled.
7. Resize the plot area narrowly; view/global controls should wrap or remain reachable rather than disappear offscreen.
8. Run a long simulator Time trace. The live line should update smoothly without obvious full-canvas flashing or rapidly jumping axes/ticks.
9. With Time `Last N`, confirm the live plot shows the rolling window; after completion confirm the stored trace can display the full run and Auto markers do not create a dense marker cloud.
10. Right-click a Time plot and confirm Time display settings are in the plot context, not the Traces-column gear.
11. Confirm the Traces gear controls trace-table columns only.
12. Open `Log`; controls remain at the top and log text fills the available panel with its own scrollbar.
13. Launch Map Reconstruction; confirm maximized startup, usable restored size, visible three-stage workflow, and reachable Map Analysis color controls including **Flip color**.
14. Load a second Map CSV after a reconstruction and visually confirm the workflow returns to Signal Preparation without stale old map/QC content.

For automated gates, follow `RELEASE_CHECKLIST.md`; do not treat this visual checklist as a substitute for CI or hardware validation.
