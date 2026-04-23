# Developer Notes: Matplotlib in `Generate_combined_graph.py`

This document explains the Matplotlib patterns used in `Generate_combined_graph.py` and why they keep the live window responsive.

## Interactive mode and window lifecycle

- `plt.ion()`: Enables Matplotlib "interactive" mode so figures can update without blocking the Python process.
- `plt.show(block=False)`: Creates/displays the window but does not block the script. The script continues into the live loop.

## The event loop: why `plt.pause(...)` matters

In GUI backends (Qt, Tk, etc.), the window stays responsive only if the GUI event loop is serviced regularly.

- `plt.pause(seconds)`:
  - Processes GUI events (mouse/keyboard, pan/zoom, redraw requests).
  - Sleeps for roughly `seconds`.
  - Returns to your Python code.

In this project, a **longer** `plt.pause(--refresh-sec)` can improve perceived responsiveness because it reduces how often Python does expensive update work (less redraw churn).

## Fast live updates: reuse artists (avoid `ax.clear()` + re-plot)

The main performance win is reusing existing plot objects:

- `ax.plot([], [])` returns a `Line2D` artist.
- `line.set_data(x, y)` updates the artist in-place.

Why this matters:
- `ax.clear()` throws away artists, legends, locators, etc., forcing Matplotlib to rebuild a lot of state every refresh.
- Re-creating legends (`ax.legend`) and recomputing layouts (`fig.tight_layout`) on every refresh is expensive.

This script:
- Builds all lines once in `build_figure_and_lines(...)`
- Updates data only in `update_lines(...)`
- Runs `fig.tight_layout(...)` only when the figure is rebuilt (plot layout changes)

## Scheduling redraws (and keeping them cheap)

- `fig.canvas.draw_idle()` schedules a redraw "soon" rather than forcing an immediate full draw.
- `fig.canvas.flush_events()` pushes GUI events through (useful with some backends).

In practice, `draw_idle()` + `plt.pause(...)` is a good combination for live plots:
- `draw_idle()` requests the redraw
- `plt.pause(...)` gives the backend time to actually do it and handle input

## Axes sharing and time formatting

- `plt.subplots(..., sharex=True)` makes all subplots share the same x-axis (time), which improves consistency and reduces duplicated formatter work.
- `mdates.DateFormatter("%I:%M:%S")` formats timestamps for readability.
- `ticker.MaxNLocator(...)` limits the number of ticks to keep rendering lightweight.

## Autoscaling strategy used here

For each subplot, `update_lines(...)` computes simple y-limits from the current displayed data and calls `ax.set_ylim(...)`.

Why not call `ax.relim()` / `ax.autoscale_view()` every time?
- They can be slower and do more work than necessary for bounded, regularly-updated time series.

## Background parsing vs main-thread plotting

Matplotlib is not thread-safe for GUI operations. This script keeps a strict split:

- Background thread (`ThreadPoolExecutor`):
  - Reads files from disk
  - Parses JSON/regex
  - Produces DataFrames
- Main thread:
  - Calls `plt.pause(...)`
  - Updates `Line2D` objects (`set_data`)
  - Rebuilds the figure if plot layout changes

## Keeping work bounded as logs grow

Two layers limit per-refresh cost:

1) Tail reading: `read_last_lines(path, --web-tail-lines/--teraterm-tail-lines)` parses only the end of each file.
2) Display windowing: `--window-min` and `--max-points` cap the data passed into Matplotlib.

## Common tuning knobs

Examples:

- Faster updates with less history:
  - `python Generate_combined_graph.py --refresh-sec 2 --window-min 10 --max-points 2000`
- One-time “wide window” run (slower but still bounded):
  - `python Generate_combined_graph.py --window-min 360 --max-points 50000 --web-tail-lines 50000 --teraterm-tail-lines 200000`

