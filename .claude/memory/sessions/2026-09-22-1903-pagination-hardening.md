# 2026-09-22 19:03 · pagination-hardening

**Goal:** Review and execute epic #169: thead, break rules, page margins, the long-table fixture

Epic #169 implemented in six commits on `claude/gifted-ritchie-7dkp5g`, all four sub-issues
(#173–#176). Not merged; no PR opened.

## What happened
- **#173 `d8d413e`**: `thead`/`tbody` on the data table, alone. The golden diff was checked by a
  script: 48 added tag lines across 12 tables, no removals. 28/28 email screenshots
  pixel-identical. Two lint tests counted the substring `<th`, which `thead` matches, and now match
  the element name.
- **#173 `6fab7c8`**: `row-total` / `row-subhead` hooks and three row rules in
  `document/base.html`'s style block.
- **#174 `612596b`**: `section-title`, `fine-print`, `figure` hooks, a caption rule, and
  `orphans`/`widows` at 2 on `body`.
- **#175 `5ccc10c`**: `PageMargin` on `PageFormat`. The sheet is `width`/`height`, the frame is
  the sheet less the margin, and the cover spans the sheet. A4 20mm, Letter 0.75in, slide 10mm.
- **#174 `9b8c35f`**: a `subtitle` hook on all seven subtitle paragraphs. The first raster of the
  new fixture found a chart's subtitle stranded; no issue had named it.
- **#176 `9387beb`**: `a4_long_table`, PDF text tests via pypdfium2, and the paged-only
  `table-structure` lint rule. The `thead` removal is a committed test.

## Gotchas & dead ends
- **An `avoid` needs an earlier break to fall back to.** A probe that opens the document with the
  section under test always strands the title, rule or no rule. Probes need a preceding section.
- **Cell padding moves a whole table.** When a table's rows fit but the container cell's bottom
  padding does not, WeasyPrint 70 breaks before the table rather than inside it.
- **Rules interact.** `.figure` moving a chart whole is what stranded its subtitle. Without any
  rules the subtitle never strands, so its test strips that one rule only.
- **A 15mm A4 side margin makes the frame exactly 680px, the email's width.** Rejected, because a
  template still reading the email frame would then look right on paper.
- **`_validate_size_fields` rejects zero**, so a margin could not be four plain frame tokens.
- **Two Pythons on this box.** Bare `pytest`/`mypy` resolve to `/root/.local` without Jinja2; use
  `python -m pytest` / `python -m mypy`. Screenshots need
  `PYHERMES_CHROMIUM=/opt/pw-browsers/chromium`.

## State at end
- Branch pushed with six commits on `2f1dacb`. 2048 tests pass with every extra, and 1947 pass
  with 107 skipped under `[dev]` alone. ruff and mypy are clean.

## Open threads
- Open a PR with one `Closes` line for each of #169 and #173–#176, then check
  `sub_issues_summary` after merge.
- CLAUDE.md "Open work and state" should name #169 as done once it merges.
