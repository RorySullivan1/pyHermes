"""
Every ``DataTable`` axis at once — the fixture that closes epic #116.

#117 gave columns an alignment and a kind, #118 gave cells a colour, a
background and an override, #119 gave rows a kind, and #120 gave the table a
name and row headers. Each landed with its own tests, and each is invisible
in a golden until an email actually uses it — so this is the email a
*cross-axis* regression shows up in, and the one that stops these properties
being added, never exercised, and quietly rotting.

Two tables, because one cannot carry the whole surface honestly:

* **the sleeve table** — a caption, a second **text** column (unreachable
  before #117 at any argument), a **centred** column, per-cell colours *and*
  backgrounds, `subhead` groupings and a `total`. Its first column is text,
  so every row gets a ``th scope="row"``;
* **the ranking table** — a **numeric first column**, which is the only way
  a golden can show that the row-header rule keys on the column's resolved
  *kind* rather than on position. Without it, "the first cell is a row
  header" and "a text first column is a row header" pin identically.

**The body is short on purpose.** ``kitchen_sink`` exercises the component
library; a fat body here would make this golden noisy for reasons unrelated
to the table, which is ``custom_banner``'s reasoning and applies unchanged.

Theme, size and font stay at their defaults for the same reason: a preset
moving alongside a table axis would leave a diff nobody can attribute, and
the three design axes already have fixtures of their own.
"""

from __future__ import annotations

from pathlib import Path

from svc.builder import DataTable, Email, EmailBuilder, FullWidth, TextBlock
from svc.builder.models import Cell, Column, TableRow

#: Gains and losses, as the caller's claim about a figure rather than a
#: styling choice — the justification that admits #118's colours at all.
_GAIN = "#4A7C59"
_LOSS = "#B85450"

#: A shaded cell says something the number alone does not: this mark is
#: stale. Same channel as the text colour, same kind of claim.
_STALE = "#FBF3E2"


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
