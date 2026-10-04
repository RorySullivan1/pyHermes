# 2026-10-04 — epic #346, deck layouts

Implemented #347–#353 on `claude/integrate-claude-assets-pyhermes-d4spzb`, restarted from
`main` after PR #373 merged.

- **#347** `Slide(source=, as_of=)`; `SlideBox.with_source`, `source_top`; the box is per slide
  (`Deck.slide_box`). Citations ride a new `Document._marked()` hook the walk and `validate`
  read; `Deck` adds each slide's source. A footnote in a source is refused.
- **#348** `background_image` + `ground`, `image` + `image_side`; `SlideBox.picture`, `left`;
  `IMAGE_FIELDS`; `SLIDE_DPI = 96` through `validate_image_resolution(dpi=)`. The skeleton's
  clear-ground rule is emitted only when a slide carries a full-bleed picture.
- **#349** `StatementSlide`, `Deck.add_statement`; `Slide.TITLE_BAND`, `False` for it and a
  divider. **Found:** the first fit run named both dividers "(its title wraps)" once the
  agenda put them in the check: they have no title band.
- **#350** `Deck(divider_agenda=True)`, `AgendaEntry`; the title takes the sidebar's main.
- **#351** `Deck.handout(page)`, `pyhermes.pdf.render_handout` / `save_handout`: the sheet
  markup scaled by CSS, not rastered, so `[pdf]` alone suffices (`deck.md` says why).
- **#352** `DeckFooter`, `SheetFooter`; the mark follows the label, after a centred mark met
  the label on a half sheet in the first raster.
- **#353** `pitch_layouts_16_9`, a second deck fixture; `tests/test_deck_layouts.py`; the
  manual's deck page; CI's `pdf` job prints and photographs each handout.

Goldens: four new for `pitch_layouts_16_9`; every other golden byte-identical. Same container
flakes as #361 (PDF determinism, without HarfBuzz-Subset).
