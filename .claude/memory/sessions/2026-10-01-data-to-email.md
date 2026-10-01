# 2026-10-01 · data-to-email

**Goal:** Implement epic #273 (figures, charts and pictures from data without hand-work).

## What happened
- #282 merged as PR #286 first; the branch fast-forwarded to `main`.
- #274: `Card.from_number` (inherited by `KpiItem`) formats a figure and its change and tones by
  the change's sign, flipped by `good="down"`.
- #275: `pyhermes.data.chart_style()` returns a `ChartStyle` (a `dict` of matplotlib rc, with
  `positive`, `negative`, `series` attributes); `RC_TOKENS` maps each setting to its token.
- #276: `EmailImage.__post_init__` warns when the pixel width exceeds
  `Config.oversize_image_ratio` (4.5) times the display width.

## Gotchas & dead ends
- `plt.rc_context` refuses unknown keys, so the sign colours ride as attributes on a dict subclass.
- At the issue's ratio of 3 the gallery warned: equations are 4x by `DEFAULT_MATH_SCALE`, and
  print pictures 3.1x for 300 dpi. 4.5 clears both and still catches a 13x phone photo.
- `formats.number` defaults to no decimals and writes zero unsigned; three test expectations
  were wrong before the code was.
- The manual runs each charts block in its own scope, so a block needs its own imports.
