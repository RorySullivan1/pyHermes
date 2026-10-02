# 2026-10-02 — epic #361, placement across phones, sheets and media

Implemented #362–#367 on `claude/integrate-claude-assets-pyhermes-d4spzb`.

- **#362/#363** `stack="natural" | "reverse" | False` on every split and `Columns`. Reverse =
  columns written in phone order under `dir="rtl"` (band cell + MSO ghost table), `dir="ltr"`
  per column, gutter margin flipped. Unstacked = a fluid percentage row (`sizing.shares`),
  refused below `Config.min_column_px` at `PHONE_FLOOR` 375. Paper ignores both.
- **#364** `keep_together` / `break_before` on `Container`; paper-only `tr` styles; refused in
  `Panel` and `Slide`; `Container.opening()` generalises `Page.opening()`; tall kept section
  warns from `layout()` / `render_pdf()` via `kept-section-N` ids appearing on >1 sheet.
- **#365** `Only` (composite) and `OnlySections` (section list). `Document.configured()` binds
  `walking_in(medium.name)`; numbered apparatus inside is refused.
- **#366** `Slide(layout=, side=)`, `SlideBox.regions()`, per-region sentinels.
- **#367** `placed_layout` / `a4_placed_layout`, pitch_16_9 sidebar slide, manual pages 9 and
  11, rules files, CI module lists.

Every pre-existing golden byte-identical except `pitch_16_9` (opted in). Container-only flakes:
the PDF byte-determinism tests (no HarfBuzz-Subset), including `test_attachments`' two.
