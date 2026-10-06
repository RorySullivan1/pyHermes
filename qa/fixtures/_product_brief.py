"""
Single-sheet print pieces (#386), shared by the email and the US Letter product brief.

A three-sheet product brief for a fictional fund, with no layout workaround: a
masthead band run to the sheet's edges (#396), a fund box in a brand tone beside
a solid ticker chip (#387, #388), three equal boxes joined by "+" signs (#398), a
chart with a brand-tone key and a qualifier (#337, #395), a scenario table ruled
off its label column pointing by a connector arrow at a dashed verdict box
(#390, #399), a grey band run to the edges, a sheet of fine-print disclosures
(#393, #394) and a logo pinned to that sheet's foot (#397). The paged fixture
leaves its running boxes off the masthead sheet (#400). Every name and figure
is fictional.
"""

from __future__ import annotations

from pyhermes.builder import (
    Callout,
    ChartBlock,
    Column,
    Columns,
    Container,
    DataTable,
    FactList,
    FullWidth,
    ImageBlock,
    Legend,
    TextBlock,
    TwoColumn,
)
from pyhermes.builder.exhibits import LegendEntry
from pyhermes.builder.images import EmailImage
from pyhermes.builder.models import TableRow
from pyhermes.builder.theming import DEFAULT_THEME

from . import _brief
from ._png import solid_png

#: The classic theme with the brand's gold, sky and ink; no semantic token is repainted.
THEME = DEFAULT_THEME.derive(tones={"gold": "#B8860B", "sky": "#0077A8", "ink": "#111111"})

#: The masthead's ground and the band's.
NAVY = "#1B2A3A"
GREY = "#E9E7E3"

_CHART_PNG = solid_png(600, 110, (0, 119, 168))
_LOGO_PNG = solid_png(160, 40, (27, 42, 58))


def _box(label: str, copy: str) -> Callout:
    """One of the three equal boxes the "+" signs join."""
    return Callout(TextBlock(f"<p>{copy}</p>"), tone="sky", label=label)


def sections() -> list[Container]:
    """The sections both fixtures render, in order."""
    return [
        FullWidth(
            title="Meridian Broad Market Fund",
            title_size="display",
            title_case="upper",
            kicker="Product brief",
            background_color=NAVY,
            bleed=True,
            content=TextBlock("<p>The whole US equity market, in one low-cost holding.</p>"),
        ),
        TwoColumn(
            ratio=(2, 1),
            left=Callout(
                TextBlock(
                    "<p>Holds every large and mid-sized US company in its index, weighted "
                    "by the shares the public can buy, rebalanced each quarter.</p>"
                ),
                tone="gold",
                label="The fund",
            ),
            right=Callout(
                TextBlock("<p><strong>MBMF</strong> on NYSE Arca</p>"),
                tone="ink",
                label="Ticker",
                fill="solid",
            ),
        ),
        FullWidth(
            title="How it is built",
            content=Columns(
                [
                    _box("Large caps", "About 80% of the market's value."),
                    _box("Mid caps", "About 15%, the next tier down."),
                    _box("Quarterly rebalance", "Weights reset to the index."),
                ],
                separator="+",
            ),
        ),
        FullWidth(
            title="Performance",
            content=ChartBlock(
                EmailImage.attached(_CHART_PNG, alt="Growth of 10,000 since launch", width=600),
                subtitle="Growth of 10,000 invested at launch",
                qualifier="Total return, USD, net of fees, March 2019 to September 2026",
                source="Fictional data",
                caption="Growth of an investment",
                label="Exhibit",
                legend=Legend([LegendEntry("Fund", tone="gold"), LegendEntry("Index", tone="sky")]),
            ),
        ),
        FullWidth(
            title="Three scenarios, one verdict",
            break_before=True,
            content=Columns(
                [
                    DataTable(
                        [
                            Column("Scenario", rule_after=True),
                            Column("Index", kind="numeric"),
                            Column("Fund", kind="numeric"),
                        ],
                        [
                            TableRow(["Rates fall", "+14.0%", "+13.9%"]),
                            TableRow(["Rates hold", "+7.5%", "+7.4%"]),
                            TableRow(["Rates rise", "-6.2%", "-6.3%"]),
                        ],
                        subtitle="Twelve-month return in each scenario",
                        source="Fictional data",
                    ),
                    Callout(
                        TextBlock(
                            "<p>The fund tracks its index within 0.1% in every scenario, "
                            "so the choice is the market, not the vehicle.</p>"
                        ),
                        tone="gold",
                        label="Verdict",
                        frame="dashed",
                    ),
                ],
                ratio=(2, 1),
                separator="arrow",
            ),
        ),
        FullWidth(
            title="Portfolio at a glance",
            background_color=GREY,
            bleed=True,
            content=FactList(
                {
                    "Holdings": "3,612",
                    "Ongoing charge": "0.04%",
                    "Inception": "12 March 2019",
                    "Distributions": "Quarterly",
                    "Turnover": "3%",
                    "Benchmark": "Meridian US Total Market",
                },
                columns=2,
            ),
        ),
        FullWidth(
            title="Important information",
            type_size="fine",
            align="justify",
            break_before=True,
            content=TextBlock("".join(f"<p>{line}</p>" for line in _brief.DISCLOSURES)),
        ),
        FullWidth(
            pin="bottom",
            content=ImageBlock(EmailImage.attached(_LOGO_PNG, alt="Meridian", width=160)),
        ),
    ]
