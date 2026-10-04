"""
The deck layouts of #346, as a second 16:9 gallery deck beside ``pitch_16_9``.

A sourced slide whose source cites a reference listed on a later slide, a
full-bleed picture, a picture on each side of the copy, a statement slide,
divider agendas, and a footer counting ``N / total`` under a confidentiality
mark. Kept apart from ``pitch_16_9`` so that fixture's goldens prove every new
field renders byte for byte at its default (#353). Every slide fits its body.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder import Bibliography, Contents, DataTable, FullWidth, HeroStat, TextBlock
from pyhermes.builder.images import EmailImage
from pyhermes.builder.models import TableRow
from pyhermes.builder.research import Reference
from pyhermes.deck import SLIDE_16_9, Deck, DeckFooter

from . import pitch_16_9
from ._png import solid_png

#: The full-bleed picture: a dark sheet, at one source pixel a CSS px.
_BLEED_PNG = solid_png(1280, 720, (28, 42, 58))

#: The pictures beside the copy: half the sheet each.
_LEFT_PNG = solid_png(640, 720, (91, 138, 154))
_RIGHT_PNG = solid_png(640, 720, (196, 160, 98))

#: The confidentiality mark every banded sheet carries.
MARK = "Strictly private and confidential"

#: The source line, citing the reference the last slide lists.
SOURCE = "Hermes Research; Bank of England [@boe2026]"

#: The statement slide's figure.
STATEMENT = HeroStat("38 bps", "2s10s", "The steepest curve since 2022")

#: The notes on the statement slide, carrying the sentinel no other projection may.
STATEMENT_NOTES = (
    "Let the number sit for a beat before saying anything.\n\n"
    "The sentinel ZEBRANOTES7 marks what only the presenter reads."
)

#: The title of each slide that has one, in order.
TITLES: tuple[str, ...] = (
    "Agenda",
    "The picture",
    "Where the curve stands",
    "Beside the argument",
    "The other side",
    "The evidence",
    "Sourced figures",
    "The lead figure",
    "References",
)


def build(template_dir: Path | None = None) -> Deck:
    """Build the deck. Deterministic: same bytes every call."""
    deck = Deck(
        pitch_16_9.facts(),
        page=SLIDE_16_9,
        template_dir=template_dir,
        divider_agenda=True,
        footer=DeckFooter(counter="total", label=MARK),
    )
    deck.add_slide([FullWidth(content=Contents())], TITLES[0])
    deck.add_divider(TITLES[1], subtitle="Pictures on a slide")
    deck.add_slide(
        [
            FullWidth(
                content=TextBlock(
                    "<p>Ten-year yields ended the quarter eighteen basis points higher, "
                    "and the long end did the work.</p>"
                )
            )
        ],
        TITLES[2],
        background_image=EmailImage.attached(_BLEED_PNG, alt="The gilt market at dusk"),
        ground="dark",
        notes="Open on the picture; the number comes later.",
    )
    deck.add_slide(
        [
            FullWidth(
                content=TextBlock(
                    "<p>The premium rose for a third quarter. It now explains most of "
                    "the move at the long end, and little of the front.</p>"
                )
            )
        ],
        TITLES[3],
        image=EmailImage.attached(_LEFT_PNG, alt="The trading floor"),
        image_side="left",
    )
    deck.add_slide(
        [FullWidth(content=TextBlock("<p>The front end waits on the next two prints.</p>"))],
        TITLES[4],
        image=EmailImage.attached(_RIGHT_PNG, alt="The Bank of England"),
        image_side="right",
    )
    deck.add_divider(TITLES[5], subtitle="Figures, sourced", valign="middle")
    deck.add_slide(
        [
            FullWidth(
                content=DataTable(
                    ["Tenor", "Yield", "Change (bps)"],
                    [
                        TableRow(["2Y", "3.83%", "+9"]),
                        TableRow(["10Y", "4.21%", "+18"]),
                        TableRow(["30Y", "4.78%", "+21"]),
                    ],
                )
            )
        ],
        TITLES[6],
        source=SOURCE,
        as_of="30 September 2026",
    )
    deck.add_statement(STATEMENT, TITLES[7], notes=STATEMENT_NOTES)
    deck.add_slide(
        [
            FullWidth(
                content=Bibliography(
                    [
                        Reference(
                            "boe2026",
                            ["Bank of England"],
                            2026,
                            "Monetary Policy Report",
                            venue="September",
                        )
                    ]
                )
            )
        ],
        TITLES[8],
    )
    return deck
