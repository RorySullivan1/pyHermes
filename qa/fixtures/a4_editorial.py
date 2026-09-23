"""
The editorial primitives on paper (#189): an A4 page of copy set the way print sets it.

``a4_portrait`` is the paged medium's byte-identity reference and its sheet
counts are claims other tests make, so the primitives get a document of their
own rather than squeezing onto its sheets. Same facts and regions, so only the
body differs.
"""

from __future__ import annotations

from pathlib import Path

from svc.builder import FullWidth, PullQuote, TextBlock
from svc.document import PagedDocument

from . import _paged


def build(template_dir: Path | None = None) -> PagedDocument:
    """Build the editorial page. Deterministic: same bytes every call."""
    document = PagedDocument(_paged.facts(), template_dir=template_dir, **_paged.regions())
    for section in sections():
        document.add_section(section)
    return document


def sections() -> list[FullWidth]:
    """The body, one section per primitive, so each golden diff names one."""
    return [
        FullWidth(
            title="The Quarter",
            content=TextBlock(
                "<p>The curve steepened through the quarter as the front end repriced. "
                "Duration added to returns for the first time in four quarters, and "
                "the long end held its ground while the front moved. Carry paid, and "
                "the book was paid to wait for the turn.</p>",
                drop_cap=True,
            ),
        ),
        FullWidth(
            title="In Their Words",
            content=PullQuote(
                "Duration earned its place in the book again this quarter.",
                attribution="Head of Rates Strategy",
                align="right",
            ),
        ),
    ]
