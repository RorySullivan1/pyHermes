"""
Fund Factsheet — the dense, two-sheet document the paged medium was built for.

Where ``quarterly-review`` shows the managed elements (a cover, a contents
sheet, back matter), this shows the opposite discipline: a factsheet has **no
cover and no contents**, because every one of its two sheets has to carry
data. It is the format an ETF or fund publishes monthly, and its constraints
are unusual —

- **the sheet count is the specification.** Two sheets, not "about two": the
  page break is explicit rather than wherever the content lands, running this
  file exits non-zero if the layout ever says otherwise, and
  ``tests/test_examples.py`` pins it so a builder change cannot move it
  quietly,
- **density is the point.** It renders at ``dense``, the print density, and
  its returns tables sit tighter still through ``spacing=`` (epic #209).
  Nearly every section is a ``TwoColumn``, so two tables share a row,
- **the numbers are the product**, so they come from one place at the top of
  this file and are referenced below — a factsheet whose figures are scattered
  through its layout code is one nobody dares update.

The two charts are matplotlib Figures through ``svc.data.chart_from_figure``,
which is the adapter's reason to exist: the builder never learns to plot.

**The fund is fictional.** ``HERMES CORE US EQUITY ETF`` does not exist, and
every figure here is illustrative sample data chosen to be internally
consistent. It is a layout demonstration, not a record of anything.

Run it directly to (re)generate ``fund-factsheet.html`` next to this file, and
``fund-factsheet.pdf`` as well when the ``[pdf]`` extra is installed:

    python examples/fund-factsheet/fund-factsheet.py

``build()`` is a pure, deterministic factory in the same shape as the other
examples and the fixtures in ``qa/fixtures/`` — same bytes every call.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from svc.builder import (
    CardGroup,
    Container,
    DataTable,
    FullWidth,
    Spacing,
    TextBlock,
    TwoColumn,
)
from svc.builder.enums import CardOrientation, TwoColumnRatio
from svc.builder.formats import number
from svc.builder.models import Cell, Column, ColumnGroup, KpiItem, TableRow
from svc.builder.sizing import LETTER_PORTRAIT
from svc.data.exceptions import BackendMissingError
from svc.document import (
    EmptyBackMatter,
    EmptyContentsPage,
    EmptyCover,
    PagedDocument,
    RunningFooter,
    RunningHeader,
    paged_medium,
)

# --------------------------------------------------------------------------
# The numbers, in one place. A factsheet is re-published every month with the
# same layout and new figures, so the figures are lifted out of the layout.
# --------------------------------------------------------------------------

#: The specification. A factsheet is two sheets; see the module docstring.
SHEETS = 2

AS_OF = "30 September 2026"
FUND = "Hermes Core US Equity ETF"
TICKER = "HCUS"

_GAIN = "#4A7C59"
_LOSS = "#B85450"

#: Growth of a $10,000 investment, ten year-ends, fund and benchmark.
_GROWTH_YEARS = [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]
_GROWTH_FUND = [
    10000,
    11_820,
    11_296,
    14_842,
    17_573,
    22_600,
    18_487,
    23_312,
    29_117,
    31_941,
    35_910,
]
_GROWTH_BENCH = [
    10000,
    11_838,
    11_318,
    14_881,
    17_624,
    22_674,
    18_551,
    23_404,
    29_251,
    32_101,
    36_112,
]

#: Sector weights, largest first. They total 100.0.
_SECTORS = [
    ("Information Technology", 32.4),
    ("Financials", 13.1),
    ("Health Care", 11.2),
    ("Consumer Discretionary", 10.4),
    ("Communication Services", 9.3),
    ("Industrials", 8.1),
    ("Consumer Staples", 5.6),
    ("Energy", 3.4),
    ("Utilities", 2.5),
    ("Real Estate", 2.2),
    ("Materials", 1.8),
]

#: Average annual total returns, in percent, as of AS_OF. Raw figures: the
#: table's columns write them (#225), so no cell spells its own format.
_RETURNS = [
    ("Fund (NAV)", 18.42, 11.87, 14.03, 12.51, 11.94),
    ("Fund (Market Price)", 18.39, 11.85, 14.02, 12.50, 11.93),
    ("Hermes US Large-Cap Index", 18.51, 11.96, 14.12, 12.60, 12.03),
]

#: The one figure the returns table flags, rather than the whole table (#224).
_INCEPTION_NOTE = "Annualised from the fund's inception on 14 March 2012."

#: Calendar-year total returns, fund against benchmark.
_CALENDAR = [
    ("2025", "9.71", "9.80"),
    ("2024", "24.92", "25.02"),
    ("2023", "26.07", "26.19"),
    ("2022", "-18.20", "-18.11"),
    ("2021", "28.61", "28.71"),
]

#: Risk over three years, monthly returns, fund against benchmark.
_RISK = [
    ("Standard Deviation", "15.21%", "15.19%"),
    ("Sharpe Ratio", "0.71", "0.72"),
    ("Beta", "1.00", "1.00"),
    ("Tracking Error", "0.04%", "-"),
    ("Maximum Drawdown", "-24.83%", "-24.71%"),
    ("Up / Down Capture", "99.8 / 100.1", "-"),
]

#: How the shares trade, as of AS_OF.
_TRADING = [
    ("Avg. Daily Volume (30D)", "2.14M shares"),
    ("Median Bid/Ask Spread", "0.01%"),
    ("Premium / Discount", "+0.02%"),
    ("Shares Outstanding", "88.9M"),
    ("Options Available", "Yes"),
    ("Primary Listing", "NYSE Arca"),
]

#: What the portfolio holds, in aggregate.
_CHARACTERISTICS = [
    ("Price / Earnings", "24.8x"),
    ("Price / Book", "4.6x"),
    ("Wtd. Avg. Market Cap", "$982.4B"),
    ("Dividend Yield", "1.38%"),
    ("Return on Equity", "27.9%"),
]

#: The second row of characteristics: growth and balance sheet.
_FUNDAMENTALS = [
    ("EPS Growth (3Y)", "11.4%"),
    ("Sales Growth (3Y)", "8.2%"),
    ("Net Debt / EBITDA", "0.9x"),
    ("Active Share", "0.6%"),
    ("Turnover (12M)", "3.1%"),
]

#: The last four quarterly distributions, per share.
_DISTRIBUTIONS = [
    ("Q3 2026", "$0.182"),
    ("Q2 2026", "$0.179"),
    ("Q1 2026", "$0.171"),
    ("Q4 2025", "$0.194"),
    ("Trailing 12M", "$0.726"),
]

#: Both returns tables sit tighter than the dense preset (#215): a returns
#: table is read across a row, and a row's padding is what it spends. The
#: table beside the calendar returns takes it too, so the two end level.
_RETURNS_SPACING = Spacing(table_cell_pad=3)

_TOP_HOLDINGS = [
    ("Apple Inc.", "7.42"),
    ("Microsoft Corp.", "6.98"),
    ("NVIDIA Corp.", "6.11"),
    ("Amazon.com Inc.", "3.84"),
    ("Alphabet Inc. Class A", "2.31"),
    ("Meta Platforms Inc.", "2.48"),
    ("Broadcom Inc.", "2.06"),
    ("Alphabet Inc. Class C", "1.93"),
    ("Berkshire Hathaway Inc. Class B", "1.71"),
    ("Eli Lilly & Co.", "1.44"),
]


def _percent(value: float) -> str:
    return number(value, 2)


def _returns_table() -> DataTable:
    """
    The returns table in the words a desk writes one in (#217).

    "Annualised" spans the four periods, the units row says "%" once, and the
    columns write and tone the raw figures, aligned on the point.
    """
    columns = [
        Column(head, format=_percent, tone="auto", align_decimal=True, unit="%")
        for head in ("1 Year", "3 Year", "5 Year", "10 Year", "Since Incept.")
    ]
    rows = [TableRow(cells=[name, *values]) for name, *values in _RETURNS]
    nav_since = rows[0].cells[-1].value
    rows[0].cells[-1] = Cell(f"{_percent(nav_since)}[^1]", value=nav_since, tone="positive")
    return DataTable(
        headers=["Basis", *columns],
        groups=[
            ColumnGroup("Share class"),
            ColumnGroup("Annualised", 4),
            ColumnGroup("Since launch"),
        ],
        rows=rows,
        notes=[_INCEPTION_NOTE],
        as_of=AS_OF,
        spacing=_RETURNS_SPACING,
    )


def _sign(value: str) -> str:
    """Green or red, read off the figure itself.

    Both returns tables colour from the sign rather than from a constant: a
    hardcoded green is right only until the first negative quarter, and that
    is precisely the release nobody re-reads the colours on.
    """
    return _LOSS if value.startswith("-") else _GAIN


def _facts() -> dict[str, Any]:
    """The document's own facts. Fixed, so the render never moves."""
    return {
        "language": "en-US",
        "firm_name": "Hermes Research",
        "campaign_name": f"{FUND} ({TICKER})",
        "department": "Index Strategies",
        "date_range": f"Fact Sheet as of {AS_OF}",
        "issue_label": TICKER,
        "current_year": "2026",
        "header_disclaimer": (
            "Illustrative sample only. This fund does not exist and these figures "
            "are not a record of any real portfolio."
        ),
        "theme": "classic",
        "size_theme": "dense",
        "font_theme": "classic",
    }


# --------------------------------------------------------------------------
# The two charts.
# --------------------------------------------------------------------------


def _matplotlib() -> Any:
    """
    Import matplotlib, or say what to install.

    The charts here are the ``[charts]`` extra, which ``pip install -e
    ".[dev]"`` deliberately does not bring. Raising the package's own
    ``BackendMissingError`` rather than a bare ``ImportError`` is what lets a
    caller -- and the examples test -- tell "this needs an extra" apart from
    "this example is broken".
    """
    try:
        import matplotlib

        matplotlib.use("Agg")
    except ImportError as exc:  # pragma: no cover - depends on the install
        raise BackendMissingError(
            "The fund factsheet plots two charts with matplotlib, which is an "
            'optional extra. Install it with: pip install "pyhermes[charts]"'
        ) from exc
    return matplotlib


def _growth_chart() -> Any:
    """Growth of $10,000, fund against benchmark, over ten years."""
    _matplotlib()
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    figure, axes = plt.subplots(figsize=(9.6, 2.1))
    axes.plot(_GROWTH_YEARS, _GROWTH_FUND, color="#2C3E50", linewidth=1.8, label=f"Fund ({TICKER})")
    axes.plot(
        _GROWTH_YEARS,
        _GROWTH_BENCH,
        color="#8FA6B8",
        linewidth=1.3,
        linestyle=(0, (4, 2)),
        label="Benchmark",
    )
    axes.fill_between(_GROWTH_YEARS, _GROWTH_FUND, 10000, color="#2C3E50", alpha=0.06)

    axes.set_ylim(8_000, 40_000)
    axes.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v / 1000:,.0f}k"))
    axes.set_xticks(_GROWTH_YEARS[::2])
    axes.tick_params(axis="both", labelsize=7, colors="#5A6B7B", length=0)
    axes.grid(axis="y", color="#E3E8EC", linewidth=0.7)
    axes.set_axisbelow(True)
    for edge in ("top", "right", "left"):
        axes.spines[edge].set_visible(False)
    axes.spines["bottom"].set_color("#C9D2D9")
    axes.legend(frameon=False, fontsize=7, loc="upper left", labelcolor="#3D4C5A")
    figure.tight_layout(pad=0.3)
    return figure


