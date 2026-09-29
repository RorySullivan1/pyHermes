"""A quarterly factor-attribution review — the analytical report as a real email.

Written against the public API only, the way a caller would, to find out what the
library makes easy and what it makes awkward. Built for **Outlook** specifically:
``MinimalBanner`` rather than ``Banner`` so no VML masthead is involved, every
image carrying an explicit width, and no construct the ``qa/lint.py`` Outlook
rules reject.
"""

from __future__ import annotations

from drafts._chart import bar_chart
from pyhermes.builder import (
    AuthorBlock,
    Card,
    CardGroup,
    ChartBlock,
    Column,
    DataTable,
    Email,
    EmailBuilder,
    EmailImage,
    Footer,
    FullWidth,
    MinimalBanner,
    NumberedList,
    TableRow,
    TextBlock,
    TwoColumn,
)
from pyhermes.builder.models import Cell, NumberedItem

#: Monthly long-short factor spread, in percent, most recent last. Drawn as the
#: chart image and quoted in the copy, so the two cannot disagree.
MONTHLY_SPREAD = [2.4, 1.1, -0.8, 3.2, -1.9, 0.6, 2.8, 1.4, -0.3]


def _metadata() -> dict[str, str]:
    return {
        "email_subject": "Factor Review — Q3 2026 attribution and positioning",
        "preheader_text": "Value led on a 7.4% spread; momentum gave back half of Q2's gain.",
        "firm_name": "Hermes Research",
        "campaign_name": "factor-review-q3-2026",
        "department": "Quantitative Strategy",
        "date_range": "Quarter ending 30 September 2026",
        "issue_label": "Q3 2026",
        "header_disclaimer": (
            "For professional investors only. Past performance is not a guide to future returns."
        ),
        "current_year": "2026",
        "unsubscribe_url": "https://example.com/unsubscribe",
        "view_in_browser_url": "https://example.com/archive/factor-review-q3-2026",
    }


def build(template_dir=None) -> Email:
    chart = EmailImage.attached(
        bar_chart(MONTHLY_SPREAD),
        alt="Monthly long-short factor spread, in percent, over the last nine months",
        width=560,
        filename="factor-spread.png",
    )

    return (
        EmailBuilder(template_dir=template_dir)
        .metadata(_metadata())
        .banner(MinimalBanner(title="Factor Review", subtitle="Quantitative Strategy"))
        # 1. The headline numbers, first screen.
        .section(
            FullWidth(
                title="Quarter at a Glance",
                highlight=True,
                content=CardGroup(
                    [
                        Card("Value", "+7.4%", "#4A7C59", "long-short spread"),
                        Card("Momentum", "-2.1%", "#B85450", "gave back half of Q2"),
                        Card("Quality", "+3.6%", "#4A7C59", "third positive quarter"),
                    ],
                    orientation="horizontal",
                ),
            )
        )
        # 2. The thesis, in prose.
        .section(
            FullWidth(
                title="What Drove the Quarter",
                content=TextBlock(
                    "<p>Value's <strong>7.4% long-short spread</strong> was the quarter's "
                    "dominant contribution, and it came almost entirely from the short "
                    "book: expensive growth names de-rated through August as the rate "
                    "path repriced.</p>"
                    "<p>Momentum reversed sharply in the same window. The factor gave back "
                    "roughly half of its Q2 gain, which is the ordinary cost of a crowded "
                    "book meeting a fast rotation rather than a signal decay.</p>",
                    subtitle="Attribution is gross of costs and before financing",
                ),
            )
        )
        # 3. The chart, embedded rather than hosted.
        .section(
            FullWidth(
                title="Monthly Spread",
                content=ChartBlock(
                    chart,
                    alt_text="Monthly long-short factor spread over nine months",
                    source="Hermes Research. Gross of transaction costs.",
                    subtitle="Long-short spread by month, percent",
                    width=560,
                ),
            )
        )
        # 4. The numbers, as a real data table.
        .section(
            FullWidth(
                title="Attribution by Factor",
                content=DataTable(
                    headers=[
                        Column("Factor", kind="text"),
                        Column("Q3", kind="numeric"),
                        Column("YTD", kind="numeric"),
                        Column("Vol", kind="numeric"),
                        Column("Sharpe", kind="numeric"),
                    ],
                    rows=[
                        TableRow(
                            [
                                "Value",
                                Cell("+7.4%", color="#4A7C59"),
                                Cell("+14.2%", color="#4A7C59"),
                                "11.3%",
                                "1.26",
                            ]
                        ),
                        TableRow(
                            [
                                "Momentum",
                                Cell("-2.1%", color="#B85450"),
                                Cell("+6.8%", color="#4A7C59"),
                                "14.7%",
                                "0.46",
                            ]
                        ),
                        TableRow(
                            [
                                "Quality",
                                Cell("+3.6%", color="#4A7C59"),
                                Cell("+9.1%", color="#4A7C59"),
                                "8.2%",
                                "1.11",
                            ]
                        ),
                        TableRow(
                            [
                                "Low Volatility",
                                Cell("-0.4%", color="#B85450"),
                                Cell("+2.3%", color="#4A7C59"),
                                "6.9%",
                                "0.33",
                            ]
                        ),
                        TableRow(
                            ["Composite", "+2.1%", "+8.1%", "7.4%", "1.09"],
                            kind="total",
                        ),
                    ],
                    caption="Factor attribution, Q3 2026, gross of costs",
                    source="Hermes Research",
                    as_of="30 September 2026",
                ),
            )
        )
        # 5. A split: positioning against risk.
        .section(
            TwoColumn(
                ratio="50-50",
                title="Positioning and Risk",
                left=TextBlock(
                    "<p><strong>Adding to value.</strong> The spread widened without a "
                    "corresponding move in realised vol, which is the configuration the "
                    "book is sized for.</p>",
                    subtitle="Positioning",
                ),
                right=TextBlock(
                    "<p><strong>Trimming momentum.</strong> Crowding scores sit in the "
                    "ninth decile and the reversal has not fully unwound them.</p>",
                    subtitle="Risk",
                ),
            )
        )
        # 6. What we are watching, as an ordered list.
        .section(
            FullWidth(
                title="Into Q4",
                content=NumberedList(
                    [
                        NumberedItem(
                            "01",
                            "Rate path repricing",
                            "<p>A further 50bp of cuts priced out would extend the value "
                            "de-rating; the short book is positioned for it.</p>",
                        ),
                        NumberedItem(
                            "02",
                            "Momentum crowding",
                            "<p>We reduce further if decile-nine crowding persists into "
                            "November without a vol expansion.</p>",
                        ),
                        NumberedItem(
                            "03",
                            "Quality as ballast",
                            "<p>Three positive quarters at 8.2% vol; the allocation stays.</p>",
                        ),
                    ]
                ),
            )
        )
        .section(
            FullWidth(
                content=AuthorBlock(
                    name="Dr. Elena Marsh",
                    job_title="Head of Quantitative Strategy",
                    email="e.marsh@example.com",
                )
            )
        )
        .footer(
            Footer(
                border=True,
                disclaimer=(
                    "<p>This document is issued by Hermes Research for professional "
                    "investors only. Figures are gross of transaction costs and "
                    "financing. Past performance is not a guide to future returns.</p>"
                ),
            )
        )
        .build()
    )
