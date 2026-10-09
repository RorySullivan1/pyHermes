"""
Daily Investment Note — a one-day portfolio note built to be read on a phone.

The shape a desk sends before the open: what happened, what drove the book,
and what we are doing about it, in that order.

- **A first paragraph** — the day in two sentences of market and two of portfolio.
- **Chart 1, cumulative return** — the portfolio against its benchmark over the
  last twenty sessions, with its key stated in HTML under the picture
  (``ChartBlock(legend=...)``), so the key survives Outlook's default of
  blocking images.
- **The contribution table** — the five largest contributors and three largest
  detractors, the rest grouped, and the portfolio as a total row. The figures
  arrive as numbers and the columns write and tone them, aligned on the point.
- **Chart 2, contribution by sector** — a diverging bar, gains in the theme's
  positive tone and losses in its negative, read off ``chart_style``.
- **A second paragraph** — positioning and what we are watching.

**Built for a phone.** Every section is ``FullWidth``, so nothing has a column
to collapse at 375px. The table holds to four columns, which fit a phone
without a horizontal scroll. The two charts are drawn at a 5.2 in figure width
with 12 pt labels, so when a phone scales the 616px picture down to its
width the type stays about 11px tall rather than shrinking to a smudge.

**The portfolio is fictional** and every figure is illustrative sample data
chosen to be internally consistent: each contribution is weight × return.

Run it directly to (re)generate ``daily-investment-note.html`` next to this file:

    python examples/daily-investment-note/daily-investment-note.py

The charts are ``cid:`` images, which resolve inside a MIME message rather than
a browser; ``python -m qa.preview examples/daily-investment-note/daily-investment-note.py:build
--screenshot`` photographs it with the images inlined, at desktop and phone width.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pyhermes.builder import (
    ChartBlock,
    DataTable,
    Email,
    EmailBuilder,
    Footer,
    FullWidth,
    TextBlock,
)
from pyhermes.builder.enums import RowKind
from pyhermes.builder.exhibits import Legend, LegendEntry
from pyhermes.builder.formats import number
from pyhermes.builder.models import Column, TableRow
from pyhermes.data.exceptions import BackendMissingError

# --------------------------------------------------------------------------
# The numbers, in one place: tomorrow's note is this file with new figures.
# --------------------------------------------------------------------------

AS_OF = "8 October 2026"
PORTFOLIO = "Hermes Global Equity"
THEME = "classic"

#: The body's display width in px; the charts are drawn at twice it.
_CHART_WIDTH = 616

#: Cumulative total return, in percent, over the last twenty sessions.
_SESSIONS = list(range(1, 21))
_PORTFOLIO_PATH = [
    0.00, 0.31, 0.18, 0.52, 0.47, 0.86, 1.12, 0.94, 1.30, 1.58,
    1.41, 1.77, 2.05, 1.89, 2.21, 2.48, 2.36, 2.70, 2.84, 3.46,
]  # fmt: skip
_BENCHMARK_PATH = [
    0.00, 0.24, 0.20, 0.41, 0.33, 0.66, 0.85, 0.71, 1.02, 1.22,
    1.10, 1.38, 1.57, 1.46, 1.71, 1.90, 1.83, 2.10, 2.19, 2.60,
]  # fmt: skip

#: Today's largest contributors and detractors: (holding, weight %, return %).
_CONTRIBUTORS = [
    ("NVIDIA", 6.1, 2.85),
    ("Microsoft", 5.4, 1.62),
    ("ASML Holding", 2.3, 3.10),
    ("JPMorgan Chase", 2.8, 1.48),
    ("Taiwan Semiconductor", 3.2, 1.21),
]
_DETRACTORS = [
    ("Novo Nordisk", 1.9, -2.64),
    ("Exxon Mobil", 2.0, -1.35),
    ("LVMH", 1.6, -1.12),
]

#: The portfolio's return today, in percent; "Other holdings" is the residual.
_PORTFOLIO_RETURN = 0.62

#: Contribution by sector, in bps, largest gain first. Sums to the 62 bps above.
_SECTORS = [
    ("Info. Tech.", 42.6),
    ("Financials", 11.2),
    ("Industrials", 6.4),
    ("Comm. Services", 5.1),
    ("Cons. Disc.", 3.9),
    ("Materials", 1.3),
    ("Utilities", -0.6),
    ("Energy", -3.1),
    ("Health Care", -4.8),
]

_NOTE_ON_MARKETS = (
    "<p><strong>Semiconductors carried the tape.</strong> Global equities rose 0.41% "
    "as a firmer-than-expected order book from the lithography makers lifted the "
    "chip complex for a third session, and Treasury yields slipped 4 bps after a "
    "softer services print. Energy lagged with crude, and European luxury extended "
    "its slide on weaker Chinese travel data. The portfolio returned "
    "<strong>+0.62%</strong>, <strong>21 bps</strong> "
    "ahead of the benchmark, taking the twenty-session lead to 86 bps. NVIDIA, "
    "ASML and Microsoft added 33 bps between them; health care cost "
    "5 bps, all of it Novo Nordisk.</p>"
)

_NOTE_ON_POSITIONING = (
    "<p><strong>We are taking some semiconductor profit.</strong> After a 9% run in "
    "the group over twenty sessions, technology is now 4.2 points overweight, the "
    "top of our range, so we trim NVIDIA by 50 bps at the open and add to "
    "JPMorgan ahead of next week's bank earnings, where net interest margin "
    "guidance is the swing factor. The healthcare overweight stays: the Novo move "
    "is sentiment on a competitor's trial read-out, not a change in its own data. "
    "Tomorrow brings US CPI at 8:30 ET. A core print at or below 0.2% would "
    "support the duration-sensitive growth names we hold; a hot number is the main "
    "risk to today's leadership, and we would add to energy rather than chase.</p>"
)


# --------------------------------------------------------------------------
# The contribution table.
# --------------------------------------------------------------------------


def _bps_of(weight: float, ret: float) -> float:
    """A holding's contribution in bps: weight % × return %."""
    return round(weight * ret, 1)


