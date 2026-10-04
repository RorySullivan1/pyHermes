"""
A 16:9 pitch deck: the deck medium's gallery fixture (#301).

A title slide, an agenda, two parts each opened by a divider, a KPI slide, a
table slide (a measured paragraph over a table at 0.6 of the body), a chart
slide with notes, a two-column slide anchored middle, a slide laid out with a
sidebar (#366) and the closing disclosures. The title slide and the second
divider are anchored middle (#355). Each slide opens on copy no
other carries, so a test can find it on its sheet. Every ``Slide``,
``DividerSlide``, ``TitleSlide`` and ``ClosingSlide`` field is set somewhere
away from its default, per standing rule 9, and every slide fits its body.
"""

from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any

from pyhermes.builder import (
    BarList,
    CardGroup,
    ChartBlock,
    Contents,
    DataTable,
    FullWidth,
    HeroStat,
    TextBlock,
    TwoColumn,
)
from pyhermes.builder.formats import pct
from pyhermes.builder.images import EmailImage
from pyhermes.builder.models import KpiItem, TableRow
from pyhermes.deck import SLIDE_16_9, ClosingSlide, Deck, Slide, TitleSlide

from . import _paged
from ._png import solid_png

#: The firm's mark on the title slide: 160px displayed, 320 source pixels.
_LOGO_PNG = solid_png(320, 80, (44, 62, 80))

#: The chart: 560px displayed in a 60-40 split's wide column.
_CHART_PNG = solid_png(1120, 520, (91, 138, 154))

#: The title slide's ground, a pale wash the dark type reads on.
_GROUND_PNG = solid_png(640, 360, (238, 242, 245))

#: The title of each slide that has one, in order. The tests read these back
#: off the PDF, one sheet at a time.
TITLES: tuple[str, ...] = (
    "Agenda",
    "Where rates stand",
    "The quarter in four numbers",
    "Curve by tenor",
    "The term premium",
    "What we would do",
    "Two positions",
    "The view in brief",
    "The lead figure",
)

#: The table slide's lead-in: long enough that, uncapped, a line would cross the body.
MEASURED = (
    "The long end did the work this quarter. Ten-year yields rose eighteen basis points "
    "while the two-year barely moved, and the term premium explains most of the difference."
)

#: The notes on the chart slide, and a sentinel no projection but the notes may carry.
CHART_NOTES = (
    "Walk through the term premium first, then the hedge. The sentinel "
    "ZEBRANOTES7 marks what only the presenter reads."
)


_PCT = partial(pct, dp=2)


def _bps_change(value: float) -> str:
    return f"{value:+d} bps" if value else "0 bps"


def _bps_level(value: float) -> str:
    return f"{value} bps"


def facts() -> dict[str, Any]:
    """The paged gallery's facts, at the density a deck is read at."""
    return {**_paged.facts(), "size_theme": "presentation"}


