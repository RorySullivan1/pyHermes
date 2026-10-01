# 2026-10-01 · deck-medium

**Goal:** Implement epic #218 (a slide deck medium, #296–#301) and open its PR with a watch.

## What happened
- `pyhermes/deck/`: `Deck`, `Slide`, `DividerSlide`, `SlideBox`, `TitleSlide` / `ClosingSlide`
  (each with an `Empty` variant), `overflowing_slides`, `DECK_MEDIUM`, and `SLIDE_4_3`.
- `presentation`, the fifth density, is the deck's alone (`MEDIUM_DENSITIES`), set from the
  fixture's PDF: 15pt body and 30pt title on the 960pt sheet against spacious's 11.25 and 24.
- `slide-overflow` is a layout rule: `layout_findings()` runs it from `lint_document`, the
  check and `preview --lint`. The brochure's anchor reading moved to `pdf.anchor_tops`.
- `pitch_16_9` is the fourth gallery; a deck's goldens gain `NAME.notes.txt`.
- Docs: `deck.md`, the manual's page 11, a README section, and CLAUDE.md's row.

## Gotchas & dead ends
- A `valign` cell left the title slide's and the divider's copy at the top under WeasyPrint;
  absolute boxes fixed it. `BoxSurface.align` defaults to centre; `TitleSlide` overrides it.
- A centred slide lost its footer number behind the label: the footer band pins `left`.
- `textgen.wrap` breaks on hyphens, so a hyphenated sentinel split across lines.
- pdfium's `FPDFText_GetFontSize` is in text space: multiply by 0.75 for points.
- The digital-PDF determinism tests fail here on `main` too (no HarfBuzz-Subset).