def _contribution_table() -> DataTable:
    """
    Contributors, detractors, the residual and the total, in four columns.

    Four is what a 375px phone holds without scrolling sideways; a fifth
    (active weight, say) belongs in the desktop-only attachment, not here.
    """
    shown = _CONTRIBUTORS + _DETRACTORS
    total_bps = _PORTFOLIO_RETURN * 100
    other_weight = round(100 - sum(weight for _, weight, _ in shown), 1)
    other_bps = round(total_bps - sum(_bps_of(w, r) for _, w, r in shown), 1)
    other_return = round(other_bps / other_weight, 2)

    def data(name: str, weight: float, ret: float) -> TableRow:
        return TableRow(cells=[name, weight, ret, _bps_of(weight, ret)])

    rows = [
        TableRow(cells=["Top contributors"], kind=RowKind.SUBHEAD),
        *(data(*holding) for holding in _CONTRIBUTORS),
        TableRow(cells=["Top detractors"], kind=RowKind.SUBHEAD),
        *(data(*holding) for holding in _DETRACTORS),
        TableRow(cells=["Other holdings", other_weight, other_return, other_bps]),
        TableRow(
            cells=[PORTFOLIO, 100.0, _PORTFOLIO_RETURN, total_bps],
            kind=RowKind.TOTAL,
        ),
    ]
    return DataTable(
        headers=[
            Column("Holding", width=3),
            Column("Weight", format=lambda v: number(v, 1), align_decimal=True, unit="%"),
            Column(
                "Return",
                format=lambda v: number(v, 2, sign=True),
                tone="auto",
                align_decimal=True,
                unit="%",
            ),
            Column(
                "Contrib.",
                format=lambda v: number(v, 1, sign=True),
                tone="auto",
                align_decimal=True,
                unit="bps",
            ),
        ],
        rows=rows,
        source="Hermes Research; illustrative sample data",
        subtitle=f"Contribution to return, {AS_OF}",
    )


# --------------------------------------------------------------------------
# The two charts.
# --------------------------------------------------------------------------


