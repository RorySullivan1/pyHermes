# 2026-10-06 — epic #386, single-sheet print pieces

Implemented #396–#401 on `claude/integrate-claude-assets-pyhermes-d4spzb`, from `main` at `559df5d`.

- **#396** `bleed=True` on every section. `common/placed.html` wraps the section's tables in a block
  with negative margins and equal padding; `bleed_of(engine)` gives the distances (sheet margin by
  default). Top edge only when `Container.sheet_top` (set by `at_sheet_top()`: body's first, `Page`'s
  first, a panel's first) or `break_before`. A bled panel grows its `.panel` box into the bleed on trim
  edges and its copy box stops clipping; a slide binds `SLIDE_BLEED` (zeros).
- **#397** `pin="bottom"`. Paper: `float: footnote` (probed: absolute overlapped; footnote moved whole
  to the next sheet). Head rules for the call/marker only when pinned (`Document._head_rules`). Panel
  and slide: `position:absolute` at the box's foot via `pin_of(engine)`. The row it leaves paints no
  ground; the block carries it and zeroes its line box.
- **#398** `Columns` 2–6 slots; `separator=` glyph (1–3 chars) or `"arrow"`; refused with
  `stack="reverse"`. `common/separated-columns.html`: one real table row, `.stack-column` cells.
  New box token `component.connector` (24 / 20 / 28 / 18 / 40).
- **#399** `connector` macro in `analysis/trend-arrow.html`, VML twin; a hidden down arrow swapped
  in by an `@media` rule the email skeleton writes only when a connector exists.
- **#400** `skip_first` on both running boxes: `@page :first { @box { content: none; } }`. Opt-in.
- **#401** `_product_brief.py`, `letter_product_brief` (3 sheets), `product_brief_layout`;
  `tests/test_print_pieces.py`; manual section in `07-reports-and-pdfs.md`; README paragraph.

**Probes** in the scratchpad, recorded in `media.md`. The pinned float first showed a sliver of
ground where its empty row stayed in flow, and extra height from the area's line box; both fixed.
The brochure band first stopped short of the top trim because `.panel-copy` also clips.

Same container flakes as before: PDF byte determinism (no HarfBuzz-Subset).