def build(template_dir: Path | None = None) -> Deck:
    """Build the deck. Deterministic: same bytes every call."""
    deck = Deck(
        facts(),
        page=SLIDE_16_9,
        title_slide=TitleSlide(
            title="Rates, Projected",
            subtitle="A quarterly view of the gilt curve",
            logo_url=EmailImage.attached(_LOGO_PNG, alt="Hermes mark", width=160),
            logo_alt="Hermes Research",
            logo_width=140,
            background_image_url=EmailImage.attached(_GROUND_PNG, alt="Ground"),
            align="right",
            background_color="#EEF2F5",
            text_color="#22313F",
            valign="middle",
        ),
        closing_slide=ClosingSlide(heading="Important information", align="left"),
        template_dir=template_dir,
    )
    deck.add_slide(
        [FullWidth(content=Contents(subtitle="Two parts, five slides"))],
        TITLES[0],
        notes="Thirty seconds: say what each part answers.",
    )
    deck.add_divider(TITLES[1], subtitle="Levels, curve and premium", notes="Pause here.")
    deck.add_slide(
        [
            FullWidth(
                content=CardGroup(
                    [
                        # Each change drawn as an arrow in its own tone (#319).
                        KpiItem.from_number(
                            "10Y gilt", 0.0421, _PCT, change=18, change_fmt=_bps_change, arrow=True
                        ),
                        KpiItem.from_number(
                            "2s10s", 38, _bps_level, change=9, change_fmt=_bps_change, arrow=True
                        ),
                        KpiItem.from_number(
                            "Breakeven", 0.0342, _PCT, change=-4, change_fmt=_bps_change, arrow=True
                        ),
                        KpiItem.from_number(
                            "Term premium",
                            61,
                            _bps_level,
                            change=0,
                            change_fmt=_bps_change,
                            arrow=True,
                        ),
                    ]
                )
            )
        ],
        TITLES[2],
    )
    deck.add_slide(
        [
            # A paragraph across the whole body, capped at the standard measure (#358).
            FullWidth(content=TextBlock(f"<p>{MEASURED}</p>")),
            # A four-row table at a share of the body, centred by its section (#357).
            FullWidth(
                content=DataTable(
                    ["Tenor", "Yield", "Change (bps)", "Weight"],
                    [
                        TableRow(["2Y", "3.83%", "+9", "18%"]),
                        TableRow(["5Y", "3.97%", "+12", "27%"]),
                        TableRow(["10Y", "4.21%", "+18", "35%"]),
                        TableRow(["30Y", "4.78%", "+21", "20%"]),
                    ],
                    source="Hermes Research, as at quarter end",
                    width=0.6,
                ),
                align="center",
            ),
        ],
        TITLES[3],
        notes="The long end did the work; the front end barely moved.",
    )
    deck.add_slide(
        Slide(
            [
                TwoColumn(
                    "70-30",
                    left=ChartBlock(
                        EmailImage.attached(_CHART_PNG, alt="Term premium, ten years", width=560),
                        alt_text="Term premium, ten years",
                        source="Hermes Research",
                    ),
                    right=TextBlock(
                        "<p>The premium rose for a third quarter, and now explains most of "
                        "the move at the long end.</p>"
                    ),
                )
            ],
            title=TITLES[4],
            notes=CHART_NOTES,
            anchor="premium",
        )
    )
    deck.add_divider(TITLES[5], valign="middle")
    deck.add_slide(
        [
            TwoColumn(
                "50-50",
                left=TextBlock(
                    "<p><strong>Steepener.</strong> Own 30Y against 5Y, sized to the "
                    "premium's last move.</p>"
                ),
                right=TextBlock(
                    "<p><strong>Linker hedge.</strong> Hold breakevens through the next "
                    "two prints.</p>"
                ),
            )
        ],
        TITLES[6],
        background_color="#F4F1EA",
        align="center",
        # A short body set in the middle of the sheet (#355).
        valign="middle",
    )
    # A main area and a sidebar of facts (#366): Slide.layout away from its default.
    deck.add_slide(
        [
            FullWidth(
                content=TextBlock(
                    "<p>Rates have further to rise at the long end, and the premium is the "
                    "reason. The front end waits on the next two prints.</p>",
                    measure="full",
                ),
                title="Our view",
            )
        ],
        TITLES[7],
        layout="sidebar",
        side=[
            FullWidth(
                content=CardGroup(
                    [
                        KpiItem("10Y gilt", "4.21%", sublabel="+18 bps"),
                        KpiItem("Term premium", "61 bps", sublabel="+12 bps"),
                    ],
                    orientation="vertical",
                ),
                title="In figures",
                highlight=True,
            )
        ],
    )
    # One figure set alone beside what earned it (#322, #320): the statement the
    # deck-layouts epic's statement slide builds on.
    deck.add_slide(
        [
            TwoColumn(
                "50-50",
                left=HeroStat("38 bps", "2s10s", "The curve's steepest since 2022", align="center"),
                right=BarList(
                    [("Duration", 0.0042), ("Curve", 0.0018), ("Credit", -0.0009)],
                    value_format=partial(pct, dp=2, sign=True),
                    tone="auto",
                    diverging=True,
                    title="Contribution to return",
                ),
            )
        ],
        TITLES[8],
        valign="middle",
    )
    return deck