def _sector_chart() -> Any:
    """Sector weights as a horizontal bar chart, largest at the top."""
    _matplotlib()
    import matplotlib.pyplot as plt

    # barh draws index 0 at the bottom, so the series runs bottom-up:
    # "Other" on the floor, then the eight named sectors ascending, which
    # puts the largest at the top where the eye starts.
    shown = _SECTORS[:8]
    other = round(sum(weight for _, weight in _SECTORS[8:]), 1)
    names = ["Other"] + [name for name, _ in reversed(shown)]
    weights = [other] + [weight for _, weight in reversed(shown)]

    figure, axes = plt.subplots(figsize=(9.6, 1.8))
    positions = range(len(names))
    axes.barh(list(positions), weights, color="#2C3E50", height=0.62)
    for position, weight in zip(positions, weights, strict=True):
        axes.text(
            weight + 0.5, position, f"{weight:.1f}%", va="center", fontsize=7.2, color="#3D4C5A"
        )

    axes.set_yticks(list(positions))
    axes.set_yticklabels(names, fontsize=7.6, color="#3D4C5A")
    axes.set_xlim(0, 35)
    axes.set_xticks([])
    axes.tick_params(axis="y", length=0)
    for edge in ("top", "right", "bottom", "left"):
        axes.spines[edge].set_visible(False)
    figure.tight_layout(pad=0.3)
    return figure


