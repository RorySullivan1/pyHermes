"""
A research note's content, shared by the paged and the email fixture (#312).

Every long-form piece at once: citations, a glossary the body links to, a
key-takeaways callout, three body exhibits, one a lettered grid with a key and
a cross-reference to a panel, a source line shared by a section, a
bibliography, a glossary and two lettered appendices, the second holding a
grid. Both media build the same sections, so their goldens pin that the
numbering agrees across them.
"""

from __future__ import annotations

from pyhermes.builder import (
    Appendices,
    Aside,
    Bibliography,
    Callout,
    ChartBlock,
    Container,
    DataTable,
    FigureGrid,
    FullWidth,
    Glossary,
    Legend,
    LegendEntry,
    Reference,
    Stack,
    Term,
    TextBlock,
)
from pyhermes.builder.images import EmailImage
from pyhermes.builder.models import TableRow

from ._png import solid_png

#: The decile chart, the note's second exhibit.
_DECILE_PNG = solid_png(600, 90, (91, 138, 154))

#: The cost chart in Appendix B.
_COST_PNG = solid_png(600, 70, (122, 150, 120))

#: A grid panel's chart: one region's spread, or one turnover's costs (#339).
_PANEL_PNG = solid_png(300, 120, (91, 138, 154))

#: Every exhibit heading, in reading order, as each projection must print it.
EXHIBITS = [
    "Exhibit 1 · Momentum decile returns",
    "Exhibit 2 · The winner-minus-loser spread",
    "Exhibit 3 · The spread by region",
    "Exhibit A.1 · Data coverage",
    "Exhibit B.1 · Returns after trading costs",
    "Exhibit B.2 · Costs by turnover",
]

#: The panels of the grids, as each projection anchors them.
PANELS = ["exhibit-3-a", "exhibit-3-b", "exhibit-b-2-a", "exhibit-b-2-b"]

REFERENCES = [
    Reference(
        "jt1993",
        ["Jegadeesh, Narasimhan", "Titman, Sheridan"],
        1993,
        "Returns to buying winners and selling losers: implications for stock market efficiency",
        "The Journal of Finance",
        doi="10.1111/j.1540-6261.1993.tb04702.x",
    ),
    Reference(
        "carhart1997",
        ["Carhart, Mark M."],
        1997,
        "On persistence in mutual fund performance",
        "The Journal of Finance",
        doi="10.1111/j.1540-6261.1997.tb03808.x",
    ),
    Reference(
        "dm2016",
        ["Daniel, Kent", "Moskowitz, Tobias J."],
        2016,
        "Momentum crashes",
        "Journal of Financial Economics",
        doi="10.1016/j.jfineco.2015.12.002",
    ),
    Reference(
        "afmp2018",
        ["Frazzini, Andrea", "Israel, Ronen", "Moskowitz, Tobias J."],
        2018,
        "Trading costs",
        url="https://example.com/trading-costs",
    ),
]

TERMS = [
    Term("Momentum", "The tendency of recent winners to keep outperforming recent losers."),
    Term(
        "Winner-minus-loser",
        "A portfolio long the top decile of past returns and short the bottom decile.",
    ),
    Term("Momentum crash", "A sudden reversal in which past losers sharply outperform."),
    Term("Turnover", "The share of a portfolio traded each month to keep it on its signal."),
]


def _deciles() -> DataTable:
    return DataTable(
        headers=["Decile", "Return", "Volatility"],
        rows=[
            TableRow(cells=["1 (losers)", "-0.4%", "8.1%"]),
            TableRow(cells=["5", "0.7%", "4.9%"]),
            TableRow(cells=["10 (winners)", "1.3%", "6.2%"]),
        ],
        caption="Momentum decile returns",
        label="Exhibit",
        source="Hermes Research [@jt1993]",
        as_of="30 September 2026",
    )


def _coverage() -> DataTable:
    return DataTable(
        headers=["Region", "Stocks", "From"],
        rows=[
            TableRow(cells=["United States", "3,412", "1963"]),
            TableRow(cells=["Europe", "2,180", "1990"]),
            TableRow(cells=["Japan", "1,604", "1990"]),
        ],
        caption="Data coverage",
        label="Exhibit",
        source="Hermes Research",
    )


def _panel(alt: str, subtitle: str, legend: Legend | None = None) -> ChartBlock:
    return ChartBlock(
        EmailImage.attached(_PANEL_PNG, alt=alt, width=300), subtitle=subtitle, legend=legend
    )


