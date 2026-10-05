"""
Labels and status (#328), shared by the email and the paged fixture.

Every object epic #324 added, each away from its default: cards badged in all
three tones, a recommendation table whose ratings carry badges beside a status
column drawn as dots in all three tones, a badged full-width title, a badged
split title on a dark band, and a twelve-tag row that wraps. Both media build
the same sections, so each golden pins what its own medium makes of them.
"""

from __future__ import annotations

from pyhermes.builder import (
    Badge,
    CardGroup,
    Column,
    Container,
    DataTable,
    FullWidth,
    TagRow,
    TextBlock,
    TwoColumn,
)
from pyhermes.builder.models import Cell, KpiItem, TableRow

#: Each status a dashboard row may hold, and the tone its dot is drawn in.
STATUSES = {"On track": "positive", "Watch": "neutral", "Breach": "negative"}

#: The tags under the coverage note: twelve, so the row has to wrap.
TAGS = [
    "Rates",
    "Credit",
    "FX",
    "Equities",
    "Commodities",
    "Inflation",
    "Emerging markets",
    "Money markets",
    "Covered bonds",
    "Supranationals",
    "Municipals",
    "Securitised",
]


def _rating(text: str, badge: Badge | None = None) -> Cell:
    return Cell(text, badge=badge)


def sections() -> list[Container]:
    """The sections both fixtures render, in order."""
    return [
        FullWidth(
            title="Recommendations",
            badge=Badge("Preliminary"),
            content=CardGroup(
                [
                    KpiItem("10Y gilt", "Overweight", badge=Badge("Upgrade", "positive")),
                    KpiItem("Linkers", "Neutral", badge="New"),
                    KpiItem("Sterling credit", "Underweight", badge=Badge("At risk", "negative")),
                ]
            ),
        ),
        FullWidth(
            title="Risk dashboard",
            content=DataTable(
                [
                    "Book",
                    Column("Rating", kind="text"),
                    Column("Status", kind="status", statuses=STATUSES),
                    "Limit",
                ],
                [
                    TableRow(["Rates", "", "", ""], kind="subhead"),
                    TableRow(
                        ["Gilts", _rating("A", Badge("Upgrade", "positive")), "On track", "62%"]
                    ),
                    TableRow(["Linkers", _rating("A-"), "Watch", "81%"]),
                    TableRow(["Credit", "", "", ""], kind="subhead"),
                    TableRow(
                        [
                            "Sterling IG",
                            _rating("BBB", Badge("Downgrade", "negative")),
                            "Breach",
                            "104%",
                        ]
                    ),
                    TableRow(["Covered", _rating("AA", Badge("New")), "On track", "40%"]),
                ],
                caption="Books against their limits",
                source="Hermes Risk",
            ),
        ),
        TwoColumn(
            "70-30",
            title="Coverage",
            badge=Badge("Updated", "positive"),
            background_color="#22313F",
            left=TextBlock(
                "<p>The desk covers twelve markets this quarter, two more than last, "
                "and publishes on each at least monthly.</p>"
            ),
            right=TagRow(["Rates", "Credit", "FX"]),
        ),
        FullWidth(title="Markets covered", content=TagRow(TAGS)),
    ]
