# HappyMeasure UI Style Guide — Core Flat Lab

HappyMeasure uses a **Core Flat + Nordic Lab** style. The UI should feel like a clean instrument workspace: quiet navigation, clear controls, low-saturation status colors, and no decorative clutter.

## Navigation

- Use a push-side rail, not a hidden drawer or permanent tab bar.
- The rail reserves column 0 and the workspace uses column 1.
- Clicking a rail button switches the page; the rail does not auto-hide on outside clicks.
- Active rail button uses a flat selected background that visually belongs to the page content.
- Rebuilt/scrollable pages must refresh their scroll region so controls remain reachable on short Windows viewports and larger UI scales.

## Color and surfaces

- Main background: very light cool gray in light mode; charcoal gray in dark mode.
- Content cards: flat white / dark card, thin border, no heavy shadow.
- Accent: low-saturation blue-green.
- Dangerous action: muted red fill, not bright Windows red.
- Disabled state: low-contrast gray, but text must remain readable.

## Controls

- Buttons must look clickable: flat surface + thin border or filled status color.
- Avoid floating text-only buttons unless they are inside a context menu.
- Remove native ugly focus rings where possible; use consistent flat focus/hover state.
- Boolean settings should visually pair the checkbox with its own label; avoid a detached label in one column and an unlabeled checkbox far away.
- Dependent controls must look disabled when their parent feature is off.
- Plot-specific controls belong in the plot right-click menu, not the global toolbar or the Traces-column gear.

## Plot controls

The top toolbar keeps only global/view-selection actions. View-specific settings stay in the plot context menu.

Typical plot-context actions include:

```text
Autoscale this view
Set X range
Set Y range
Number format
X unit
Y unit
Plot style
Time plot settings...   (Time view)
```

Time plot settings own display-only policy such as marker `Auto/On/Off`, live `All data/Last N`, and refresh cadence. They must not be placed in the Traces-table column gear and must never imply truncation of stored measurement data.

The Traces gear is reserved for trace-table column visibility/organization. Trace management/export actions belong to the trace list/context, not plot view settings.

## Naming

- **Save Plot** means image export.
- **Export Data** means measurement CSV export.
- **Import Data** means CSV trace import.
- **Clear Traces** means removing traces from the current workspace.

## Layout contract

- Push-side rail for navigation, not a hidden drawer.
- Left content pane configures the current workflow; it should not duplicate global execution buttons.
- The bottom operator bar is the only Start/Pause/STOP surface.
- Wide windows use Config | Plot | Traces. Narrow windows stack/reflow without making required actions unreachable.
- Buttons remain visually identifiable: filled green for Start, filled red for STOP, bordered/soft cards for secondary actions.
- Advanced Acquisition groups should stay compact and responsive rather than using fixed widths that clip under Windows scaling.