# --------------------------------------------------------------------------
# The document.
# --------------------------------------------------------------------------


def _sheet_one() -> list[Container]:
    """The first sheet's sections: the fund at a glance, its growth and its returns."""
    from svc.data import chart_from_figure

    return [
        FullWidth(
            title=f"{FUND} ({TICKER})",
            highlight=True,
            content=CardGroup(
                [
                    KpiItem("NAV", "$54.18", "", "as of 30 Sep"),
                    KpiItem("YTD Return", "+12.45%", _GAIN, "NAV basis"),
                    KpiItem("Net Assets", "$4.82B", "", "fund total"),
                    KpiItem("Expense Ratio", "0.04%", "", "net, annual"),
                ],
                orientation=CardOrientation.HORIZONTAL,
            ),
        ),
        TwoColumn(
            ratio=TwoColumnRatio.EQUAL,
            title="Investment Objective and Fund Facts",
            left=TextBlock(
                "<p>The Fund seeks to track the investment results of an index "
                "composed of large-capitalization U.S. equities. It invests at "
                "least 90% of its assets in the securities of its benchmark and "
                "is rebalanced quarterly.</p>"
            ),
            right=DataTable(
                headers=["Fund Fact", "Value"],
                rows=[
                    TableRow(cells=["Ticker / Exchange", f"{TICKER} · NYSE Arca"]),
                    TableRow(cells=["Inception", "14 March 2012"]),
                    TableRow(cells=["Benchmark", "Hermes US Large-Cap Index"]),
                    TableRow(cells=["Holdings", "503"]),
                    TableRow(cells=["30-Day SEC Yield", "1.21%"]),
                    TableRow(cells=["Distributions", "Quarterly"]),
                ],
            ),
        ),
        FullWidth(
            title="Growth of $10,000",
            content=chart_from_figure(
                _growth_chart(),
                alt=(
                    "Growth of a $10,000 investment from 2016 to 2026, fund and "
                    "benchmark, rising from $10,000 to approximately $35,900"
                ),
                width=690,
            ),
        ),
        FullWidth(
            title="Average Annual Total Returns",
            content=_returns_table(),
        ),
        TwoColumn(
            ratio=TwoColumnRatio.EQUAL,
            title="Risk Statistics (3 Year) and Trading",
            left=DataTable(
                headers=["Statistic", "Fund", "Benchmark"],
                rows=[TableRow(cells=list(row)) for row in _RISK],
            ),
            right=DataTable(
                headers=["Trading", "Value"],
                rows=[TableRow(cells=list(row)) for row in _TRADING],
            ),
        ),
    ]


