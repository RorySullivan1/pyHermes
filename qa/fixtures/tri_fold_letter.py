"""
A letter tri-fold: the brochure medium's gallery fixture (#172).

Six panels in reader order, each opening on copy no other panel carries, so a
test can find every face on the sheet by its text and check the imposition put
it where the fold says. Every ``Panel`` field is set somewhere at a
non-default value, per standing rule 9.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.brochure import TRI_FOLD_LETTER, Brochure, Panel
from pyhermes.builder import (
    Aside,
    AuthorBlock,
    CardGroup,
    ChartBlock,
    ContactBlock,
    FlowedColumns,
    FullWidth,
    HeroStat,
    ImageBlock,
    NumberedList,
    PullQuote,
    QrCode,
    TextBlock,
)
from pyhermes.builder.enums import CardOrientation
from pyhermes.builder.images import EmailImage
from pyhermes.builder.models import Card, NumberedItem

from . import _paged
from ._png import solid_png
from ._qr import URL as QR_URL
from ._qr import qr_png

#: A chart that fits a full panel's copy (356px less a 24px inset a side) and
#: prints at 300 dpi there: 300px displayed needs 938 source pixels (#188).
_CHART_PNG = solid_png(938, 313, (91, 138, 154))

#: The front cover's full-bleed ground (#189): 368px wide with its bleed, so
#: 1,150 source pixels print it at 300 dpi. Pale, so the cover copy reads on it.
_COVER_PNG = solid_png(1150, 2625, (226, 234, 240))

#: The wrapped figure on the inside flap: 96px displayed, 300 source pixels.
_DESK_PNG = solid_png(300, 375, (74, 124, 89))

#: The words each face opens on, in reader order. The tests read these back
#: off the PDF, one side at a time.
MARKERS: tuple[str, ...] = (
    "Rates, Folded",
    "Why the curve",
    "What we measured",
    "Three positions",
    "About Hermes Research",
    "Talk to the desk",
)


def build(template_dir: Path | None = None) -> Brochure:
    """Build the tri-fold. Deterministic: same bytes every call."""
    return Brochure(_paged.facts(), panels(), fold=TRI_FOLD_LETTER, template_dir=template_dir)


def panels() -> list[Panel]:
    """The six faces, front cover first."""
    return [
        Panel(
            [
                FullWidth(
                    title=MARKERS[0],
                    content=TextBlock(
                        "<p>A quarterly view of the gilt curve, on one sheet.</p>",
                        align="center",
                    ),
                    align="center",
                ),
            ],
            title="Front cover",
            # A tinted ground under a full-bleed picture, and the one panel
            # with a wider inset: the cover's copy sits further from the trim.
            background_color="#EEF2F5",
            background_image=EmailImage.attached(_COVER_PNG, alt="Cover ground"),
            align="center",
            inset=36,
            # The cover's title sits low, at the safe line (#355).
            valign="bottom",
        ),
        Panel(
            [
                FullWidth(
                    title=MARKERS[1],
                    content=TextBlock(
                        "<p>The curve steepened through the quarter as the front end "
                        "repriced. Duration added to returns for the first time in "
                        "four quarters, and the long end held its ground.</p>",
                        drop_cap=True,
                        # A boxout the prose wraps round inside the panel (#343).
                        aside=Aside("Two-year against ten-year gilt yields.", title="2s10s"),
                    ),
                ),
                FullWidth(
                    content=PullQuote(
                        "Duration earned its place in the book again.",
                        attribution="Head of Rates Strategy",
                    ),
                ),
            ],
            title="Inside left",
        ),
        Panel(
            [
                FullWidth(
                    title=MARKERS[2],
                    content=ChartBlock(
                        EmailImage.attached(_CHART_PNG, alt="The 2s10s spread", width=300),
                        caption="The 2s10s spread",
                        source="Hermes Research",
                    ),
                ),
                # The panel's figure, set alone under its chart (#322).
                FullWidth(
                    content=HeroStat("38 bps", "2s10s", "steepest since 2022", align="center"),
                ),
            ],
            title="Inside centre",
        ),
        Panel(
            [
                FullWidth(
                    title=MARKERS[3],
                    content=NumberedList(
                        [
                            NumberedItem("01", "Steepeners", "<p>Two against ten.</p>"),
                            NumberedItem("02", "Linkers", "<p>Breakevens look cheap.</p>"),
                            NumberedItem("03", "Cash", "<p>Carry pays to wait.</p>"),
                        ]
                    ),
                ),
            ],
            title="Inside right",
        ),
        Panel(
            [
                FullWidth(
                    title=MARKERS[4],
                    content=AuthorBlock(
                        "Rates Strategy", job_title="Hermes Research", align="right"
                    ),
                ),
                # Left, against the panel's right: a measure set ragged-left
                # reads badly, and the override is the cascade working.
                FlowedColumns(
                    align="left",
                    content=TextBlock(
                        "<p>Hermes Research covers rates, credit and currencies for "
                        "institutional clients. This brochure summarises the quarterly "
                        "review; the full document carries the method and every "
                        "exhibit.</p>"
                    ),
                ),
                # The way back to the web (#344): a code printed at one inch.
                FullWidth(content=QrCode(qr_png(), QR_URL, caption="The full review online")),
            ],
            title="Back cover",
            align="right",
        ),
        Panel(
            [
                FullWidth(
                    title=MARKERS[5],
                    content=TextBlock(
                        "<p>The rates desk takes calls from seven, and every client "
                        "gets the full review on request.</p>",
                        figure=ImageBlock(
                            EmailImage.attached(_DESK_PNG, alt="The rates desk", width=96),
                            align="right",
                            wrap="right",
                        ),
                    ),
                ),
                FullWidth(
                    content=CardGroup(
                        [Card("Desk", "+44 20 0000 0000"), Card("Hours", "07:00-18:00")],
                        orientation=CardOrientation.VERTICAL,
                    ),
                ),
                FullWidth(
                    content=ContactBlock("Get the full review", cta_url="mailto:rates@example.com"),
                ),
            ],
            title="Inside flap",
        ),
    ]
