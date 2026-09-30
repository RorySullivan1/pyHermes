# 2026-09-30 · composition

**Goal:** Implement epic #261 (composition: several blocks in one cell, columns inside a cell).

## What happened
- Found PR #260 merged at `a1c3c82`, before #258's fix and the regenerated examples were pushed;
  merged `main` into the branch (a reset was refused as destructive) so both ride the #261 PR.
- #262: `Stack` in `pyhermes/builder/composition.py`; `Component.children()`, `descendants()`,
  `leaves()`; `Document._components()` walks leaves, `_spacings()` every node.
- #264: `ratio=` takes weights, `Config.min_column_px` (90) checked at the standard frame;
  `FourColumn`; `column_layout(..., within=)`; new gallery fixture `composed_layout`.
- #263: `Columns`, sized by a `cell_width` each container binds; one level, refused at construction.

## Gotchas & dead ends
- `column_layout` already used `total` as a local (the sum of weights); a `total=` parameter was
  silently overwritten and gave 50px columns. Named `within` instead.
- `block_gap` is also a `TextBlock`'s bottom margin, so a Stack override moves paragraph gaps too.
  Judged against a screenshot and kept rather than minting a token.
- `FourColumn` cannot read `column_pad_x`: a column that wide leaves the others under the floor.
- The spacing reverse-sentinel caught `Columns` reading `pad_x` alone (the frame fallback);
  recorded in `test_spacing.FALLBACK_READS` rather than declared.
- Pre-existing, filed separately: at the phone breakpoint a split's column cell shrinks to its
  content, so a table in a stacked column is only as wide as its figures.
