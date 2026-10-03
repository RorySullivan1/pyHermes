"""
Placement across media, shared by the email and the paged fixture (#361).

One set of sections carries every control the epic added: a split that puts
its right column first on a phone, a narrow pair that stays side by side
there, an email-only button, a print-only page note with an image of its own,
a section kept together and one that starts a fresh sheet. Both media build
the same sections, so each golden pins what its own medium makes of them.
After the fresh sheet come #354's: a paper-only split aligned middle, a chart
and an equation the prose wraps round, a callout, a table, figures and a
contents list each at a share of the column, and a narrow measure.
"""

from __future__ import annotations

from pyhermes.builder import (
    Button,
    Callout,
    CardGroup,
    ChartBlock,
    Columns,
    Container,
    Contents,
    DataTable,
    FullWidth,
    ImageBlock,
    MathBlock,
    Only,
    OnlySections,
    Stack,
    TextBlock,
    TwoColumn,
)
from pyhermes.builder.images import EmailImage
from pyhermes.builder.models import KpiItem, TableRow

from ._png import solid_png

#: The chart a phone reader should meet before the commentary on it.
_CURVE_PNG = solid_png(400, 160, (91, 138, 154))

#: The page note's mark: attached, so only the medium showing the note carries it.
_MARK_PNG = solid_png(48, 48, (184, 84, 80))

#: The chart and the equation the prose wraps round (#359): small, so a column holds both.
_PREMIUM_PNG = solid_png(320, 200, (91, 138, 154))
_EQUATION_PNG = solid_png(360, 80, (34, 49, 63))

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
        *_positioned(),
    ]


def _positioned() -> list[Container]:
    """#354's controls, after the fresh sheet so no engineered break above them moves."""
    return [
        # An email refuses valign off the top (#356), so the split is paper's alone.
        OnlySections(
            [
                TwoColumn(
                    "30-70",
                    left=_figure("Term premium", "61 bps", "+12 bps"),
                    right=TextBlock(f"<p>{_COPY}</p>" * 3),
                    title="A figure level with the middle of its commentary",
                    valign="middle",
                )
            ],
            media=("document",),
        ),
        FullWidth(
            TextBlock(
                f"<p>{_COPY} {_COPY}</p>",
                figure=ChartBlock(
                    EmailImage.attached(_PREMIUM_PNG, alt="Term premium", width=160),
                    alt_text="Term premium",
                    source="Hermes Research",
                    wrap="right",
                ),
            ),
            title="A chart the prose wraps round",
        ),
        FullWidth(
            TextBlock(
                f"<p>{_COPY} {_COPY}</p>",
                figure=MathBlock(
                    _EQUATION_PNG, r"P = \sum_t c_t\,e^{-y t}", width=180, wrap="left"
                ),
            ),
            title="An equation the prose wraps round",
        ),
        FullWidth(
            Callout(
                TextBlock("<p>The premium, not the policy path, moved the long end.</p>"),
                label="Key takeaway",
                width=0.6,
            ),
            title="A callout at a share of its column",
            align="center",
        ),
        FullWidth(
            DataTable(
                ["Tenor", "Yield", "Change (bps)"],
                [TableRow(["2Y", "3.83%", "+9"]), TableRow(["10Y", "4.21%", "+18"])],
                source="Hermes Research",
                width=0.6,
            ),
            title="A short table, not the whole width",
            align="center",
        ),
        FullWidth(
            CardGroup(
                [KpiItem("10Y gilt", "4.21%"), KpiItem("2s10s", "38 bps")],
                width=0.5,
            ),
            title="Two figures to the right",
            align="right",
        ),
        FullWidth(Contents(width=0.6), title="In this note"),
        FullWidth(
            TextBlock(f"<p>{_COPY} {_COPY}</p>", measure="narrow"),
            title="A narrow measure",
        ),
    ]
