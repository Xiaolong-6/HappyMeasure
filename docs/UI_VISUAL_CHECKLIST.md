# UI visual smoke checklist

Run this manually on Windows before handing the package to another agent or user.

1. Launch `Run_HappyMeasure.bat`.
2. Confirm the default page is `Hardware`.
3. Confirm the page header contains only the hamburger button and page title.
4. Confirm connection state appears only in the bottom status bar.
5. Confirm the status bar shows red when disconnected and green when connected/debug-ready.
6. Open and close the left drawer; it should slide in/out and not cover the page title permanently.
7. Resize the window narrowly; plot view controls should wrap rather than disappear.
8. Change UI scale to 8 pt, 12 pt, and 18 pt; confirm no major overlap.
9. Run a simulator sweep; during measurement, only the live plot should show and the trace list should be hidden.
10. After completion, confirm stored traces and the trace list return.
11. Right-click the plot; confirm it offers plot image/view/range/style actions only.
12. Right-click the trace list; confirm CSV export/import and trace-management actions are there.
13. Open `Log`; confirm buttons are on the first row and the log text fills the remaining panel.
14. Validate with `tools\validation\Run_Full_Validation.bat`.