def _sheet_two() -> list[Container]:
    """The second sheet's: what the fund holds, then the disclosures, which must fit here."""
    from svc.data import chart_from_figure

    return [
        TwoColumn(
            ratio=TwoColumnRatio.EQUAL,
            title="Calendar Year Returns and Characteristics",
            left=DataTable(
                headers=["Year", "Fund", "Benchmark"],
                rows=[
                    TableRow(
                        cells=[year, fund, bench],
                        colors=["", _sign(fund), _sign(bench)],
                    )
                    for year, fund, bench in _CALENDAR
                ],
                spacing=_RETURNS_SPACING,
            ),
            right=DataTable(
                headers=["Characteristic", "Value"],
                rows=[TableRow(cells=list(row)) for row in _CHARACTERISTICS],
                spacing=_RETURNS_SPACING,
            ),
        ),
        TwoColumn(
            ratio=TwoColumnRatio.EQUAL,
            title="Fundamentals and Distributions",
            left=DataTable(
                headers=["Fundamental", "Value"],
                rows=[TableRow(cells=list(row)) for row in _FUNDAMENTALS],
            ),
            right=DataTable(
                headers=["Distribution", "Per Share"],
                rows=[TableRow(cells=list(row)) for row in _DISTRIBUTIONS],
            ),
        ),
        # Ten holdings as two fives. The row is then as tall as
        # five rows instead of ten, which is the whole reason the
        # disclosures still fit on this sheet.
        TwoColumn(
            ratio=TwoColumnRatio.EQUAL,
            title="Top 10 Holdings",
            left=DataTable(
                headers=["Holding", "Weight (%)"],
                rows=[TableRow(cells=[name, weight]) for name, weight in _TOP_HOLDINGS[:5]],
            ),
            right=DataTable(
                headers=["Holding", "Weight (%)"],
                rows=[TableRow(cells=[name, weight]) for name, weight in _TOP_HOLDINGS[5:]],
            ),
        ),
        FullWidth(
            title="Sector Weights (%) — top eight, remainder grouped",
            content=chart_from_figure(
                _sector_chart(),
                alt=(
                    "Sector weights: Information Technology 32.4%, "
                    "Financials 13.1%, Health Care 11.2%, and eight "
                    "further sectors totalling 100%"
                ),
                width=690,
            ),
        ),
        FullWidth(
            title="Important Information",
            content=TextBlock(
                "<p><strong>Illustrative sample only.</strong> The Hermes Core "
                "US Equity ETF does not exist; every figure is invented sample "
                "data chosen to be internally consistent. Nothing here is a "
                "record of any real portfolio, nor investment advice.</p>"
                "<p>Consider a fund's objectives, risks, charges and expenses before "
                "investing. One cannot invest directly in an index; ETF shares "
                "trade at market price, not NAV. Past performance does not "
                "guarantee future results.</p>"
            ),
        ),
    ]


