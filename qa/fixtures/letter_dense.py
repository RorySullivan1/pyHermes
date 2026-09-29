"""
A two-sheet Letter portrait document at ``dense``: the fixture for epic #209.

The print density (#211) and the per-object override (#213 to #215) together,
on the medium they were made for. Each ``spacing`` below sits at a value no
preset holds, so the golden pins every one, and ``SHEETS`` is what the PDF
test holds the layout to.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pyhermes.builder import (
    CardGroup,
    DataTable,
    FullWidth,
    NumberedList,
    Spacing,
    TextBlock,
    TwoColumn,
)
from pyhermes.builder.enums import CardOrientation, TwoColumnRatio
from pyhermes.builder.models import Column, KpiItem, NumberedItem, TableRow
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

_GAIN = "#4A7C59"
_LOSS = "#B85450"

#: The sheets this document lays out to; the PDF test asserts it.
SHEETS = 2

#: The yield table's columns, which the long-table test reads back.
TENORS = ("Market", "3M", "2Y", "5Y", "10Y", "30Y", "2s10s")

_MARKETS = [
    ("United States", "5.21", "4.62", "4.18", "4.21", "4.39", "-41"),
    ("Germany", "3.62", "2.88", "2.41", "2.46", "2.69", "-42"),
    ("United Kingdom", "5.08", "4.31", "3.99", "4.12", "4.61", "-19"),
    ("Japan", "0.08", "0.36", "0.62", "0.93", "2.07", "+57"),
    ("Canada", "4.71", "3.94", "3.41", "3.38", "3.36", "-56"),
    ("Australia", "4.38", "3.79", "3.83", "4.18", "4.61", "+39"),
    ("France", "3.66", "2.94", "2.79", "3.03", "3.51", "+9"),
    ("Italy", "3.71", "3.21", "3.28", "3.81", "4.47", "+60"),
]


def facts() -> dict[str, Any]:
    """Every ``DocumentMetadata`` fact, at the density the fixture exists for."""
    return {
        "language": "en-US",
        "header_disclaimer": "For professional investors only.",
        "firm_name": "Hermes Research",
        "campaign_name": "Rates Monitor",
        "department": "Global Rates",
        "date_range": "Week ending 25 September 2026",
        "issue_label": "Monitor 39",
        "current_year": "2026",
        "theme": "classic",
        "size_theme": "dense",
        "font_theme": "classic",
    }


def build(template_dir: Path | None = None) -> PagedDocument:
    """Build the monitor. Deterministic: same bytes every call."""
    document = PagedDocument(
        facts(),
        template_dir=template_dir,
        medium=paged_medium(LETTER_PORTRAIT),
        cover=EmptyCover(),
        contents=EmptyContentsPage(),
        running_header=EmptyRunningHeader(),
        running_footer=RunningFooter(
            label="Hermes Research · Rates Monitor", box="bottom-left", show_page_number=True
        ),
        back_matter=EmptyBackMatter(),
    )
    document.add_page(_first_sheet(), spacing={"section_title_top": 7})
    document.add_page(_second_sheet())
    return document


def _yield_table(caption: str, spacing: Spacing | None = None) -> DataTable:
    """Eight markets across the curve, the curve's slope coloured by its sign."""
    rows = [
        TableRow(
            cells=list(market),
            colors=["", "", "", "", "", "", _GAIN if market[-1].startswith("+") else _LOSS],
        )
        for market in _MARKETS
    ]
    return DataTable(
        headers=[Column(tenor) for tenor in TENORS],
        rows=rows,
        source="Hermes Research, closing mid yields",
        as_of="25 September 2026",
        caption=caption,
        spacing=spacing,
    )


def _first_sheet() -> list[Any]:
    return [
        FullWidth(
            title="The Week in Rates",
            content=CardGroup(
                [
                    KpiItem("UST 10Y", "4.21%", _LOSS, "+6 bps"),
                    KpiItem("Bund 10Y", "2.46%", _GAIN, "-3 bps"),
                    KpiItem("Gilt 10Y", "4.12%", _LOSS, "+2 bps"),
                    KpiItem("JGB 10Y", "0.93%", _LOSS, "+4 bps"),
                ],
                orientation=CardOrientation.HORIZONTAL,
                spacing={"kpi_pad_y": 5, "card_label_gap": 2},
            ),
        ),
        TwoColumn(
            ratio=TwoColumnRatio.EQUAL,
            title="Positioning",
            spacing=Spacing(column_bottom=4, gutter=14),
            left=TextBlock(
                "<p>Front ends repriced the first cut later again, and five of the "
                "eight curves flattened from the front. Duration stays long.</p>"
            ),
            right=TextBlock(
                "<p>Japan is the exception: the long end sold off as the central "
                "bank stepped back from the market, and the curve steepened.</p>"
            ),
        ),
        FullWidth(
            title="Government Yields",
            spacing={"pad_x": 6, "content_bottom": 4},
            content=_yield_table("Yields and curve slope", Spacing(table_cell_pad=3)),
        ),
    ]


def _second_sheet() -> list[Any]:
    return [
        FullWidth(
            title="Yields a Week Earlier",
            content=_yield_table("The same markets, one week before"),
        ),
        FullWidth(
            title="What We Are Watching",
            content=NumberedList(
                [
                    NumberedItem("1", "Payrolls", "<p>A soft print brings the cut forward.</p>"),
                    NumberedItem("2", "Bund supply", "<p>Heavy issuance into quarter end.</p>"),
                    NumberedItem("3", "JGB auctions", "<p>Demand at the long end is thin.</p>"),
                ],
                spacing={"block_gap": 5, "list_title_gap": 2},
            ),
        ),
    ]
