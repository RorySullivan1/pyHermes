"""
Organising content (#334), shared by the email and the paged fixture.

Every object epic #329 added, each away from its default: fact lists in one,
two and three columns, one of them with toned figures on a dark band; a
six-event timeline holding every state; a three-across teaser list with
thumbnails and tags, and a one-column one beside it; and kickers on a full
width title, a split title and a dark band's. Both media build the same
sections, so each golden pins what its own medium makes of them.
"""

from __future__ import annotations

from pyhermes.builder import (
    Container,
    EmailImage,
    Event,
    FactList,
    FullWidth,
    Teaser,
    TeaserList,
    TextBlock,
    Timeline,
    TwoColumn,
)
from pyhermes.builder.formats import pct
from pyhermes.builder.models import Cell

from ._png import solid_png

#: The fund's facts, in the order a factsheet prints them.
FACTS = {
    "Inception": "12 March 2019",
    "Fund size": "GBP 1.24bn",
    "ISIN": "GB00B1YW4409",
    "Benchmark": "FTSE Actuaries Gilts",
    "Ongoing charge": "0.45%",
    "Dealing": "Daily, 12:00 UK",
}

#: Six events, so every state shows and the rule joins five gaps.
EVENTS = [
    Event("2 Oct", "Quarter-end review", "Positioning rolled into Q4.", state="done"),
    Event("9 Oct", "Gilt auction", "Long-dated supply, 30-year.", state="done"),
    Event("14 Oct", "UK CPI", "September print; the services line matters most.", state="next"),
    Event("29 Oct", "FOMC", "A hold is priced; the dots are not."),
    Event("6 Nov", "Bank of England", "Decision and the Monetary Policy Report."),
    Event("10 Dec", "ECB", "Last meeting of the year."),
]


def _thumb(rgb: tuple[int, int, int], alt: str) -> EmailImage:
    return EmailImage.attached(solid_png(360, 200, rgb), alt=alt, width=180)


#: Three pieces of further reading, each with a thumbnail.
TEASERS = [
    Teaser(
        "The long end reprices",
        "https://example.com/research/long-end",
        "2 Oct 2026",
        "Term premium is back, and the curve is steepening for the right reasons.",
        image=_thumb((91, 138, 154), "A curve steepening"),
        tags=["Rates", "Macro"],
    ),
    Teaser(
        "Credit at the tights",
        "https://example.com/research/credit",
        "28 Sep 2026",
        "Why we still prefer quality over carry into year end.",
        image=_thumb((44, 62, 80), "Spreads against their range"),
        tags=["Credit"],
    ),
    Teaser(
        "The dollar smile",
        "https://example.com/research/dollar",
        "21 Sep 2026",
        "Three regimes, and which one we are in.",
        image=_thumb((184, 84, 80), "The dollar against growth"),
    ),
]


def sections() -> list[Container]:
    """The sections both fixtures render, in order."""
    return [
        FullWidth(
            title="Fund facts",
            kicker="Gilt Fund · Factsheet",
            content=FactList(FACTS, columns=2),
        ),
        TwoColumn(
            (3, 2),
            title="The calendar",
            kicker="Markets · Week 40",
            left=Timeline(EVENTS, subtitle="What we watch, and what has passed"),
            right=FactList(
                [
                    ("Bank Rate", "4.00%"),
                    ("10Y gilt", Cell.from_number(0.0421, pct, tone="neutral")),
                    ("Since last", Cell("+18 bps", tone="negative")),
                ],
                title="Where we stand",
            ),
        ),
        FullWidth(
            title="By the numbers",
            kicker="Performance",
            background_color="#22313F",
            content=FactList(
                {
                    "1 month": Cell("+0.8%", tone="positive"),
                    "3 months": Cell("-1.2%", tone="negative"),
                    "1 year": Cell("+3.4%", tone="positive"),
                    "3 years": 4.1,
                    "5 years": 2.7,
                    "Since launch": 2.2,
                },
                columns=3,
                value_format=lambda value: f"{value:.1f}% p.a.",
            ),
        ),
        FullWidth(
            title="Further reading",
            kicker="Research",
            content=TeaserList(TEASERS, columns=3, subtitle="From the desk this month"),
        ),
        FullWidth(
            title="Also this week",
            content=TeaserList(TEASERS[:2]),
        ),
        FullWidth(
            content=TextBlock("<p>Past performance is not a guide to future returns.</p>"),
        ),
    ]
