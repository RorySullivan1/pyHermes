"""
Placement across media, shared by the email and the paged fixture (#361).

One set of sections carries every control the epic added: a split that puts
its right column first on a phone, a narrow pair that stays side by side
there, an email-only button, a print-only page note with an image of its own,
a section kept together and one that starts a fresh sheet. Both media build
the same sections, so each golden pins what its own medium makes of them.
"""

from __future__ import annotations

from pyhermes.builder import (
    Button,
    CardGroup,
    ChartBlock,
    Columns,
    Container,
    FullWidth,
    ImageBlock,
    Only,
    OnlySections,
    Stack,
    TextBlock,
    TwoColumn,
)
from pyhermes.builder.images import EmailImage
from pyhermes.builder.models import KpiItem

from ._png import solid_png

#: The chart a phone reader should meet before the commentary on it.
_CURVE_PNG = solid_png(400, 160, (91, 138, 154))

#: The page note's mark: attached, so only the medium showing the note carries it.
_MARK_PNG = solid_png(48, 48, (184, 84, 80))

_COPY = (
    "The long end did the work this quarter: ten-year yields rose eighteen basis points while "
    "the two-year barely moved, and the term premium explains most of the difference."
)


def _figure(label: str, value: str, sublabel: str) -> CardGroup:
    return CardGroup([KpiItem(label, value, sublabel=sublabel)], orientation="vertical")


def sections() -> list[Container]:
    """The sections, in reading order. Deterministic: same objects' bytes every call."""
    return [
        TwoColumn(
            "30-70",
            left=TextBlock(f"<p>{_COPY}</p>"),
            right=ChartBlock(
                EmailImage.attached(_CURVE_PNG, alt="Gilt curve, quarter on quarter", width=400),
                alt_text="Gilt curve, quarter on quarter",
                source="Hermes Research",
            ),
            title="The chart comes first on a phone",
            stack="reverse",
        ),
        TwoColumn(
            "50-50",
            left=_figure("10Y gilt", "4.21%", "+18 bps"),
            right=_figure("2s10s", "38 bps", "+9 bps"),
            title="Two figures, side by side everywhere",
            stack=False,
        ),
        FullWidth(
            Stack(
                [
                    Columns(
                        [
                            TextBlock("<p><strong>Modified duration</strong></p>"),
                            TextBlock("<p>6.8 years</p>", align="right"),
                        ],
                        ratio=(3, 2),
                        stack=False,
                    ),
                    Columns(
                        [
                            TextBlock("<p>Read the curve, then the trade.</p>"),
                            TextBlock("<p>The trade, read first on a phone.</p>"),
                        ],
                        stack="reverse",
                    ),
                ]
            ),
            title="A label beside its value",
        ),
        FullWidth(
            Stack(
                [
                    TextBlock(f"<p>{_COPY}</p>"),
                    Only(
                        Button("Download the PDF", "https://example.com/rates-review.pdf"),
                        media="email",
                    ),
                ]
            ),
            title="Read the full note",
        ),
        OnlySections(
            [
                FullWidth(
                    Stack(
                        [
                            ImageBlock(
                                EmailImage.attached(_MARK_PNG, alt="Printed edition", width=48)
                            ),
                            TextBlock(
                                "<p>This printed edition carries the full tables; the email "
                                "links to them.</p>"
                            ),
                        ]
                    ),
                    title="About this edition",
                    highlight=True,
                )
            ],
            media=("document",),
        ),
        FullWidth(
            TextBlock(f"<p>{_COPY}</p>" * 6),
            title="Kept on one sheet",
            keep_together=True,
        ),
        FullWidth(
            TextBlock(f"<p>{_COPY}</p>"),
            title="Opening a fresh sheet",
            break_before=True,
        ),
    ]
