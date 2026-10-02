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
    Every slide whose copy does not fit, named ``slide N: Title``.

    The body is measured against the footer band, and a title against its
    band, which holds one line (#316); a slide whose title wraps is named with
    ``(its title wraps)``, and one with both faults once, with both reasons.
    The disclosures slide is measured too. A sentinel lands past its line when
    copy overflows on the sheet, and nowhere when the engine placed it on no
    sheet at all. Empty when everything fits.

    Raises:
        pyhermes.pdf.BackendMissingError: If WeasyPrint is not installed.
        pyhermes.pdf.PdfError: If the exporter refuses the deck, as it refuses a hosted image.
    """
    from pyhermes.pdf import anchor_tops

    landed = anchor_tops(deck)
    box = deck.box()
    named = [(deck.number(slide), slide.title or "") for slide in deck.slides if slide.sections]
    if deck.closing_slide.TEMPLATE_PATHS:
        closing = len(deck.slides) + (1 if deck.title_slide.TEMPLATE_PATHS else 0) + 1
        named.append((closing, deck.closing_slide.heading))
    overflowing = []
    for number, title in named:
        body = landed.get(f"slide-{number}-end")
        body_overflows = body is None or body > box.body_bottom
        title_end = landed.get(f"slide-{number}-title-end")
        # The sentinel ends the title's last line, so past half a line below
        # the first it has wrapped onto a second.
        title_wraps = bool(title) and (
            title_end is None or title_end > box.margin_top + box.title_line / 2
        )
        name = f"slide {number}: {title}" if title else f"slide {number}"
        if title_wraps and body_overflows:
            overflowing.append(f"{name} (its title wraps, and its body overflows)")
        elif title_wraps:
            overflowing.append(f"{name} (its title wraps)")
        elif body_overflows:
            overflowing.append(name)
    return overflowing
