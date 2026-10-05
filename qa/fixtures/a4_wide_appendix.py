"""
Page-level presentation on paper (#340): a portrait report with one wide appendix.

A landscape page holds a holdings table too wide for a portrait column (#341),
and the report returns to portrait after it. ``a4_portrait``'s sheet counts are
claims other tests make, so the page-level features get a document of their
own. Same facts and regions, so only the body and the stamp differ.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder import Aside, DataTable, FullWidth, TextBlock
from pyhermes.builder.models import TableRow
from pyhermes.document import Page, PagedDocument

from . import _paged

#: The wide table's headers, which the PDF test finds on the landscape sheet.
HEADERS = [
    "Issue",
    "Sector",
    "Rating",
    "Coupon",
    "Maturity",
    "Weight",
    "Yield",
    "Duration",
    "Spread",
    "Active",
]

#: The status set across every sheet (#342).
STAMP = "DRAFT"

#: The aside's copy, which the PDF test finds beside the summary's prose.
ASIDE = "The holding's weight less its weight in the benchmark."

#: The sections' titles, in reading order, which the PDF test finds by sheet.
SUMMARY = "Summary"
APPENDIX = "Holdings in Full"
METHOD = "Method"

_ISSUERS = ["UKT", "Vodafone", "HSBC", "Tesco", "BT", "National Grid", "Aviva", "Lloyds"]


def build(template_dir: Path | None = None) -> PagedDocument:
    """Build the report. Deterministic: same bytes every call."""
    facts = {**_paged.facts(), "stamp": STAMP}
    document = PagedDocument(facts, template_dir=template_dir, **_paged.regions())
    for section in sections():
        document.add_section(section)
    return document


def sections() -> list[FullWidth | Page]:
    """A portrait summary, the landscape appendix, and a portrait note after it."""
    return [
        FullWidth(
            title=SUMMARY,
            content=TextBlock(
                "<p>The book ran long duration through the quarter, and the curve did "
                'most of the work. <a class="xref" href="#holdings-in-full">The appendix</a> '
                "sets out every holding at month end, on a sheet turned on its side so the "
                'table keeps all ten columns, and <a class="xref" href="#method">the method</a> '
                "follows it.</p>"
                "<p>Weights are rounded. The active column is the weight against the "
                "benchmark, and a negative figure is an underweight. The book is "
                "measured against the sterling aggregate index, rebalanced at each "
                "month end, and every holding is priced at the close on the last "
                "business day. Duration carried the quarter: the long end held while "
                "the front repriced, and the steepener paid for its carry.</p>",
                # A boxout the prose wraps round on paper (#343).
                aside=Aside(ASIDE, title="Active weight", side="right"),
            ),
        ),
        Page(
            [FullWidth(title=APPENDIX, content=_holdings())],
            orientation="landscape",
        ),
        FullWidth(
            title=METHOD,
            content=TextBlock(
                "<p>Yields are to worst, durations are modified, and spreads are over "
                "the matched gilt. The benchmark is the sterling aggregate index.</p>"
            ),
        ),
    ]


def _holdings() -> DataTable:
    """Twenty-four holdings across ten columns: a table no portrait column holds."""
    rows = [
        TableRow(
            cells=[
                f"{issuer} {2027 + n}",
                "Government" if issuer == "UKT" else "Corporate",
                "AA" if issuer == "UKT" else ["A", "BBB", "A-"][n % 3],
                f"{1 + n % 4}.{n % 8}25%",
                f"{1 + n % 12:02d}/{2027 + n}",
                f"{2 + n % 5}.{n % 10}%",
                f"{3 + n % 3}.{n % 9}%",
                f"{2 + n % 9}.{n % 7}",
                f"{40 + 7 * (n % 11)}",
                f"{'+' if n % 2 else '-'}0.{n % 9}%",
            ]
        )
        for n, issuer in enumerate(_ISSUERS * 3)
    ]
    return DataTable(
        headers=list(HEADERS),
        rows=rows,
        caption="Model portfolio, every holding",
        source="Hermes Research",
        as_of="30 September 2026",
    )
