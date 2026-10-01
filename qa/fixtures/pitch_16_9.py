"""
A 16:9 pitch deck: the deck medium's gallery fixture (#301).

A title slide, an agenda, two parts each opened by a divider, a KPI slide, a
table slide, a chart slide with notes, a two-column slide and the closing
disclosures. Each slide opens on copy no other carries, so a test can find it
on its sheet. Every ``Slide``, ``DividerSlide``, ``TitleSlide`` and
``ClosingSlide`` field is set somewhere away from its default, per standing
rule 9, and every slide fits its body.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pyhermes.builder import (
    CardGroup,
    ChartBlock,
    Contents,
    DataTable,
    FullWidth,
    TextBlock,
    TwoColumn,
)
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
)

#: The notes on the chart slide, and a sentinel no projection but the notes may carry.
CHART_NOTES = (
    "Walk through the term premium first, then the hedge. The sentinel "
    "ZEBRANOTES7 marks what only the presenter reads."
)


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
                        KpiItem("10Y gilt", "4.21%", sublabel="+18 bps"),
                        KpiItem("2s10s", "38 bps", sublabel="+9 bps"),
                        KpiItem("Breakeven", "3.42%", sublabel="-4 bps"),
                        KpiItem("Term premium", "61 bps", sublabel="+12 bps"),
                    ]
                )
            )
        ],
        TITLES[2],
    )
    deck.add_slide(
        [
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
                )
            )
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
    deck.add_divider(TITLES[5])
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
    )
    return deck