def build(template_dir: Path | None = None) -> PagedDocument:
    """The two-sheet factsheet. Deterministic: same bytes every call."""
    document = PagedDocument(
        _facts(),
        template_dir=template_dir,
        medium=paged_medium(LETTER_PORTRAIT),
        # A factsheet opens on its data. No cover sheet, no contents sheet --
        # both would spend one of the two sheets the format allows.
        cover=EmptyCover(),
        contents=EmptyContentsPage(),
        # The disclosures live on sheet two, in the flow. A BackMatter
        # region would spend a third sheet saying the same thing.
        back_matter=EmptyBackMatter(),
        running_header=RunningHeader(
            label=f"{FUND} ({TICKER})",
            box="top-left",
            show_page_number=False,
        ),
        running_footer=RunningFooter(
            label=f"Illustrative sample — not a real fund · As of {AS_OF}",
            box="bottom-left",
            show_page_number=True,
        ),
    )

    # One page per sheet. A page opening the body never breaks before it,
    # so both are written the same way and the tree reads as the format does.
    return document.add_page(_sheet_one()).add_page(_sheet_two())


def main() -> None:
    """Render beside this file, and print what was written."""
    here = Path(__file__).parent
    html = build().save(here / "fund-factsheet.html")
    print(f"{html}  ({html.stat().st_size / 1024:.1f} KB)")

    try:
        from svc.pdf import page_count, save_pdf
    except ImportError:  # pragma: no cover - the extra is optional by design
        print('pdf skipped: install the extra with `pip install -e ".[pdf]"`')
        return
    from svc.pdf import PdfError

    try:
        pdf = save_pdf(build(), here / "fund-factsheet.pdf")
    except PdfError as exc:
        print(f"pdf skipped: {exc}")
        return
    sheets = page_count(build())
    print(f"{pdf}  ({pdf.stat().st_size / 1024:.1f} KB, {sheets} page(s))")
    if sheets != SHEETS:
        raise SystemExit(
            f"a factsheet is {SHEETS} sheets; this laid out to {sheets}. "
            "Trim a section or shorten a chart rather than accepting the drift."
        )


if __name__ == "__main__":
    main()
