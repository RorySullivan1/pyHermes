# 2026-09-24 · table-semantics

**Goal:** Complete epic #217 (table semantics for quantitative material) and open a PR onto `main`.

## What happened
- One commit per child on `claude/integrate-claude-assets-pyhermes-d4spzb`, restarted from `main`
  after PR #210 (the claudeBrain sync) merged.
- #223 `ColumnGroup` + `groups=`: a `thead` tier of `th scope="colgroup"`, centred labels in
  `text()`, and the `table-header-tier` lint rule in every medium. `a4_long_table.build_grouped()`
  re-measures the engineered boundaries under a tiered head.
- #224 markers in heads and cells: `coerce_notes` over the whole table in reading order, `marked()`
  in the template, and `text_markers` before the column widths are measured. `Cell.note` refused.
- #225 `Column.format` / `Column.tone`, `Cell.value`, raw figures in rows; `table_from_frame`
  now defers to the columns.
- #226 `Column.align_decimal` via `textgen.decimal_pads` (with a virtual point before a suffix),
  and `Column.unit` as a units `thead` row. The grouped long-table counts are now `(7, 8, 11)`.
- #227 `HeatScale` + `Column.scale`, the `heat_color` filter, `Column.bar` as a nested
  presentation table with the `table_bar_height` token.
- #228 `letter_quant_table` (2 sheets, Letter), the factsheet's returns table rewritten,
  `data-table.md` sections and post-mortem, README, CLAUDE.md, qa-harness.md.

## Gotchas & dead ends
- **The rasters found two defects nothing else could see:** a tone on its own heat tint was
  illegible (the fix is `readable_on`), and a superscript marker padded as `[1]` pulled an aligned
  column askew (the fix is a hanging marker in the markup only).
- A bar cell sized `0%` beside an unsized filler got auto-layout width; both cells now carry
  widths. The mobile `.data-table td` padding rule is beaten by inline `padding: 0 !important`.
- `TestComponentFieldsAreExercised` passed vacuously on `groups=[]`; it now treats an empty
  collection as unset.
- A new component size token must render in `kitchen_sink` (`TestTheTokensAreLive`), which is
  why `kitchen_sink` draws a bar. The colour audit accepts a heat tint only if `heat_color`
  derives it from a theme's own tokens.
- Paged goldens regenerate through `tests/test_paged.py --update-goldens`, not
  `test_goldens.py`.

## Open threads
- A real Outlook render of a grouped table (header `colspan`) is still owed (#150's posture).
