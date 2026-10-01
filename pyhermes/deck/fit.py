"""
Whether every slide's copy fits its body, asked of the print engine.

A slide clips what overflows it (#297), and a clip is silent in the PDF. This
lays the deck out and reads back where each slide's closing sentinel landed,
as :func:`~pyhermes.brochure.overflowing_panels` does for a panel. It needs the
``[pdf]`` extra, imported only on use.
"""

from __future__ import annotations

from .document import Deck


def overflowing_slides(deck: Deck) -> list[str]:
    """
    Every slide whose copy runs past its body, named ``slide N: Title``.

    The disclosures slide is measured too. A sentinel lands below the body
    when copy overflows on the sheet, and nowhere when the engine placed it
    on no sheet at all. Empty when everything fits.

    Raises:
        pyhermes.pdf.BackendMissingError: If WeasyPrint is not installed.
    """
    from pyhermes.pdf import anchor_tops

    landed = anchor_tops(deck)
    limit = deck.box().body_bottom
    named = [(deck.number(slide), slide.title or "") for slide in deck.slides if slide.sections]
    if deck.closing_slide.TEMPLATE_PATHS:
        closing = len(deck.slides) + (1 if deck.title_slide.TEMPLATE_PATHS else 0) + 1
        named.append((closing, deck.closing_slide.heading))
    overflowing = []
    for number, title in named:
        y = landed.get(f"slide-{number}-end")
        if y is None or y > limit:
            overflowing.append(f"slide {number}: {title}" if title else f"slide {number}")
    return overflowing
