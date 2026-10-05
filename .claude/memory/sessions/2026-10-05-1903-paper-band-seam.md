# 2026-10-05 19:03 · paper-band-seam

**Goal:** Remove the 1px seam under a dark split's left column on paper

## What happened
- Root cause is CSS paint order, not geometry: WeasyPrint's layout boxes put the band and the
  tallest column's foot at the same fractional y (236.56). A column is an `inline-table`, painted
  in the inline phase after every block background, so its own fill covered the half-pixel row
  the next section's cell owns. Only the tallest column reaches the edge.
- Two forms: a dark split's fill hangs 1px below the band (`a4_labelled_layout`, the reported
  case — it is a *dark* tongue, not a light line); and the mirror, a plain split's white fill
  notching the top of a following dark band (`a4_organised_layout`, live on `main`).
- Fix: `columns.html` emits the column's `background-color` only `{% if not medium.paged %}`;
  the band's cell already paints the ground. Owner chose this broad scope over "only when
  `background_color` is set", which would have left the mirror notch.
- 8 goldens moved (7 paged + `pitch_16_9`), every line only that declaration (script-checked).
  Re-rastering all 35 sheets before/after: exactly two pixel rows differ, the two defects.
- `TestABandsEdgeIsStraightOnPaper` in `tests/test_surfaces.py`: markup check (dev) + two raster
  checks (`[pdf]`+`[qa]`), perturbed against the old template and seen to fail.
- Decision recorded in `design-axes.md` under *Section surfaces*.

## Gotchas & dead ends
- `background_color` is absent (not None) when unset, so `{% if background_color %}` trips
  StrictUndefined; the old template survived only through `| default(...)`. Use `is defined`.
- `tests/test_goldens.py` covers only the email gallery; paged goldens are `tests/test_paged.py`,
  and `test_brochure`'s "goldens are unaffected" sweeps both again.
- Worktree venv: `python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev,pdf,qa]" numpy`,
  run with `WEASYPRINT_DLL_DIRECTORIES='C:\msys64\ucrt64\bin'`. Without numpy five paper tests fail.
- Pre-existing failures on this host, clean tree too: `test_check` drive-path (Windows `\`),
  `test_glance` no-split and `test_measure` deck paragraph (host font metrics).

## State at end
- Fix, goldens, tests and docs are in the worktree `claude/vibrant-almeida-8d2f96`, uncommitted.

## Open threads
- Commit / PR when the owner asks.
