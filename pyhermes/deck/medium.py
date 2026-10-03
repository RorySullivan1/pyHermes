"""
The deck medium: one slide to a sheet, projected or sent as a PDF.

A medium rather than a page preset because a slide changes the skeleton, the
unit of layout and the constraint: one idea is one sheet, and copy that does
not fit is a finding rather than a second sheet. `.claude/rules/deck.md`
carries the reasoning, and why the 16:9 page alone was not a deck.
"""

from __future__ import annotations

from dataclasses import replace

from pyhermes.builder.medium import Medium
from pyhermes.builder.sizing import SLIDE_16_9, PageFormat

from .regions import ClosingSlide, TitleSlide

__all__ = ["DECK_MEDIUM", "deck_medium"]

#: The shipped deck medium, on a 16:9 slide.
#:
#: The overlay searches ``deck/`` first, then the paged medium's
#: ``document/``, then the shared tree, so a deck forks only its skeleton and
#: its sheets, and shares the paged medium's editorial partial. It has two
#: regions, the slides a deck opens and closes on; every slide between them
#: is a ``Slide`` the caller composes.
DECK_MEDIUM = Medium(
    name="deck",
    skeleton="base.html",
    page_format=SLIDE_16_9,
    region_types=(TitleSlide, ClosingSlide),
    template_search_path=("deck", "document"),
    paged=True,
    measure="standard",
)


def deck_medium(page: PageFormat) -> Medium:
    """The deck medium on ``page``: ``SLIDE_16_9``, ``SLIDE_4_3`` or a page of your own."""
    return replace(DECK_MEDIUM, page_format=page)
