"""
Print typography (#385), shared by the email and the US Letter brief.

A three-sheet product brief for a fictional fund: a masthead in display
capitals on a dark band (#392), a justified overview (#394), a chart and a
returns table each with a qualifier under its subtitle (#395), a reading-size
note with a fine-print section after it on the same sheet, and a sheet of
disclosures in fine print (#393), all in a house typeface the PDF embeds
(#391). The email takes every setting and degrades each as `design-axes.md`
states.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder import (
    ChartBlock,
    Container,
    DataTable,
    FactList,
    FigureGrid,
    FullWidth,
    ImageBlock,
    TextBlock,
    TwoColumn,
)
from pyhermes.builder.images import EmailImage
from pyhermes.builder.models import Column, TableRow
from pyhermes.builder.typography import DEFAULT_FONTS, FontStack, FontTheme

from ._png import solid_png

_FONTS = Path(__file__).parent / "fonts"

#: The house face: Specimen Condensed, a renamed DejaVu Sans no machine has installed.
HOUSE = FontStack(
    "Specimen Condensed",
    "Arial",
    "sans-serif",
    files={
        "400": _FONTS / "SpecimenCondensed-Regular.ttf",
        "700": _FONTS / "SpecimenCondensed-Bold.ttf",
    },
)

#: The brief's faces: the house face for structure and chrome, the serif kept for prose.
FONTS: FontTheme = DEFAULT_FONTS.derive(heading=HOUSE, label=HOUSE)

_CHART_PNG = solid_png(600, 160, (44, 62, 80))
_PANEL_PNG = solid_png(300, 110, (91, 138, 154))

_OVERVIEW = (
    "<p>The Meridian Broad Market Fund holds every large and mid-sized company in "
    "its index, weighted by the value of the shares the public can buy, and "
    "rebalances each quarter. It is built to be held for a long time at a low "
    "cost, with distributions paid quarterly and reinvested by default.</p>"
    "<p>Turnover is low because the index changes slowly, and the fund lends a "
    "small share of its holdings against collateral, returning the income to "
    "holders after the agent's fee.</p>"
)

#: Ten paragraphs of fictional disclosure copy, the sheet a brief closes on.
DISCLOSURES = [
    "This brief is issued for information only by a fictional manager. It is not an "
    "offer to buy or sell any security, nor a solicitation of one, and it takes no "
    "account of any reader's objectives, circumstances or needs.",
    "Past performance is not a reliable indicator of future results. The value of an "
    "investment and the income from it can fall as well as rise, and investors may get "
    "back less than they invested, in particular over a short holding period.",
    "Returns are shown net of the ongoing charge, in US dollars, with income "
    "reinvested. Returns to an investor in another currency may rise or fall with "
    "exchange rates, and are not hedged back to that currency by the fund.",
    "Index returns are shown for comparison only. An index is not managed, bears no "
    "costs, holds no cash and cannot be invested in directly, so a fund that tracks one "
    "will trail it by about its costs over time.",
    "The fund may lend securities. Lending carries the risk that a borrower fails to "
    "return them and that the collateral held against them falls short of their value "
    "when they must be bought back in the market.",
    "Holdings and weights are as of the date shown and change over time. They are not "
    "a recommendation to buy or sell any security named, and the fund may no longer "
    "hold a security by the time this brief is read.",
    "Distributions are not guaranteed, and a distribution may be paid in part from "
    "capital, which reduces what is left invested and the income it can earn in later "
    "periods. The tax treatment of a distribution depends on the holder.",
    "The fund's prospectus and key information document describe its risks, costs and "
    "terms in full, and should be read before investing. Both are available in English "
    "from the manager on request, free of charge.",
    "Shares are bought and sold at market price, which may differ from the fund's net "
    "asset value, and brokerage commissions and the spread between the bid and the offer "
    "reduce the return an investor receives.",
    "Every name, figure and date in this brief is fictional, written to exercise a "
    "document's layout in print. None of it describes a real fund, a real manager or a "
    "real market, and none of it should be relied on.",
]


def sections() -> list[Container]:
    """The sections both fixtures render, in order."""
    return [
        FullWidth(
            title="Meridian Broad Market Fund",
            title_size="display",
            title_case="upper",
            kicker="Product brief",
            background_color="#1B2A3A",
            content=TextBlock(
                "<p>Low-cost exposure to the whole US equity market, in one holding.</p>"
            ),
        ),
        TwoColumn(
            title="Overview",
            align="justify",
            left=TextBlock(_OVERVIEW, align="justify"),
            right=FactList(
                {
                    "Ticker": "MBMF",
                    "Inception": "12 March 2019",
                    "Ongoing charge": "0.04%",
                    "Holdings": "3,612",
                    "Distributions": "Quarterly",
                }
            ),
        ),
        FullWidth(
            title="Performance",
            content=ChartBlock(
                EmailImage.attached(_CHART_PNG, alt="Growth of 10,000 since inception", width=600),
                subtitle="Growth of 10,000 invested at launch",
                qualifier="Total return, USD, net of fees, March 2019 to September 2026",
                source="Fictional data",
                caption="Growth of an investment",
                label="Exhibit",
            ),
        ),
        FullWidth(
            title="Calendar returns",
            content=DataTable(
                [
                    Column("Period", kind="text"),
                    Column("Fund", kind="numeric"),
                    Column("Index", kind="numeric"),
                ],
                [
                    TableRow(["1 year", "18.2%", "18.3%"]),
                    TableRow(["3 years", "9.6%", "9.7%"]),
                    TableRow(["5 years", "13.1%", "13.2%"]),
                    TableRow(["Since launch", "12.4%", "12.5%"]),
                ],
                subtitle="Annualised returns to the end of the quarter",
                qualifier="Net of fees, in USD, at net asset value",
                caption="Returns by period",
                label="Exhibit",
                source="Fictional data",
            ),
        ),
        TwoColumn(
            title="Portfolio",
            left=ImageBlock(
                EmailImage.attached(_PANEL_PNG, alt="Sector weights", width=300),
                subtitle="Sector weights",
                qualifier="Percent of net assets",
            ),
            right=FigureGrid(
                [
                    ImageBlock(
                        EmailImage.attached(_PANEL_PNG, alt="Large caps", width=300),
                        subtitle="Large",
                    ),
                    ImageBlock(
                        EmailImage.attached(_PANEL_PNG, alt="Mid caps", width=300),
                        subtitle="Mid",
                    ),
                ],
                subtitle="Weights by size",
                qualifier="Percent of net assets, by market value",
                columns=1,
            ),
        ),
        FullWidth(
            title="How to read this brief",
            content=TextBlock(
                "<p>Returns are net of the ongoing charge. The notes that follow are set in "
                "fine print, as a brief's are, beside this reading-size note.</p>"
            ),
        ),
        FullWidth(
            title="Important information",
            type_size="fine",
            align="justify",
            keep_together=True,
            content=TextBlock("".join(f"<p>{line}</p>" for line in DISCLOSURES)),
        ),
    ]