def _pyplot() -> Any:
    """pyplot, or the package's own error naming the ``[charts]`` extra."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover - depends on the install
        raise BackendMissingError(
            "The daily note plots two charts with matplotlib, which is an optional "
            'extra. Install it with: pip install "pyhermes[charts]"'
        ) from exc
    return plt


def _performance_chart() -> ChartBlock:
    """Cumulative return over twenty sessions, the key stated in HTML beneath it."""
    from pyhermes.data import chart_style, image_from_figure

    plt = _pyplot()
    style = chart_style(THEME)
    with plt.rc_context(style):
        figure, axes = plt.subplots(figsize=(5.2, 2.6))
        axes.plot(_SESSIONS, _PORTFOLIO_PATH, color=style.series[0], linewidth=2.2)
        axes.plot(_SESSIONS, _BENCHMARK_PATH, color=style.series[1], linewidth=1.6)
        axes.fill_between(
            _SESSIONS, _PORTFOLIO_PATH, _BENCHMARK_PATH, color=style.positive, alpha=0.12
        )
        # The end values, labelled at the line ends, so the reader needs no axis.
        for path, colour in (
            (_PORTFOLIO_PATH, style.series[0]),
            (_BENCHMARK_PATH, style.series[1]),
        ):
            axes.annotate(
                f"{path[-1]:+.2f}%",
                (_SESSIONS[-1], path[-1]),
                xytext=(5, 0),
                textcoords="offset points",
                va="center",
                fontsize=12,
                fontweight="bold",
                color=colour,
            )
        axes.set_xlim(1, 23)
        axes.set_xticks([1, 10, 20])
        axes.set_xticklabels(["-20d", "-10d", "Today"])
        axes.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%"))
        axes.set_yticks([0, 1, 2, 3])
        axes.tick_params(axis="both", labelsize=12, length=0)
        axes.grid(axis="y", linewidth=0.6, alpha=0.5)
        axes.set_axisbelow(True)
        for edge in ("top", "right", "left"):
            axes.spines[edge].set_visible(False)
        figure.tight_layout(pad=0.4)
    image = image_from_figure(
        figure,
        alt=(
            "Cumulative return over the last twenty sessions: the portfolio up 3.46%, "
            "the benchmark up 2.60%"
        ),
        width=_CHART_WIDTH,
    )
    plt.close(figure)
    return ChartBlock(
        image,
        subtitle="Cumulative total return, last 20 sessions",
        source="Hermes Research; illustrative sample data",
        legend=Legend(
            [LegendEntry(PORTFOLIO, series=0), LegendEntry("Benchmark (MSCI ACWI)", series=1)]
        ),
    )


def _sector_chart() -> ChartBlock:
    """Today's contribution by sector, a diverging bar coloured by sign."""
    from pyhermes.data import chart_from_figure, chart_style

    plt = _pyplot()
    style = chart_style(THEME)
    # barh draws index 0 at the bottom, so reverse: the largest gain sits on top.
    names = [name for name, _ in reversed(_SECTORS)]
    values = [bps for _, bps in reversed(_SECTORS)]
    with plt.rc_context(style):
        figure, axes = plt.subplots(figsize=(5.2, 3.3))
        positions = list(range(len(names)))
        colours = [style.positive if v >= 0 else style.negative for v in values]
        axes.barh(positions, values, color=colours, height=0.66)
        for position, value in zip(positions, values, strict=True):
            axes.text(
                value + (0.8 if value >= 0 else -0.8),
                position,
                f"{value:+.1f}",
                va="center",
                ha="left" if value >= 0 else "right",
                fontsize=12,
            )
        axes.axvline(0, linewidth=0.9, color=style["axes.edgecolor"])
        axes.set_yticks(positions)
        axes.set_yticklabels(names, fontsize=12)
        axes.set_xlim(-12, 54)
        axes.set_xticks([])
        axes.tick_params(axis="y", length=0)
        for edge in ("top", "right", "bottom", "left"):
            axes.spines[edge].set_visible(False)
        figure.tight_layout(pad=0.4)
    block = chart_from_figure(
        figure,
        alt=(
            "Contribution by sector in basis points: Information Technology +42.6, "
            "Financials +11.2, Industrials +6.4; Health Care -4.8 and Energy -3.1 detracted"
        ),
        width=_CHART_WIDTH,
        subtitle="Contribution to return by sector, bps",
        source="Hermes Research; illustrative sample data",
    )
    plt.close(figure)
    return block


# --------------------------------------------------------------------------
# The email.
# --------------------------------------------------------------------------


def build(template_dir: Path | None = None) -> Email:
    """Build the daily note. Deterministic: same bytes every call."""
    return (
        EmailBuilder(template_dir=template_dir)
        .metadata(
            {
                "email_subject": f"Daily Note — {AS_OF}: +62 bps, 21 ahead",
                "preheader_text": (
                    "Chips lead for a third day; we trim NVIDIA and add JPMorgan into CPI."
                ),
                "firm_name": "Hermes Research",
                "campaign_name": "Daily Investment Note",
                "department": "Global Equity",
                "date_range": f"Close of {AS_OF}",
                "theme": THEME,
            }
        )
        .footer(
            Footer(
                background_color="#F2F1EE",
                border=True,
                disclaimer=(
                    "Illustrative sample only: the portfolio is fictional and every "
                    "figure is invented. Not investment advice. Past performance does "
                    "not guarantee future results."
                ),
            )
        )
        .section(FullWidth(title="The Day in Brief", content=TextBlock(_NOTE_ON_MARKETS)))
        .section(FullWidth(title="Performance", content=_performance_chart()))
        .section(FullWidth(title="What Drove Returns", content=_contribution_table()))
        .section(FullWidth(title="By Sector", content=_sector_chart()))
        .section(
            FullWidth(
                title="Positioning and the Day Ahead", content=TextBlock(_NOTE_ON_POSITIONING)
            )
        )
        .build()
    )


if __name__ == "__main__":
    output = Path(__file__).with_suffix(".html")
    email = build()
    email.save(output)
    print(f"Wrote {output}  ({output.stat().st_size / 1024:.1f} KB)")
