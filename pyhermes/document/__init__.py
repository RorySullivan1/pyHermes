"""
The paged medium, and what will become the document-only half of the builder.

``PagedDocument`` is the product; ``Page`` marks a sheet boundary inside the
section tree; the regions are the managed elements an email never had — a
cover, a contents sheet, two running margin boxes and a back-matter sheet. Each region has an
``Empty`` variant that fills no slot, the way ``EmptyHeader`` does.
"""

from .document import PagedDocument
from .medium import PAGED_MEDIUM, paged_medium
from .page import Page
from .regions import (
    BackMatter,
    ContentsPage,
    Cover,
    EmptyBackMatter,
    EmptyContentsPage,
    EmptyCover,
    EmptyRunningFooter,
    EmptyRunningHeader,
    RunningFooter,
    RunningHeader,
)

__all__ = [
    "PAGED_MEDIUM",
    "BackMatter",
    "ContentsPage",
    "Cover",
    "EmptyBackMatter",
    "EmptyContentsPage",
    "EmptyCover",
    "EmptyRunningFooter",
    "EmptyRunningHeader",
    "Page",
    "PagedDocument",
    "RunningFooter",
    "RunningHeader",
    "paged_medium",
]
