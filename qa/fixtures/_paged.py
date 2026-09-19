"""
Shared content for the paged fixtures, so a page change is the only variable.

``a4_portrait`` and ``slide_16_9`` render the *same* sections onto different
pages. Reusing the copy rather than writing two documents is what makes the
pair a true A/B: byte-for-byte the same content, one ``PageFormat`` apart, so
every difference between the two goldens is the page and nothing else — the
technique ``compact_size`` and ``spacious_size`` use for density.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from svc.builder import CardGroup, DataTable, FullWidth, TextBlock, TwoColumn
from svc.builder.document import Document
from svc.builder.enums import CardOrientation, TwoColumnRatio
from svc.builder.medium import Medium
from svc.builder.models import KpiItem, TableRow

_GAIN = "#4A7C59"
_LOSS = "#B85450"

#: Fixed so the render never moves. A fixture that reads the clock cannot be
#: snapshotted.
_YEAR = "2026"


def facts() -> dict[str, Any]:
    """Every ``DocumentMetadata`` field, each at a distinctive value."""
    return {
        "language": "en-GB",
        "header_disclaimer": "For illustrative purposes. Not investment advice.",
        "firm_name": "Hermes Research",
        "campaign_name": "Quarterly Review",
        "department": "Rates Strategy",
        "date_range": "Quarter ending 30 September",
        "issue_label": "Issue 001",
        "current_year": _YEAR,
        "theme": "classic",
        "size_theme": "standard",
        "font_theme": "classic",
    }


def build_on(medium: Medium, template_dir: Path | None = None) -> Document:
    """The shared document, laid onto ``medium``'s page."""
    document = Document(facts(), template_dir=template_dir, medium=medium)
    return (
        document.add_section(
            FullWidth(
                title="Market Snapshot",
                highlight=True,
                content=CardGroup(
                    [
                        KpiItem("S&P 500", "5,234", _GAIN, "+1.42%"),
                        KpiItem("UST 10Y", "4.28%", _LOSS, "+6 bps"),
                        KpiItem("Gold", "2,411", _GAIN, "+0.85%"),
                    ],
                    orientation=CardOrientation.HORIZONTAL,
                ),
            )
        )
        .add_section(
            FullWidth(
                title="Narrative",
                content=TextBlock(
                    "<p>The curve steepened through the quarter as the front end "
                    "repriced. Duration added to returns for the first time in "
                    "four quarters.</p>"
                ),
            )
        )
        .add_section(
            FullWidth(
                title="Factor Returns",
                content=DataTable(
                    headers=["Factor", "1M", "YTD"],
                    rows=[
                        TableRow(cells=["Value", "+1.8%", "+7.4%"], colors=["", _GAIN, _GAIN]),
                        TableRow(cells=["Momentum", "-0.4%", "+11.2%"], colors=["", _LOSS, _GAIN]),
                        TableRow(cells=["Quality", "+0.9%", "+5.1%"], colors=["", _GAIN, _GAIN]),
                    ],
                    source="Hermes Research",
                    as_of="30 September 2026",
                    subtitle="Long-short, gross of costs",
                ),
            )
        )
        .add_section(
            TwoColumn(
                ratio=TwoColumnRatio.EQUAL,
                title="Positioning",
                left=TextBlock("<p>The left half of a 50-50 split.</p>"),
                right=TextBlock("<p>The right half of a 50-50 split.</p>"),
            )
        )
    )
