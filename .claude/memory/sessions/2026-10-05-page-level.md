# 2026-10-05 — epic #340, page-level presentation for print

Implemented #341–#345 on `claude/integrate-claude-assets-pyhermes-d4spzb`, from `main` at `b9574c2`.

- **#341** `Page(orientation=)` and `add_page(..., orientation=)`. `PagedDocument._body_context`
  lays the body as runs of sheets one way up, one `document-container` table a run; the turned
  run carries `page: landscape`, the next `break-before: page`. `_body_sections` drops each
  run's leading break (the size report shares it). Seed leaves take the turned name when the
  body opens turned with no list sheet between. `tests/test_landscape_pages.py`.
- **#342** `DocumentMetadata.stamp` (24 chars, plain text), `common/stamp.html` in the three
  paper skeletons, the email strip's first line, `[DRAFT]` opening the text part,
  `Email.validate` refusing an `EmptyHeader`. `stamp_type()` sizes it from the sheet.
  `tests/test_stamp.py` reads its glyph boxes back centred on every sheet.
- **#343** `Aside` in `surfaces.py`, a frozen value object rendered through `Callout`;
  `TextBlock(aside=)`, one float a block. A third of the column on paper, floored at
  `8 × callout_pad_x` up to half. `tests/test_aside.py`.
- **#344** `QrCode` in `surfaces.py` (paper image, email `Button`, no email manifest entry via
  `PAGED_MEDIA`), `pyhermes/qr` on segno, `[qr]` extra, `zxing-cpp` in `[qa]`,
  `qa/fixtures/_qr.py` + `_png.matrix_png`. `tests/test_qr.py`; purity in `test_data_layer`.
- **#345** `a4_wide_appendix`; `tri_fold_letter` aside + QR; `pitch_16_9` CONFIDENTIAL; the
  research pair an aside; `kitchen_sink` stamp + QR, three ratio splits untitled to pay.
  `media.md`, `brochure.md`, `qa-harness.md`, the manual's page 7, README, CLAUDE.md, CI.

**Probes, and what they decided:** `page:` on a `tr` is inert; on a flow table it works, and the
portrait content after it stays landscape without an explicit break. A fixed box repeats on every
sheet in all three media, but under the content it vanished behind painted grounds, so the stamp
goes over at 0.6 opacity. A `left: -50%` box drifted; `left: 50%` plus a negative half-width
centres. The aside float wraps in a page column and in a panel's clipped box.

Same container flakes as before: PDF byte determinism in `test_digital_pdf`, `test_attachments`
and the handout test, each also failing on clean `main` here.
