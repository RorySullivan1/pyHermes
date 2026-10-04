"""
Data at a glance (#323), shared by the email and the paged fixture.

Every object epic #318 added, each at a setting away from its default: KPI
changes drawn with an up, a down and a flat arrow over a trend, a hero figure
centred and on a dark band, a ten-item ranked list and a diverging one, a
rising, a falling and a flat sparkline, and a table whose change column carries
arrows beside a sparkline column. Both media build the same sections, so each
golden pins what its own medium makes of them.
"""

from __future__ import annotations

from functools import partial

from pyhermes.builder import (
    BarItem,
    BarList,
    CardGroup,
    Column,
    Container,
    DataTable,
    FullWidth,
    HeroStat,
    Sparkline,
    Stack,
    ThreeColumn,
)
from pyhermes.builder.formats import bps, number, pct
from pyhermes.builder.models import KpiItem, TableRow

_SIGNED = partial(pct, dp=1, sign=True)
_LEVEL = partial(number, dp=2)

#: Eight quarter-end ten-year yields, in percent: up for a third quarter.
RISING = [3.62, 3.81, 3.66, 3.88, 3.97, 4.02, 4.11, 4.21]
#: The VIX over the same quarters: down.
FALLING = [21.4, 19.9, 20.3, 18.7, 17.9, 16.8, 15.4, 14.3]
#: The policy rate: held throughout.
FLAT = [4.25] * 8


def _bps(value: float) -> str:
    return bps(value / 10_000)


def sections() -> list[Container]:
    """The sections, in reading order. Deterministic: same objects' bytes every call."""
    return [
        FullWidth(
            CardGroup(
                [
                    # A rising yield is bad news for the book: up, and negative.
                    KpiItem.from_number(
                        "10Y gilt",
                        0.0421,
                        partial(pct, dp=2),
                        change=0.0018,
                        change_fmt=bps,
                        good="down",
                        arrow=True,
                        trend=[value / 100 for value in RISING],
                    ),
                    # A falling VIX is good news: down, and positive.
                    KpiItem.from_number(
                        "VIX",
                        14.3,
                        partial(number, dp=1),
                        change=-0.6,
                        good="down",
                        arrow=True,
                        trend=FALLING,
                    ),
                    KpiItem.from_number(
                        "Bank Rate",
                        0.0425,
                        partial(pct, dp=2),
                        change=0.0,
                        change_fmt=bps,
                        arrow=True,
                        trend=[value / 100 for value in FLAT],
                    ),
                ]
            ),
            title="Rates at a glance",
        ),
        FullWidth(
            HeroStat.from_number(
                "2s10s",
                38,
                lambda value: f"{value} bps",
                context="steepest since 2022",
                align="center",
            ),
            title="The lead figure",
        ),
        FullWidth(
            BarList(
                [
                    ("UK Treasury 4.25% 2034", 0.081),
                    ("UK Treasury 3.75% 2038", 0.074),
                    ("UK Treasury 4.5% 2042", 0.066),
                    ("UK Treasury 0.125% IL 2036", 0.058),
                    ("UK Treasury 4.0% 2060", 0.051),
                    ("UK Treasury 1.5% 2047", 0.043),
                    ("UK Treasury 3.5% 2045", 0.039),
                    ("UK Treasury 4.75% 2030", 0.032),
                    ("UK Treasury 0.625% 2050", 0.027),
                    ("UK Treasury 1.25% 2051", 0.019),
                ],
                value_format=partial(pct, dp=1),
                title="Top ten holdings, by weight",
                subtitle="The long end carries the book",
            ),
            title="Where the book sits",
        ),
        FullWidth(
            BarList(
                [
                    ("Duration", 0.0042),
                    ("Curve", 0.0018),
                    BarItem("Inflation", 0.0006, tone="neutral"),
                    ("Credit", -0.0009),
                    ("Currency", -0.0021),
                ],
                value_format=partial(pct, dp=2, sign=True),
                tone="auto",
                diverging=True,
                title="Contribution to return, quarter",
            ),
            title="What earned the quarter",
        ),
        ThreeColumn(
            "33-33-33",
            left=Sparkline(
                [value / 100 for value in RISING],
                tone="auto",
                value_format=partial(pct, dp=2),
                subtitle="10Y gilt, two years",
            ),
            center=Sparkline(
                FALLING,
                tone="positive",
                value_format=partial(number, dp=1),
                subtitle="VIX, two years",
            ),
            right=Sparkline(
                [value / 100 for value in FLAT],
                highlight_last=False,
                value_format=partial(pct, dp=2),
                subtitle="Bank Rate, two years",
            ),
            title="Three series, three shapes",
        ),
        FullWidth(
            DataTable(
                [
                    "Tenor",
                    Column("Yield", format=partial(pct, dp=2)),
                    Column("Change", format=_bps, tone="auto", arrow=True),
                    Column("Two years", kind="sparkline", format=_LEVEL, tone="auto"),
                ],
                [
                    TableRow(["2Y", 0.0383, 0, [3.86, 3.91, 3.84, 3.88, 3.83, 3.83]]),
                    TableRow(["10Y", 0.0421, 18, [4.00, 4.02, 4.11, 4.15, 4.18, 4.21]]),
                    TableRow(["30Y", 0.0478, -4, [4.90, 4.88, 4.85, 4.86, 4.80, 4.78]]),
                ],
                source="Hermes Research",
                caption="Gilt yields and their change on the quarter",
            ),
            title="The curve, tenor by tenor",
        ),
        FullWidth(
            Stack(
                [
                    HeroStat(
                        "61 bps",
                        "Term premium",
                        "Most of the long end's move this quarter",
                        align="left",
                    ),
                    HeroStat("+12 bps", "On the quarter", align="left"),
                ]
            ),
            title="On a dark band",
            background_color="#22313F",
        ),
    ]
