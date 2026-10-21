"""
Whether every slide's copy fits its body, asked of the print engine.

A slide clips what overflows it (#297), and a clip is silent in the PDF. This
lays the deck out and reads back where each slide's closing sentinel landed,
as :func:`~pyhermes.brochure.overflowing_panels` does for a panel. It needs the
``[pdf]`` extra, imported only on use.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .document import Deck
from .slide import DividerSlide, Slide, SlideBox

if TYPE_CHECKING:  # pragma: no cover - the exporter is imported only on use
    from pyhermes.builder.sizing import PageFormat
    from pyhermes.pdf import Layout

#: How far, in px, a note's last line may sit past its box before it is named: sub-pixel layout.
HANDOUT_TOLERANCE = 0.5


def overflowing_slides(deck: Deck, laid_out: Layout | None = None) -> list[str]:
    """
    Every slide whose copy does not fit, named ``slide N: Title``.

    The body is measured against the footer band, or a source band over it
    (#347), each region of a laid-out body on its own (#366); a title and a
    source each against the one line its band holds (#316). A slide is named
    once, with each reason, ``(its title wraps, and its body overflows)``.
    A divider's agenda is measured when the deck shows one (#350).
    The disclosures slide is measured too. A sentinel lands past its line when
    copy overflows on the sheet, and nowhere when the engine placed it on no
    sheet at all. Empty when everything fits. ``laid_out``, a
    :func:`~pyhermes.pdf.layout` of this deck, is read rather than laying it out again.

    Raises:
        ValueError: If ``laid_out`` is a layout of another document.
        pyhermes.pdf.BackendMissingError: If WeasyPrint is not installed.
        pyhermes.pdf.PdfError: If the exporter refuses the deck, as it refuses a hosted image.
    """
    from pyhermes.pdf import anchor_tops

    landed = anchor_tops(_own(deck, laid_out))
    named: list[tuple[int, str, Slide | None, SlideBox]] = [
        (deck.number(slide), slide.title or "", slide, deck.slide_box(slide))
        for slide in deck.slides
        if slide.sections or (deck.divider_agenda and isinstance(slide, DividerSlide))
    ]
    if deck.closing_slide.TEMPLATE_PATHS:
        closing = len(deck.slides) + (1 if deck.title_slide.TEMPLATE_PATHS else 0) + 1
        named.append((closing, deck.closing_slide.heading, None, deck.box()))
    overflowing = []
    for number, title, slide, box in named:
        # A laid-out body has a sentinel per region, and either overflowing names it (#366).
        has_side = slide is not None and slide.layout != "full"
        ends = [f"slide-{number}-end", *([f"slide-{number}-side-end"] if has_side else [])]
        tops = [landed.get(end) for end in ends]
        body_overflows = any(top is None or top > box.body_bottom for top in tops)
        reasons = []
        # A sentinel ends its line's copy, so past half a line below the first it has wrapped.
        if title and (slide is None or slide.TITLE_BAND):
            title_end = landed.get(f"slide-{number}-title-end")
            if title_end is None or title_end > box.margin_top + box.title_line / 2:
                reasons.append("its title wraps")
        if slide is not None and slide.source:
            source_end = landed.get(f"slide-{number}-source-end")
            first_line = box.source_top + box.source_height - box.source_line
            if source_end is None or source_end > first_line + box.source_line / 2:
                reasons.append("its source wraps")
        if body_overflows and reasons:
            reasons.append("its body overflows")
        name = f"slide {number}: {title}" if title else f"slide {number}"
        if reasons:
            overflowing.append(f"{name} ({_listed(reasons)})")
        elif body_overflows:
            overflowing.append(name)
    return overflowing


def clipped_notes(
    deck: Deck, page: PageFormat | None = None, laid_out: Layout | None = None
) -> list[str]:
    """
    Every slide whose speaker notes the handout clips, named ``slide N: Title`` (#459).

    A handout sheet is one page, so its notes fill the room the page leaves under
    the scaled slide and are clipped past it. The clip is silent in the PDF, as a
    slide's is: this reads where the end of each slide's notes landed against the
    foot of their box. ``laid_out``, a :func:`~pyhermes.pdf.layout_handout` of
    this deck, is read rather than laying the handout out again. Empty when
    every note fits.

    Raises:
        ValueError: If ``laid_out`` is not this deck's handout.
        pyhermes.pdf.BackendMissingError: If WeasyPrint is not installed.
        pyhermes.pdf.PdfError: If the exporter refuses the deck, as it refuses a hosted image.
    """
    from pyhermes.pdf import anchor_tops, layout_handout

    if laid_out is None:
        laid_out = layout_handout(deck, page)
    elif laid_out.document is not deck or not laid_out.handout:
        raise ValueError("laid_out is not a handout layout of this deck")
    landed = anchor_tops(laid_out)
    opening = 1 if deck.title_slide.TEMPLATE_PATHS else 0
    clipped = []
    for number, slide in enumerate(deck.slides, start=1 + opening):
        if not slide.notes.strip():
            continue
        end, limit = (landed.get(f"handout-{number}-notes-{part}") for part in ("end", "limit"))
        if end is None or limit is None or end > limit + HANDOUT_TOLERANCE:
            clipped.append(f"slide {number}: {slide.title}" if slide.title else f"slide {number}")
    return clipped


def _listed(reasons: list[str]) -> str:
    """``a``, ``a, and b``, or ``a, b, and c``: the reasons a slide is named for."""
    if len(reasons) == 1:
        return reasons[0]
    return ", ".join(reasons[:-1]) + ", and " + reasons[-1]


def _own(deck: Deck, laid_out: Layout | None) -> Deck | Layout:
    """The layout to measure: ``laid_out`` when it is this deck's, else the deck itself."""
    if laid_out is None:
        return deck
    if laid_out.document is not deck:
        raise ValueError("laid_out is a layout of another document, not this deck")
    if laid_out.handout:
        raise ValueError(
            "laid_out is the deck's handout, whose sheets are scaled; lay out the deck"
        )
    return laid_out
