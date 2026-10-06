"""
Brand tones (#387), shared by the email and the paged fixture.

A theme that declares three brand tones beside the semantic three, and every
object that takes a tone naming one: a fact box and a framed box beside an
untoned one, a black ticker chip and a gold one filled solid (#388), badged and
toned cards, a hero figure, a table whose cells and status dots are in brand
tones, a bar list and a key. No semantic token is repainted, so a gain is still
green beside the brand's gold. The verdict box, the sleeves table and the sector
section are framed dashed, and the table's label column is ruled off (#390).
"""

from __future__ import annotations

from pyhermes.builder import (
    Badge,
    BarList,
    Callout,
    CardGroup,
    Column,
    Container,
    DataTable,
    FullWidth,
    HeroStat,
    Legend,
    TextBlock,
    TwoColumn,
)
from pyhermes.builder.exhibits import LegendEntry
from pyhermes.builder.glance import BarItem
from pyhermes.builder.models import Cell, KpiItem, TableRow
from pyhermes.builder.theming import DEFAULT_THEME

#: The classic theme with a brand's gold, sky and ink, its semantic tones untouched.
THEME = DEFAULT_THEME.derive(tones={"brand": "#B8860B", "sky": "#0077A8", "ink": "#111111"})

#: Each sleeve a holding sits in, and the tone its dot is drawn in.
SLEEVES = {"Core": "brand", "Satellite": "sky", "Hedge": "neutral"}


def sections() -> list[Container]:
    """The sections both fixtures render, in order."""
    return [
        FullWidth(
            title="Fund facts",
            content=Callout(
                TextBlock(
                    "<p>A broad US equity fund tracking 500 large companies, with a "
                    "0.03% expense ratio and quarterly distributions.</p>"
                ),
                tone="brand",
                label="At a glance",
            ),
        ),
        TwoColumn(
            left=Callout(
                TextBlock("<p>Low-cost core exposure for a long holding period.</p>"),
                tone="sky",
                label="Who it suits",
                frame="dashed",
            ),
            right=Callout(
                TextBlock("<p>Concentrated in its ten largest names.</p>"),
                label="Watch",
            ),
        ),
        TwoColumn(
            left=Callout(
                TextBlock("<p><strong>HRMF</strong> on NYSE Arca</p>"),
                tone="ink",
                label="Ticker",
                fill="solid",
            ),
            right=Callout(
                TextBlock("<p>12 March 2019</p>"), tone="brand", label="Inception", fill="solid"
            ),
        ),
        FullWidth(
            title="The fund in numbers",
            badge=Badge("House view", "brand"),
            content=CardGroup(
                [
                    KpiItem("Assets", "$412bn", tone="brand", badge=Badge("Flagship", "sky")),
                    KpiItem("Holdings", "503", tone="sky"),
                    KpiItem("1Y return", "+18.2%", tone="positive"),
                ]
            ),
        ),
        FullWidth(content=HeroStat("0.03%", "Expense ratio", tone="brand")),
        FullWidth(
            title="Sleeves",
            content=DataTable(
                [
                    Column("Holding", rule_after=True),
                    Column("Sleeve", kind="status", statuses=SLEEVES),
                    "Weight",
                ],
                [
                    TableRow(["US large cap", "Core", Cell("62%", tone="brand")]),
                    TableRow(["Global small cap", "Satellite", Cell("23%", tone="sky")]),
                    TableRow(["Treasury futures", "Hedge", "15%"]),
                ],
                frame="dashed",
            ),
        ),
        FullWidth(
            title="Sector weights",
            border=True,
            frame="dashed",
            content=BarList(
                [
                    BarItem("Technology", 31, tone="brand"),
                    BarItem("Financials", 13, tone="sky"),
                    BarItem("Health care", 11),
                ],
                value_format=lambda value: f"{value}%",
            ),
        ),
        FullWidth(
            content=Legend(
                [
                    LegendEntry("Fund", tone="brand"),
                    LegendEntry("Benchmark", tone="sky"),
                    LegendEntry("Excess", tone="positive"),
                ]
            )
        ),
    ]
