"""
Every composition axis at once (#261), so a cross-axis regression is visible.

Several blocks in one cell (a ``Stack``), a split nested inside a cell (``Columns``), a
split at weights no preset names, and a four-column row. The body is otherwise plain,
and theme, size and font stay default, so every line of its golden is about composition.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pyhermes.builder import (
    CardGroup,
    Columns,
    DataTable,
    Email,
    EmailBuilder,
    FourColumn,
    FullWidth,
    Stack,
    TextBlock,
    TwoColumn,
)
from pyhermes.builder.models import KpiItem, TableRow

_YEAR = "2026"


def _metadata() -> dict[str, Any]:
    return {
        "email_subject": "Composed Layout — blocks inside blocks",
        "preheader_text": "One email exercising every composition axis at once.",
        "firm_name": "Hermes Research",
        "campaign_name": "composed-layout",
        "date_range": "Week ending 2 October",
        "issue_label": "Issue 010",
        "current_year": _YEAR,
        "unsubscribe_url": "https://example.com/unsubscribe",
        "view_in_browser_url": "https://example.com/archive/010",
    }


def _returns() -> DataTable:
    return DataTable(
        ["Factor", "1M", "YTD"],
        [TableRow(["Value", "+1.8%", "+7.4%"]), TableRow(["Momentum", "-0.4%", "+3.1%"])],
        caption="Style factor returns",
        label="Exhibit",
        source="Hermes Research",
    )


def build(template_dir: Path | None = None) -> Email:
    """Build the composed-layout email. Deterministic: same bytes every call."""
    return (
        EmailBuilder(template_dir=template_dir)
        .metadata(_metadata())
        # A paragraph, the table it introduces and a note, under one title (#262).
        .section(
            FullWidth(
                title="Text, Table, Note",
                content=Stack(
                    [
                        TextBlock("<p>Value led again this month; momentum reversed late.</p>"),
                        _returns(),
                        TextBlock("<p>Returns are gross of fees.</p>"),
                    ]
                ),
            )
        )
        # A split at weights no preset names, a stack in its narrow column (#264).
        .section(
            TwoColumn(
                ratio=(60, 40),
                title="Sixty-Forty",
                left=TextBlock(
                    "<p>The wider column holds the argument, at weights no preset "
                    "names: sixty and forty.</p>"
                ),
                right=Stack(
                    [
                        CardGroup(
                            [KpiItem("Duration", "6.2y"), KpiItem("Yield", "4.1%")],
                            orientation="vertical",
                        ),
                        TextBlock("<p>As of Friday's close.</p>"),
                    ]
                ),
            )
        )
        # The epic's acceptance case: in one column of a split, a stack of text, a
        # table and figures, with a two-up split nested inside it (#263).
        .section(
            TwoColumn(
                ratio="30-70",
                title="Nested",
                left=TextBlock("<p>The narrow column: a view in one line.</p>"),
                right=Stack(
                    [
                        TextBlock("<p>The wide column holds a stack.</p>"),
                        _returns(),
                        Columns(
                            [
                                CardGroup(
                                    [KpiItem("UST 2Y", "3.91%"), KpiItem("UST 10Y", "4.28%")],
                                    orientation="vertical",
                                ),
                                TextBlock("<p>Two columns inside a column.</p>"),
                            ],
                            ratio=(1, 2),
                        ),
                    ]
                ),
            )
        )
        # Four columns, one left empty (#264).
        .section(
            FourColumn(
                [
                    TextBlock("<p><b>Rates</b><br>Long.</p>"),
                    TextBlock("<p><b>Credit</b><br>Neutral.</p>"),
                    None,
                    TextBlock("<p><b>FX</b><br>Short USD.</p>"),
                ],
                title="Four Across",
            )
        )
        .build()
    )
