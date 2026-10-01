"""
The same paged content on a 16:9 sheet: the paged medium, landscape.

Its value is the diff against ``a4_portrait``: identical copy, one
``PageFormat`` apart, flowing from sheet to sheet like a report. A real deck,
one slide to a sheet with a title band and a numbered footer, is the deck
medium since #218 (``pitch_16_9``); `.claude/rules/deck.md` records why the
"a slide is a page" decision this fixture once carried was superseded.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder.document import Document
from pyhermes.builder.sizing import SLIDE_16_9
from pyhermes.document import paged_medium

from . import _paged


def build(template_dir: Path | None = None) -> Document:
    """Build the 16:9 slide document. Deterministic: same bytes every call."""
    return _paged.build_on(paged_medium(SLIDE_16_9), template_dir)
