"""
The paged medium: a document laid onto sheets rather than into an inbox.

Same section tree, same three design axes, a different skeleton and a
different page. What it does *not* carry is as deliberate as what it does:
no Gmail size constraint, because nothing clips a PDF at 102 KB, and no
Outlook accommodations, because Word is not rendering it.
"""

from __future__ import annotations

from dataclasses import replace

from pyhermes.builder.medium import Medium
from pyhermes.builder.sizing import A4_PORTRAIT, PageFormat

from .regions import BackMatter, ContentsPage, Cover, ExhibitsPage, RunningFooter, RunningHeader

__all__ = ["PAGED_MEDIUM", "paged_medium"]

#: The shipped paged medium, on A4 portrait.
#:
#: Its skeleton is named ``base.html`` and resolved through the overlay
#: ``document/`` — the fork mechanism #160 shipped, doing the job it exists
#: for. A4, Letter and a slide-shaped sheet are one medium at several pages:
#: they share a skeleton, a slot contract and a rule set. A deck, one slide
#: to a sheet, is its own medium since #218 (`pyhermes.deck`).
PAGED_MEDIUM = Medium(
    name="document",
    skeleton="base.html",
    page_format=A4_PORTRAIT,
    region_types=(Cover, ContentsPage, ExhibitsPage, RunningHeader, RunningFooter, BackMatter),
    template_search_path=("document",),
    paged=True,
    measure="standard",
)


def paged_medium(page: PageFormat) -> Medium:
    """The paged medium on ``page`` — A4, Letter, a slide, either way up."""
    return replace(PAGED_MEDIUM, page_format=page)
