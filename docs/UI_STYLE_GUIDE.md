# HappyMeasure UI Style Guide — Core Flat Lab

HappyMeasure uses a **Core Flat + Nordic Lab** style. The UI should feel like a clean instrument workspace: quiet navigation, clear controls, low-saturation status colors, and no decorative clutter.

## Navigation

- Use a hidden left drawer, not a permanent tab rail.
- The current page title bar starts with a hamburger button (`☰`) followed by the page title.
- Clicking the hamburger opens the drawer from the left.
- Selecting a drawer item switches the page and closes the drawer.
- `Esc` or clicking outside the drawer closes it.
- Active drawer item uses a flat selected background that visually belongs to the page content.

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
- Plot-specific controls belong in the plot right-click menu, not the global toolbar.

## Plot controls

Top toolbar keeps only global actions:

```text
Views: Linear / Log / V/I / dV/dI / Time
Actions: Layout / Autoscale / Fullscreen / Save Plot / Export Data / Import Data / Clear Traces
```

Per-view actions stay in the plot context menu:

```text
Set X range
Set Y range
Autoscale this view
Number format
X unit
Y unit
Plot style
```

## Naming

- **Save Plot** means image export.
- **Export Data** means measurement CSV export.
- **Import Data** means CSV trace import.
- **Clear Traces** means removing traces from the current workspace.


## 0.2.4 layout lock

The accepted product shell is Core Flat / clean lab:

- Hidden left drawer opened by the hamburger in the page header.
- Left content pane configures the current workflow; it should not duplicate global execution buttons.
- The bottom operator bar is the only Start/Pause/Emergency Stop surface.
- Wide windows use Config | Plot | Traces. Narrow windows stack Traces below Plot automatically.
- View-specific plot settings live in the plot right-click menu, not in the top toolbar.
- Buttons must remain visually identifiable: filled green for Start, filled red for Emergency Stop, bordered/soft cards for secondary actions.