def _regions() -> FigureGrid:
    """Exhibit 3: one chart a region, the key naming the two lines by their chart colours."""
    key = Legend(["Winners", "Losers"])
    return FigureGrid(
        [
            _panel("Spread in the United States", "United States", key),
            _panel("Spread in Europe", "Europe", key),
        ],
        caption="The spread by region",
    )


def _turnover() -> FigureGrid:
    """Exhibit B.2: a grid in an appendix, its key naming a tone and a hex."""
    key = Legend(
        [LegendEntry("Net of costs", tone="positive"), LegendEntry("Costs", color="#5A5A5A")],
        layout="column",
    )
    return FigureGrid(
        [
            _panel("Costs at low turnover", "Low turnover", key),
            _panel("Costs at high turnover", "High turnover"),
        ],
        caption="Costs by turnover",
        source="Hermes Research [@afmp2018]",
        disclosure="Costs are estimated from a model of market impact, not observed trades.",
    )


def sections() -> list[Container]:
    """The note's sections in reading order, built fresh on every call."""
    return [
        FullWidth(
            title="Summary",
            content=Stack(
                [
                    TextBlock(
                        '<p><a href="#term-momentum">Momentum</a> has earned a premium in '
                        "every market studied since the first evidence [@jt1993], and it "
                        "survives the four-factor model [@carhart1997]. Its cost is the "
                        '<a href="#term-momentum-crash">momentum crash</a> '
                        "[@dm2016].[^1]</p>",
                        notes=["The sample ends on 30 September 2026."],
                    ),
                    Callout(
                        TextBlock(
                            "<p>The premium survives trading costs at moderate turnover, "
                            "and the crash risk is what a position should be sized to.</p>"
                        ),
                        label="Key takeaways",
                    ),
                ]
            ),
        ),
        FullWidth(
            title="Data and Method",
            content=Stack(
                [
                    TextBlock(
                        "<p>Stocks are ranked each month on their return over the prior "
                        "twelve months, skipping the most recent [@jt1993]. The "
                        '<a href="#term-winner-minus-loser">winner-minus-loser</a> '
                        'portfolio is set out in <a class="xref" href="#exhibit-1">'
                        "Exhibit 1</a>, and the sample in "
                        '<a class="xref" href="#exhibit-a-1">Exhibit A.1</a>.</p>',
                        # A method note beside the prose on paper, a callout above it
                        # in the email (#343).
                        aside=Aside(
                            "The latest month is skipped, because short-horizon returns reverse.",
                            title="Why skip a month",
                            tone="neutral",
                        ),
                    ),
                    _deciles(),
                ]
            ),
        ),
        FullWidth(
            title="Results",
            content=Stack(
                [
                    ChartBlock(
                        EmailImage.attached(
                            _DECILE_PNG, alt="Winner-minus-loser spread by year", width=600
                        ),
                        caption="The winner-minus-loser spread",
                        label="Exhibit",
                    ),
                    TextBlock(
                        "<p>The spread is positive in most years and negative in a few "
                        "deep ones [@dm2016], and Europe's is the steadier, in "
                        '<a class="xref" href="#exhibit-3-b">Exhibit 3(b)</a>. After '
                        'costs at the <a href="#term-turnover">turnover</a> the strategy '
                        'needs, <a class="xref" href="#exhibit-b-1">Exhibit B.1</a> keeps '
                        "most of it [@afmp2018].</p>"
                    ),
                    _regions(),
                ]
            ),
            # One line for both exhibits (#338), citing and calling a note.
            source="Hermes Research [@jt1993][^1]",
            as_of="30 September 2026",
            source_notes=["Returns are in US dollars, before costs."],
        ),
        FullWidth(title="References", content=Bibliography(REFERENCES)),
        FullWidth(title="Glossary", content=Glossary(TERMS)),
        Appendices(
            [
                FullWidth(title="Data sources", content=_coverage()),
                FullWidth(
                    title="Robustness",
                    content=Stack(
                        [
                            ChartBlock(
                                EmailImage.attached(
                                    _COST_PNG, alt="Returns after costs", width=600
                                ),
                                caption="Returns after trading costs",
                                label="Exhibit",
                                source="Hermes Research [@afmp2018]",
                            ),
                            _turnover(),
                        ]
                    ),
                ),
            ]
        ),
    ]
