"""
The deck medium: slides, one to a sheet, between a title slide and the disclosures.

``Deck`` is the product; ``Slide`` is the layout unit, and flattens in any
other medium as ``Page`` and ``Panel`` do; ``DividerSlide`` starts a part.
The title and closing slides are the medium's two regions. A deck reaches a
colleague as a PDF, through the unchanged exporter.
"""

from pyhermes.builder.sizing import SLIDE_4_3, SLIDE_16_9

from .document import Deck, DeckMetadata
from .fit import overflowing_slides
from .medium import DECK_MEDIUM, deck_medium
from .regions import ClosingSlide, EmptyClosingSlide, EmptyTitleSlide, TitleSlide
from .slide import DividerSlide, Slide, SlideBox

__all__ = [
    "DECK_MEDIUM",
    "SLIDE_4_3",
    "SLIDE_16_9",
    "ClosingSlide",
    "Deck",
    "DeckMetadata",
    "DividerSlide",
    "EmptyClosingSlide",
    "EmptyTitleSlide",
    "Slide",
    "SlideBox",
    "TitleSlide",
    "deck_medium",
    "overflowing_slides",
]
