"""
Every ``DataTable`` axis at once (#116), so a cross-axis regression is visible.

**Two tables on purpose.** One carries the expressive surface — per-column
``kind`` and ``align``, per-cell colour and background, row kinds, a caption
and row headers. The other is a plain table of bare strings, which is what
pins that none of the new machinery changed the default rendering. A third,
the quantitative table, carries epic #217's words: groups, a marked cell,
columns that format their own raw figures, a decimal-aligned column, units,
a bar and a diverging heat scale.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder import DataTable, Email, EmailBuilder, FullWidth, HeatScale, TextBlock
from pyhermes.builder.formats import pct
from pyhermes.builder.models import Cell, Column, ColumnGroup, TableRow

#: Gains and losses, as the caller's claim about a figure rather than a
#: styling choice — the justification that admits #118's colours at all.
_GAIN = "#4A7C59"
_LOSS = "#B85450"

#: A shaded cell says something the number alone does not: this mark is
#: stale. Same channel as the text colour, same kind of claim.
_STALE = "#FBF3E2"


def _annualised(value: float) -> str:
    return pct(value, 1)


def _quantitative_table() -> DataTable:
    """Epic #217's table: the words a quantitative desk writes a table in."""
    return DataTable(
        caption="Annualised returns by share class",
        headers=[
            "Class",
            Column("1Y", format=_annualised, tone="auto", unit="%", bar=True),
            Column("3Y", format=_annualised, tone="auto", align_decimal=True),
            Column(
                "Since launch[^1]",
                format=_annualised,
                unit="% pa",
                scale=HeatScale(0.04, 0.08, mid=0.06),
            ),
        ],
        groups=[ColumnGroup("Share class"), ColumnGroup("Annualised", 3)],
        rows=[
            # Written to two places, so the aligned column has a point to align.
            TableRow(["Accumulation", 0.0452, Cell("6.12%", value=0.0612), 0.0725]),
            TableRow(["Income", -0.0031, 0.1405, Cell("6.9%[^2]", value=0.069)]),
            TableRow(["Hedged", 0.0118, "n/a", 0.0512]),
        ],
        notes=["Launched 3 March 2014.", "The income class launched a year later."],
        source="Hermes Research",
    )


def build(template_dir: Path | None = None) -> Email:
    """Build the rich-table email. Deterministic: same bytes every call."""
    return (
        EmailBuilder(template_dir=template_dir)
        .metadata(
            {
                "email_subject": "Rich Table — every column, row and cell axis",
                "preheader_text": "Alignment, kinds, per-cell colour and a named table.",
                "firm_name": "Hermes Research",
                "campaign_name": "rich-table",
                "department": "Portfolio Analytics",
                "date_range": "Week ending 24 August",
                "issue_label": "Issue 007",
                "header_disclaimer": "For illustrative purposes. Not investment advice.",
                "current_year": "2026",
                "unsubscribe_url": "https://example.com/unsubscribe",
                "view_in_browser_url": "https://example.com/archive/007",
            }
        )
        .section(
            FullWidth(
                title="Sleeve Performance",
                content=DataTable(
                    caption="Sleeve performance, gross of fees",
                    subtitle="Grouped by asset class",
                    headers=[
                        "Sleeve",
                        # A second text column: right-aligned, mono and bold
                        # before #117, whatever it held.
                        Column("Manager", kind="text"),
                        Column("Weight", align="center"),
                        "1M",
                        "YTD",
                    ],
                    rows=[
                        TableRow(["Equities"], kind="subhead"),
                        TableRow(
                            ["Global core", "Ashford", "18%", "+1.8%", "+7.4%"],
                            colors=["", "", "", _GAIN, _GAIN],
                        ),
                        TableRow(
                            [
                                "Emerging markets",
                                "Kestrel",
                                "6%",
                                Cell("-0.4%", color=_LOSS),
                                Cell("+11.2%", color=_GAIN, background=_STALE),
                            ]
                        ),
                        TableRow(["Fixed income"], kind="subhead"),
                        TableRow(
                            ["Sovereign", "In-house", "41%", "+0.3%", "+1.9%"],
                            colors=["", "", "", _GAIN, _GAIN],
                        ),
                        TableRow(
                            [
                                "Credit",
                                "Marlow",
                                "35%",
                                Cell("-0.2%", color=_LOSS),
                                # An override: this one figure reads left, to
                                # sit under the qualifier beside it.
                                Cell("+3.6%", color=_GAIN, align="left"),
                            ]
                        ),
                        TableRow(
                            ["Total", "", "100%", "+0.6%", "+4.1%"],
                            colors=["", "", "", _GAIN, _GAIN],
                            kind="total",
                        ),
                    ],
                    source="Hermes Research",
                    as_of="24 August 2026",
                ),
            )
        )
        .section(
            FullWidth(
                title="Contribution Ranking",
                content=DataTable(
                    caption="Top contributors by rank",
                    headers=[
                        # Numeric first column: not a row header, which is
                        # what proves the rule keys on kind rather than
                        # position.
                        Column("Rank", kind="numeric"),
                        Column("Sleeve", kind="text"),
                        "bps",
                    ],
                    rows=[
                        TableRow(["1", "Sovereign", "+42"], colors=["", "", _GAIN]),
                        TableRow(["2", "Global core", "+31"], colors=["", "", _GAIN]),
                        TableRow(["3", "Credit", "-8"], colors=["", "", _LOSS]),
                    ],
                ),
            )
        )
        .section(FullWidth(title="Share Class Returns", content=_quantitative_table()))
        .section(
            FullWidth(
                content=TextBlock(
                    "<p>Weights are as of the close on the as-of date. A shaded cell "
                    "marks a stale valuation.</p>"
                ),
            )
        )
        .build()
    )
