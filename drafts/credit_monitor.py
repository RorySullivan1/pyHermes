"""A credit-risk monitor — the second report, exercising what the first did not.

`factor_review` used the flat ``MinimalBanner``, the default theme, and a plain
data table. This one deliberately takes the other paths: the full VML ``Banner``
with a background image and a logo, all three design axes off their defaults
(``slate`` / ``compact`` / ``modern``), a ``ThreeColumn`` split, subhead rows
grouping the table, cell backgrounds carrying a heat scale, and a caller-supplied
``LinkRow`` in the footer.

The banner path is the one #147 fixed, so this is also the first report to render
a logo through it rather than around it.
"""

from __future__ import annotations

from drafts._chart import bar_chart, sparkline_strip
from pyhermes.builder import (
    Banner,
    BannerPalette,
    Card,
    CardGroup,
    ChartBlock,
    Column,
    ContactBlock,
    DataTable,
    Email,
    EmailBuilder,
    EmailImage,
    Footer,
    FullWidth,
    ImageBlock,
    TableRow,
    TextBlock,
    ThreeColumn,
)
from pyhermes.builder.models import Cell, FooterLink, LinkRow

#: Weekly OAS change in basis points by rating bucket, oldest first. The three
#: series are plotted as small multiples and quoted in the copy.
SPREAD_SERIES = [
    [112, 118, 121, 116, 124, 131, 128],  # IG
    [340, 352, 361, 349, 372, 398, 391],  # HY
    [604, 618, 641, 633, 672, 715, 704],  # CCC
]

#: Net rating migrations by month, negative meaning net downgrades.
MIGRATIONS = [4, 2, -3, -6, -2, -9, -12, -7, -14]


def _logo() -> EmailImage:
    """A 96px mark. Hosted rather than attached, so the two strategies both appear."""
    return EmailImage.hosted(
        "https://cdn.example.com/hermes-mark.png", alt="Hermes Research", width=96
    )


def _metadata() -> dict[str, str]:
    return {
        "email_subject": "Credit Monitor — spreads widen a third straight week",
        "preheader_text": "IG +7bp, HY +26bp on the week; CCC leads and migrations turn.",
        "firm_name": "Hermes Research",
        "campaign_name": "credit-monitor",
        "department": "Credit Strategy",
        "date_range": "Week ending 2 October 2026",
        "issue_label": "Week 40",
        "language": "en-GB",
        "theme": "slate",
        "size_theme": "compact",
        "font_theme": "modern",
        "header_disclaimer": (
            "For professional investors only. Spreads are option-adjusted and "
            "sourced from index composites."
        ),
        "current_year": "2026",
        "unsubscribe_url": "https://example.com/unsubscribe",
        "view_in_browser_url": "https://example.com/archive/credit-week-40",
    }


def _heat(text: str, level: str) -> Cell:
    """A table cell carrying a heat background — the caller's claim about a figure."""
    grounds = {"hot": "#F2DEDC", "warm": "#F7EFE4", "cool": "#E4EDE6"}
    return Cell(text, background=grounds[level])


