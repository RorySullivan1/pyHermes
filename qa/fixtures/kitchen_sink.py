"""
Every public component, in every container geometry.

The broadest fixture in the gallery, and the one a golden snapshot is worth
the most on: a change to any component template or container ratio moves this
render. A completeness test keeps it honest — a new ``Component`` subclass
that never joins this fixture fails the suite rather than silently going
unrendered forever.
"""

from __future__ import annotations

from svc.builder import (
    AuthorBlock,
    CardGroup,
    ChartBlock,
    DataTable,
    Email,
    EmailBuilder,
    FullWidth,
    ImageBlock,
    NumberedList,
    TextBlock,
    ThreeColumn,
    TwoColumn,
)
from svc.builder.enums import CardOrientation, ImageAlign, ThreeColumnRatio, TwoColumnRatio
from svc.builder.images import EmailImage
from svc.builder.models import Card, KpiItem, NumberedItem, TableRow

from ._png import solid_png

#: Fixed so the render never moves. A fixture that reads the clock cannot be
#: snapshotted.
_YEAR = "2026"

_GAIN = "#4A7C59"
_LOSS = "#B85450"

_CHART_PNG = solid_png(320, 120, (42, 61, 84))
_THUMB_PNG = solid_png(96, 96, (184, 84, 80))


def _metadata() -> dict[str, str]:
    return {
        "email_subject": "Kitchen Sink — every component, every geometry",
        "preheader_text": "One fixture exercising the whole component library.",
        "firm_name": "Hermes Research",
        "campaign_name": "kitchen-sink",
        "date_range": "Week ending 24 August",
        "issue_label": "Issue 001",
        "header_disclaimer": "For illustrative purposes. Not investment advice.",
        "contact_description": "Reach the research desk with questions.",
        "contact_url": "https://example.com/contact",
        "footer_disclaimer": "<p>Distributed to registered recipients only.</p>",
        "current_year": _YEAR,
        "unsubscribe_url": "https://example.com/unsubscribe",
        "view_in_browser_url": "https://example.com/archive/001",
    }


def build() -> Email:
    """Build the kitchen-sink email. Deterministic: same bytes every call."""
    return (
        EmailBuilder()
        .metadata(_metadata())
        # FullWidth + horizontal CardGroup + highlight.
        .section(
            FullWidth(
                title="Market Snapshot",
                highlight=True,
                content=CardGroup(
                    [
                        KpiItem("S&P 500", "5,234", _GAIN, "+1.42%"),
                        KpiItem("UST 10Y", "4.28%", _LOSS, "+6 bps"),
                        KpiItem("Gold", "2,411", _GAIN, "+0.85%"),
                        KpiItem("VIX", "14.32", _GAIN, "-2.18 pts"),
                    ],
                    orientation=CardOrientation.HORIZONTAL,
                ),
            )
        )
        # Vertical CardGroup — the same cards, stacked, carrying prose bodies.
        .section(
            FullWidth(
                title="Sector Notes",
                content=CardGroup(
                    [
                        Card(
                            "Technology",
                            "+2.1%",
                            _GAIN,
                            "week",
                            body="<p>Semiconductor strength led the advance.</p>",
                        ),
                        Card(
                            "Energy",
                            "-0.7%",
                            _LOSS,
                            "week",
                            body="<p>Crude gave back the prior week's gain.</p>",
                        ),
                    ],
                    orientation=CardOrientation.VERTICAL,
                    subtitle="Relative performance",
                ),
            )
        )
        # DataTable, with per-cell colours.
        .section(
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
                    as_of="24 August 2026",
                    subtitle="Long-short, gross of costs",
                ),
            )
        )
        # ChartBlock — attached, so the fixture also exercises Email.assets().
        .section(
            FullWidth(
                title="Cumulative Performance",
                content=ChartBlock(
                    EmailImage.attached(_CHART_PNG, alt="Cumulative factor performance", width=320),
                    source="Hermes Research",
                    subtitle="Indexed to 100",
                ),
            )
        )
        # TwoColumn — all three ratios.
        .section(
            TwoColumn(
                ratio=TwoColumnRatio.EQUAL,
                title="Equal Columns",
                left=TextBlock("<p>The left half of a 50-50 split.</p>"),
                right=TextBlock("<p>The right half of a 50-50 split.</p>"),
            )
        )
        .section(
            TwoColumn(
                ratio=TwoColumnRatio.NARROW_WIDE,
                title="Narrow then Wide",
                highlight=True,
                left=ImageBlock(
                    EmailImage.attached(_THUMB_PNG, alt="Thumbnail", width=96),
                    caption="A 30% column",
                    align=ImageAlign.LEFT,
                ),
                right=TextBlock("<p>Commentary occupying the wider 70% column.</p>"),
            )
        )
        .section(
            TwoColumn(
                ratio=TwoColumnRatio.WIDE_NARROW,
                title="Wide then Narrow",
                left=TextBlock("<p>Commentary occupying the wider 70% column.</p>"),
                right=AuthorBlock(
                    "A. Analyst",
                    job_title="Head of Research",
                    email="research@example.com",
                ),
            )
        )
        # ThreeColumn — all four ratios.
        .section(
            ThreeColumn(
                ratio=ThreeColumnRatio.EQUAL,
                title="Three Equal",
                left=TextBlock("<p>First third.</p>"),
                center=TextBlock("<p>Second third.</p>"),
                right=TextBlock("<p>Final third.</p>"),
            )
        )
        .section(
            ThreeColumn(
                ratio=ThreeColumnRatio.WIDE_LEFT,
                title="Wide Left",
                left=TextBlock("<p>The 50% column.</p>"),
                center=TextBlock("<p>Quarter.</p>"),
                right=TextBlock("<p>Quarter.</p>"),
            )
        )
        .section(
            ThreeColumn(
                ratio=ThreeColumnRatio.WIDE_CENTER,
                title="Wide Centre",
                left=TextBlock("<p>Quarter.</p>"),
                center=TextBlock("<p>The 50% column.</p>"),
                right=TextBlock("<p>Quarter.</p>"),
            )
        )
        .section(
            ThreeColumn(
                ratio=ThreeColumnRatio.WIDE_RIGHT,
                title="Wide Right",
                left=TextBlock("<p>Quarter.</p>"),
                center=TextBlock("<p>Quarter.</p>"),
                right=TextBlock("<p>The 50% column.</p>"),
            )
        )
        # NumberedList.
        .section(
            FullWidth(
                title="What We Are Watching",
                content=NumberedList(
                    [
                        NumberedItem(
                            "01", "Inflation prints", "<p>Core services remain sticky.</p>"
                        ),
                        NumberedItem("02", "Earnings revisions", "<p>Breadth is narrowing.</p>"),
                        NumberedItem("03", "Positioning", "<p>Futures length is extended.</p>"),
                    ],
                    subtitle="Three themes into next week",
                ),
            )
        )
        .build()
    )
