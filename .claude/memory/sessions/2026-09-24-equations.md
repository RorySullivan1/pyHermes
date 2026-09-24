# 2026-09-24 · equations

**Goal:** Close epic #221 — equations from LaTeX, a MathBlock that survives every medium.

## What happened
- One commit per child on `claude/integrate-claude-assets-pyhermes-d4spzb`, restarted from `main`
  after PR #234 merged.
- #229 `MathBlock` (bytes or an alt-is-source `EmailImage`; `text()` prints `$source$`); in
  `kitchen_sink` on `solid_png`.
- #230 `svc/math` + `[math]`: `render_math` → `RenderedMath`, `MathSyntaxError`; CI `data` and `pdf`
  jobs install it.
- #231 `math_block` / `image_from_math` painted in `theme.text.primary` at `size.type.body`;
  defaults `cm` and scale 4.
- #232 `lines=` shim, `a4_equations` (engineered at a sheet foot, 8 lead-in paragraphs), 20-equation
  wire size 280 KB, real-render screenshots at 1000/375/320.
- #233 `math.md`, router/README/repo map, the factsheet's Sharpe ratio (`\dfrac`, growth chart 2.1→1.2 in).

## Gotchas
- `EmailImage` refuses an alt-less image, so the issue's `MathBlock(EmailImage.attached(png))` could
  not construct: the component takes bytes instead.
- WeasyPrint resolves `margin:auto` against `width:100%` before `max-width`, so block images sat at the
  left edge: the equation image is `inline-block` in a zero-leading line box. `ImageBlock` may share it.
- A float footnote that does not fit moves to the next sheet, away from its marker, before the sheet
  count moves: check the text per sheet, not only the count.
- `\frac` at the dense 11 px body is illegible; `\dfrac` is supported.
- `tests/test_examples.py` now skips on either extra's `BackendMissingError`.

## Open threads
- An Outlook render of an equation image, and dark-mode legibility of a transparent PNG, are owed.
- CI's pixel sizes against the local ones (`MEASURED` in `test_math.py`, ±4 px).
