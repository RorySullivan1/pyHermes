"""
A research note's content, shared by the paged and the email fixture (#312).

Every long-form piece at once: citations, a glossary the body links to, a
key-takeaways callout, two body exhibits, a bibliography, a glossary and two
lettered appendices. Both media build the same sections, so their goldens pin
that the numbering agrees across them.
"""

from __future__ import annotations

from pyhermes.builder import (
    Appendices,
    Bibliography,
    Callout,
    ChartBlock,
    Container,
    DataTable,
    FullWidth,
    Glossary,
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

#: Every exhibit heading, in reading order, as each projection must print it.
EXHIBITS = [
    "Exhibit 1 · Momentum decile returns",
    "Exhibit 2 · The winner-minus-loser spread",
    "Exhibit A.1 · Data coverage",
    "Exhibit B.1 · Returns after trading costs",
]

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
                        '<a class="xref" href="#exhibit-a-1">Exhibit A.1</a>.</p>'
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
                        source="Hermes Research",
                    ),
                    TextBlock(
                        "<p>The spread is positive in most years and negative in a few "
                        "deep ones [@dm2016]. After costs at the "
                        '<a href="#term-turnover">turnover</a> the strategy needs, '
                        '<a class="xref" href="#exhibit-b-1">Exhibit B.1</a> keeps most '
                        "of it [@afmp2018].</p>"
                    ),
                ]
            ),
        ),
        FullWidth(title="References", content=Bibliography(REFERENCES)),
        FullWidth(title="Glossary", content=Glossary(TERMS)),
        Appendices(
            [
                FullWidth(title="Data sources", content=_coverage()),
                FullWidth(
                    title="Robustness",
                    content=ChartBlock(
                        EmailImage.attached(_COST_PNG, alt="Returns after costs", width=600),
                        caption="Returns after trading costs",
                        label="Exhibit",
                        source="Hermes Research [@afmp2018]",
                    ),
                ),
            ]
        ),
    ]
