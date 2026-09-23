"""
A landscape report on US Letter, sent as a PDF (#200): the digital PDF's fixture.

The epic's claim is "a document with a cover and contents, portrait or
landscape, sent by email as a PDF", and nothing else in the gallery is a
landscape document with both. Its copy is its own rather than ``_paged``'s,
because its point is the landscape reading layout, not an A/B against A4: a
table wide enough to want the width, a wrapped figure and a pull quote.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from svc.builder import DataTable, FullWidth, ImageBlock, PullQuote, TextBlock
from svc.builder.images import EmailImage
from svc.builder.models import TableRow
from svc.builder.sizing import LETTER_LANDSCAPE
from svc.document import (
    BackMatter,
    ContentsPage,
    Cover,
    PagedDocument,
    RunningFooter,
    RunningHeader,
    paged_medium,
)

from ._png import solid_png

_GAIN = "#4A7C59"
_LOSS = "#B85450"

#: The cover mark, light on the dark ground for ``_paged``'s reason.
_MARK_PNG = solid_png(64, 64, (236, 240, 245))

#: The cover's ground, attached so the document carries its own images.
_COVER_PNG = solid_png(160, 120, (28, 45, 64))

#: The wrapped figure: 300 dpi at its 180px display width.
_DESK_PNG = solid_png(563, 420, (91, 138, 154))

#: Fixed so the render never moves.
_YEAR = "2026"

#: Eight columns: the width a portrait page would squeeze into wrapped headers.
TENORS = ("Market", "2Y", "5Y", "10Y", "30Y", "2s10s", "5s30s", "QoQ 10Y")


def facts() -> dict[str, Any]:
    """Every ``DocumentMetadata`` fact, at values of the report's own."""
    return {
        "language": "en-US",
        "header_disclaimer": "For institutional investors only. Not investment advice.",
        "firm_name": "Hermes Research",
        "campaign_name": "Global Rates Review",
        "department": "Global Rates",
        "date_range": "July to September 2026",
        "issue_label": "Report 7",
        "current_year": _YEAR,
        "theme": "classic",
        "size_theme": "standard",
        "font_theme": "classic",
    }


def build(template_dir: Path | None = None) -> PagedDocument:
    """Build the landscape report. Deterministic: same bytes every call."""
    document = PagedDocument(
        facts(),
        template_dir=template_dir,
        medium=paged_medium(LETTER_LANDSCAPE),
        cover=Cover(
            title="Global Rates Review",
            subtitle="Six curves, one quarter, and what the desk does next",
            logo_url=EmailImage.attached(_MARK_PNG, alt="Hermes Research mark", width=64),
            logo_alt="Hermes Research",
            logo_width=64,
            background_image_url=EmailImage.attached(_COVER_PNG, alt="Cover ground", width=1056),
            align="center",
            background_color="#1C2D40",
            text_color="#ECF0F5",
        ),
        contents=ContentsPage(heading="Contents"),
        running_header=RunningHeader(
            label="Global Rates Review",
            box="top-left",
            show_page_number=False,
            follow="section",
        ),
        running_footer=RunningFooter(
            label="Hermes Research · Global Rates",
            box="bottom-right",
            show_page_number=True,
        ),
        back_matter=BackMatter(heading="Disclosures", align="left"),
    )
    for section in sections():
        document.add_section(section)
    return document


def _row(market: str, *moves: str) -> TableRow:
    """One market's row: yields, then the two spreads and the quarter's move."""
    colours = ["", "", "", "", ""] + [_GAIN if m.startswith("+") else _LOSS for m in moves[4:]]
    return TableRow(cells=[market, *moves], colors=colours)


def sections() -> list[FullWidth]:
    """The body: a summary, the wide table, the desk's view and a quote."""
    return [
        FullWidth(
            title="Summary",
            content=TextBlock(
                "<p>Six curves steepened in the quarter, and five of them did it from "
                "the front. Markets pushed the first cuts later, two-year yields rose, "
                "and the long ends held. The one exception was Japan, where the long "
                "end sold off as the central bank stepped back from the market.</p>"
            ),
        ),
        FullWidth(
            title="Curves by Market",
            content=DataTable(
                headers=list(TENORS),
                rows=[
                    _row("United States", "4.62%", "4.31%", "4.28%", "4.44%", "-34", "+13", "+6"),
                    _row("United Kingdom", "4.18%", "4.02%", "4.21%", "4.74%", "+3", "+72", "+9"),
                    _row("Germany", "2.71%", "2.38%", "2.46%", "2.69%", "-25", "+31", "-4"),
                    _row("Japan", "0.38%", "0.61%", "0.97%", "2.19%", "+59", "+158", "+14"),
                    _row("Canada", "3.94%", "3.41%", "3.38%", "3.36%", "-56", "-5", "-2"),
                    _row("Australia", "3.88%", "3.97%", "4.24%", "4.61%", "+36", "+64", "+11"),
                ],
                caption="Government bond yields and curve slopes",
                subtitle="Spreads and moves in basis points",
                source="Hermes Research",
                as_of="30 September 2026",
                label="Exhibit",
            ),
        ),
        FullWidth(
            title="From the Desk",
            content=TextBlock(
                "<p>The desk keeps the steepener in the United States and adds one in "
                "Australia, where the front end has the most room to fall if growth "
                "slows. Japan is the one curve we would not chase: its long end moved on "
                "a change of buyer, not a change of view.</p><p>Duration stays neutral. "
                "Carry pays for the wait in every market but Canada, where the curve "
                "is flat enough that waiting costs.</p>",
                figure=ImageBlock(
                    EmailImage.attached(_DESK_PNG, alt="The global rates desk", width=180),
                    caption="The global rates desk",
                    align="left",
                    wrap="left",
                ),
            ),
        ),
        FullWidth(
            title="In Their Words",
            content=PullQuote(
                "Five curves steepened from the front. The sixth tells you who stopped buying.",
                attribution="Head of Global Rates",
                align="left",
            ),
        ),
    ]