def build(template_dir=None) -> Email:
    spreads = EmailImage.attached(
        sparkline_strip(SPREAD_SERIES),
        alt="Weekly option-adjusted spread by rating bucket: IG, HY and CCC",
        width=560,
        filename="spreads.png",
    )
    migrations = EmailImage.attached(
        bar_chart(MIGRATIONS),
        alt="Net rating migrations by month; negative bars are net downgrades",
        width=560,
        filename="migrations.png",
    )

    return (
        EmailBuilder(template_dir=template_dir)
        .metadata(_metadata())
        .banner(
            Banner(
                # `alt` is required at construction, so a decorative backdrop
                # cannot take the empty alt that would let a screen reader skip
                # it. Described rather than suppressed — see the draft docstring.
                background_image_url=EmailImage.hosted(
                    "https://cdn.example.com/credit-banner.jpg",
                    alt="Abstract dark banner backdrop",
                    width=680,
                ),
                logo_url=_logo(),
                title="Credit Monitor",
                subtitle="Weekly spread and migration review",
                palette=BannerPalette(accent="#C9A227"),
            )
        )
        .section(
            FullWidth(
                title="The Week",
                highlight=True,
                content=CardGroup(
                    [
                        Card("IG OAS", "128bp", "#B85450", "+7bp on the week"),
                        Card("HY OAS", "391bp", "#B85450", "+26bp, third weekly widening"),
                        Card("CCC OAS", "704bp", "#B85450", "+32bp, leading the move"),
                    ],
                    orientation="horizontal",
                ),
            )
        )
        .section(
            FullWidth(
                title="Spreads by Bucket",
                content=ChartBlock(
                    spreads,
                    alt_text="Weekly option-adjusted spread by rating bucket",
                    source="Index composites. Option-adjusted, weekly closes.",
                    subtitle="IG, HY and CCC — each scaled to its own range",
                    width=560,
                ),
            )
        )
        .section(
            FullWidth(
                title="Where the Widening Sits",
                content=DataTable(
                    headers=[
                        Column("Sector", kind="text"),
                        Column("OAS", kind="numeric"),
                        Column("1W", kind="numeric"),
                        Column("3M", kind="numeric"),
                        Column("Net migr.", kind="numeric"),
                    ],
                    rows=[
                        TableRow(["Investment grade"], kind="subhead"),
                        TableRow(["Financials", "119bp", _heat("+9bp", "warm"), "+21bp", "-2"]),
                        TableRow(["Utilities", "104bp", _heat("+3bp", "cool"), "+8bp", "0"]),
                        TableRow(["Real estate", "168bp", _heat("+18bp", "hot"), "+54bp", "-5"]),
                        TableRow(["High yield"], kind="subhead"),
                        TableRow(["Energy", "402bp", _heat("+31bp", "hot"), "+88bp", "-6"]),
                        TableRow(["Retail", "455bp", _heat("+24bp", "hot"), "+71bp", "-4"]),
                        TableRow(["Healthcare", "338bp", _heat("+11bp", "warm"), "+29bp", "-1"]),
                        TableRow(["Composite", "391bp", "+26bp", "+63bp", "-18"], kind="total"),
                    ],
                    caption="Option-adjusted spread and net rating migrations by sector",
                    source="Index composites",
                    as_of="2 October 2026",
                ),
            )
        )
        .section(
            ThreeColumn(
                ratio="33-33-33",
                title="Read-Through",
                left=TextBlock(
                    "<p><strong>Real estate</strong> is the IG outlier at +18bp, and the "
                    "refinancing wall is the reason rather than fundamentals.</p>",
                    subtitle="Investment grade",
                ),
                center=TextBlock(
                    "<p><strong>Energy</strong> leads HY at +31bp on a move that is "
                    "commodity-led and, so far, orderly.</p>",
                    subtitle="High yield",
                ),
                right=TextBlock(
                    "<p><strong>CCC</strong> at +32bp is the tell: the tail is repricing "
                    "faster than the index.</p>",
                    subtitle="Distressed",
                ),
            )
        )
        .section(
            FullWidth(
                title="Migrations Turn Negative",
                content=ImageBlock(
                    migrations,
                    alt_text="Net rating migrations by month, negative from March onward",
                    caption="Net migrations by month. Below the line is net downgrades.",
                    width=560,
                ),
            )
        )
        .section(
            FullWidth(
                content=ContactBlock(
                    heading="Questions on the sector detail?",
                    description=(
                        "The full sector table and constituent-level moves are in the "
                        "weekly appendix."
                    ),
                    cta_label="Request the appendix",
                    cta_url="mailto:credit@example.com",
                )
            )
        )
        .footer(
            Footer(
                border=True,
                link_row=LinkRow(
                    copyright="&copy; 2026 Hermes Research",
                    links=[
                        FooterLink("Methodology", "https://example.com/methodology"),
                        FooterLink("Archive", "https://example.com/archive"),
                        FooterLink("Contact", "mailto:credit@example.com"),
                    ],
                ),
                disclaimer=(
                    "<p>Spreads are option-adjusted index composites. This document is "
                    "for professional investors only and is not investment advice.</p>"
                ),
            )
        )
        .build()
    )
