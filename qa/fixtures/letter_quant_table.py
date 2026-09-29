"""
A Letter portrait returns table that crosses sheets: the fixture for epic #217.

Every word the epic added, on the medium where a tiered head has something to
prove: grouped heads, a units row, decimal-aligned figures a column formats
from raw numbers, a marker on one figure, a heat-scaled column and a bar.
``SHEETS`` is what the PDF test holds the layout to.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pyhermes.builder import ColumnGroup, DataTable, FullWidth, HeatScale, TextBlock
from pyhermes.builder.formats import pct
from pyhermes.builder.models import Cell, Column, TableRow
from pyhermes.builder.sizing import LETTER_PORTRAIT
from pyhermes.document import (
    EmptyBackMatter,
    EmptyContentsPage,
    EmptyCover,
    EmptyRunningHeader,
    PagedDocument,
    RunningFooter,
    paged_medium,
)

#: The sheets this document lays out to; the PDF test asserts it.
SHEETS = 2

#: The group labels and a unit, which the PDF test finds on every table sheet.
GROUPS = [ColumnGroup("Style and region"), ColumnGroup("Annualised", 4), ColumnGroup("Book", 1)]
UNITS = ["% of NAV"]

#: The strategies, one row each; the PDF test finds the table's sheets by them.
STRATEGIES = [
    f"{style} {region}"
    for style in ("Value", "Momentum", "Quality", "Low volatility")
    for region in ("US", "Europe", "Japan", "EM", "Global")
]


def _one_place(value: float) -> str:
    return pct(value, 1, sign=True)


def _trimmed(value: float) -> str:
    """Two places with trailing zeros dropped, so the points have work to do."""
    number, _, suffix = pct(value, 2, sign=True).partition("%")
    return number.rstrip("0").rstrip(".") + "%" + suffix


def _two_places(value: float) -> str:
    return pct(value, 2)


def _figures(n: int) -> list[float]:
    """Five deterministic figures for row ``n``: four returns and a weight."""
    return [((n * 37) % 23 - 9) / 100, ((n * 13) % 170 - 50) / 1000,
            ((n * 7) % 110 - 20) / 1000, ((n * 5) % 90) / 1000,
            (1 + (n * 11) % 29) / 1000]  # fmt: skip


def _row(n: int, name: str) -> TableRow:
    one, three, five, ten, weight = _figures(n)
    if n == 0:
        # One figure flagged, not the table: its note floats to the sheet foot.
        return TableRow([name, one, three, five, Cell("n/a[^1]", value=0.0), weight])
    return TableRow([name, one, three, five, ten, weight])


def _returns_table() -> DataTable:
    return DataTable(
        caption="Factor strategy returns and book weights",
        headers=[
            "Strategy",
            Column(
                "1Y", format=_one_place, tone="auto", scale=HeatScale(-0.1, 0.14, mid=0), unit="%"
            ),
            Column("3Y", format=_trimmed, tone="auto", align_decimal=True, unit="%"),
            Column("5Y", format=_trimmed, align_decimal=True, unit="%"),
            Column("10Y", format=_trimmed, align_decimal=True, unit="%"),
            Column("Weight", format=_two_places, bar=True, unit="% of NAV"),
        ],
        groups=GROUPS,
        rows=[TableRow(["Developed"], kind="subhead")]
        + [_row(n, name) for n, name in enumerate(STRATEGIES)]
        + [TableRow(["Total", "", "", "", "", "100.00%"], kind="total")],
        notes=["Value US has no ten-year record; the series starts in 2019."],
        source="Hermes Research, factor model",
        as_of="25 September 2026",
        disclosure="Returns are gross of costs and shown for illustration only.",
    )


def facts() -> dict[str, Any]:
    """Every ``DocumentMetadata`` fact, at the defaults the table is read in."""
    return {
        "language": "en-US",
        "header_disclaimer": "For professional investors only.",
        "firm_name": "Hermes Research",
        "campaign_name": "Factor Book",
        "department": "Quantitative Strategies",
        "date_range": "September 2026",
        "issue_label": "Book 09",
        "current_year": "2026",
    }


def build(template_dir: Path | None = None) -> PagedDocument:
    """Build the factor book. Deterministic: same bytes every call."""
    document = PagedDocument(
        facts(),
        template_dir=template_dir,
        medium=paged_medium(LETTER_PORTRAIT),
        cover=EmptyCover(),
        contents=EmptyContentsPage(),
        running_header=EmptyRunningHeader(),
        running_footer=RunningFooter(
            label="Hermes Research · Factor Book", box="bottom-left", show_page_number=True
        ),
        back_matter=EmptyBackMatter(),
    )
    document.add_section(
        FullWidth(
            title="The Book",
            content=TextBlock(
                "<p>Twenty strategies across four styles and five regions. The one-year "
                "column is tinted by the number itself, the weight is drawn as a bar, and "
                "every figure column lines up on its point.</p>"
            ),
        )
    )
    document.add_section(FullWidth(title="Returns", content=_returns_table()))
    return document
