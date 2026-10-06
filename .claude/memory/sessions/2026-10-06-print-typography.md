# 2026-10-06 — epic #385, print typography

Implemented #391–#395 on `claude/integrate-claude-assets-pyhermes-d4spzb`, from `main` at `0a513ef`.

- **#391** `FontStack(files={"400": path})` reads and sniffs each file into a `FontFile`
  (content id `font-<sha256[:16]>.<ext>`); `FontTheme.faces` and `.assets()`;
  `Document.fonts()` (paged only) beside `assets()`; the exporter serves `assets() + fonts()`,
  the handout too. `common/font-faces.html` in the three paper skeletons; `FontFace.css` writes
  the rule so no template holds a `font-family` literal. `chart_style` registers the files with
  matplotlib and uses the name read from the file. Specimen face: `qa/fixtures/fonts/`, built by
  `build_specimen.py` from DejaVu Sans (subset, 82% wide, renamed; licence beside it).
  `fontTools` joined mypy's ignore list. `tests/test_house_typeface.py`.
- **#392** `title_size="display"`, `title_case="upper"` on every section (`check_title_type`);
  the `h2` reads `size.type.title` and carries `mobile-title`.
- **#393** `type_size="fine"` → `fine_print(scheme)` rebinding on paper: body, secondary, small at
  `micro`, leading `legal_line`, measure scaled to keep its px. BackMatter and the closing slide
  stay at `small` (recorded).
- **#394** `TextAlign.JUSTIFY`; `_validate_align(justify=)`; `JUSTIFIES` on `TextBlock`;
  `models.justified()` blanks it off paper; `hyphens:auto` beside it. `test_alignment`'s
  "caller may never reach justify" test rewritten to the new rule.
- **#395** `qualifier=` on `ChartBlock`, `DataTable`, `ImageBlock`, `FigureGrid` (refused on a
  panel); `common/qualifier.html`; `_with_subtitle` prints it; `Deck.notes()` adds
  `Exhibit N: qualifier` lines.
- Gallery: `brief_layout` + `letter_brief` (`_brief.py`, 3 Letter sheets).
  `tests/test_print_typography.py`.

**Found on the way:** `main` failed `test_paged` for `a4_toned_layout`: #412 regenerated the
email golden only. The PR carries the paged golden; its diff is #390's lines alone.

**Probes:** WeasyPrint names an embedded `@font-face` family `House-Sans` in the PDF, which
pypdfium2's `FPDFText_GetFontInfo` reads back. It hyphenates with U+2010. The first brief ran to
four sheets with a forced break; dropping it put the reading-size note and the fine print on one.

Same container flakes as before: PDF byte determinism in `test_digital_pdf`, `test_attachments`
and the deck handout test (no HarfBuzz-Subset here).
