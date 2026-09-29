"""
The editorial primitives on paper (#189): an A4 page of copy set the way print sets it.

``a4_portrait`` is the paged medium's byte-identity reference and its sheet
counts are claims other tests make, so the primitives get a document of their
own rather than squeezing onto its sheets. Same facts and regions, so only the
body differs.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder import FlowedColumns, FullWidth, ImageBlock, PullQuote, TextBlock
from pyhermes.builder.images import EmailImage
from pyhermes.document import PagedDocument

from . import _paged
from ._png import solid_png

#: The wrapped figure: prints at 300 dpi at its 160px display width.
_DESK_PNG = solid_png(500, 400, (91, 138, 154))


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
        FlowedColumns(
            title="The Long Read",
            count=3,
            content=TextBlock(
                "<p>The front end repriced first. Two-year yields rose through July as "
                "the market pushed the first cut into next year, and the curve "
                "steepened with them: the long end, anchored by a softer inflation "
                "print, held its ground while the front moved.</p>"
                "<p>That was the trade. Steepeners paid, and carry paid while the "
                "book waited for the turn. Linkers lagged, and breakevens now look "
                "cheap against the path the market has priced.</p>"
                "<p>We keep the steepener into the next meeting, and add to linkers "
                "on any further weakness.</p>"
            ),
        ),
        FullWidth(
            title="From the Desk",
            content=TextBlock(
                "<p>The desk keeps the steepener on into the next meeting. The front "
                "end has further to reprice if the first cut slips again, and the long "
                "end has so far shown no appetite to follow it. Carry pays for the "
                "wait.</p><p>Linkers are the next addition. Breakevens sit below the "
                "path the market has priced for inflation, and a softer print would "
                "not change that.</p>",
                figure=ImageBlock(
                    EmailImage.attached(_DESK_PNG, alt="The rates desk", width=160),
                    caption="The rates desk",
                    align="left",
                    wrap="left",
                ),
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
