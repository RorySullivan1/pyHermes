"""
A paged fixture built to cross sheets: the teeth for epic #169.

A 60-row holdings table with a subhead mid-table and a total, a chart whose
fine print lands at a sheet foot, and a section title placed to fall at the
foot of another. Each boundary is engineered, not incidental: the lead-in
paragraph counts are chosen so that each defect occurs when the paged
skeleton's break rules are removed. `.claude/rules/qa-harness.md` carries how.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from svc.builder import ChartBlock, DataTable, FullWidth, TextBlock
from svc.builder.document import Document
from svc.builder.images import EmailImage
from svc.builder.models import Column, TableRow
from svc.document import PAGED_MEDIUM, PagedDocument

from . import _paged
from ._png import solid_png

#: The column headers, which the PDF test looks for on every sheet the table
#: occupies. Rendered upper-case by the template, and chosen so that no
#: other copy in the document contains one of them in capitals.
HEADERS = ["Issue", "Sector", "Weight", "Yield"]

_GOVERNMENT = [
    f"UKT {coupon}% {year}"
    for coupon, year in zip(
        ["0.25", "0.5", "0.875", "1.25", "1.5", "1.625", "2", "3.25", "3.5", "3.75"] * 3,
        range(2027, 2057),
        strict=True,
    )
]
_CREDIT = [
    f"{issuer} {year}"
    for issuer, year in zip(
        ["Vodafone", "HSBC", "Tesco", "BT", "National Grid", "Aviva"] * 5,
        range(2028, 2058),
        strict=True,
    )
]

#: Every holding's label, in table order; the PDF test finds the table's
#: sheets by them.
HOLDINGS = _GOVERNMENT + _CREDIT

#: The subhead that splits the two books, and the total beneath them.
SUBHEAD = "Investment-grade credit"
TOTAL = "Total portfolio"

#: The section whose title is placed at a sheet foot, and its first line.
ENGINEERED_TITLE = "Outlook"
ENGINEERED_FIRST_LINE = "Duration stays long into the new year"

#: The chart's subtitle, attribution and disclosure, placed at a sheet foot.
CHART_SUBTITLE = "Key-rate exposure"
CHART_SOURCE = "Source: Hermes Research, curve model"
CHART_DISCLOSURE = "Modelled exposures are estimates and may differ from the book."

#: How many paragraphs precede each engineered boundary. Tuned on A4 against
#: the skeleton with its break rules removed; see the module docstring.
INTRO_PARAGRAPHS = 13
LEAD_IN_PARAGRAPHS = 10
RUN_ON_PARAGRAPHS = 12

_CHART_PNG = solid_png(600, 280, (74, 124, 89))


def _paragraphs(count: int, topic: str) -> TextBlock:
    return TextBlock(
        "".join(
            f"<p>{topic}, paragraph {n}: the book held its weights through the month "
            "and the curve did most of the work.</p>"
            for n in range(1, count + 1)
        )
    )


def _row(label: str, sector: str, n: int) -> TableRow:
    return TableRow(cells=[label, sector, f"{1 + n % 3}.{n % 10}%", f"{3 + n % 4}.{n % 7}%"])


def _holdings_table() -> DataTable:
    rows = [_row(label, "Government", n) for n, label in enumerate(_GOVERNMENT)]
    rows.append(TableRow(cells=[SUBHEAD], kind="subhead"))
    rows += [_row(label, "Corporate", n) for n, label in enumerate(_CREDIT)]
    rows.append(TableRow(cells=[TOTAL, "", "100.0%", "4.1%"], kind="total"))
    return DataTable(
        headers=list[str | Column](HEADERS),
        rows=rows,
        caption="Model portfolio, by issue",
        subtitle="Sterling fixed income, weights at month end",
        source="Hermes Research",
        as_of="30 September 2026",
        disclosure="Weights are rounded and may not sum to the total shown.",
    )


def regions() -> dict:
    """
    The shared regions, with the **footer** following the section (#185).

    ``a4_portrait``'s header follows; this is the complementary pairing, a
    fixed header over a following footer. Margin boxes take no body space, so
    the tuned boundaries above do not move.
    """
    shared = _paged.regions()
    shared["running_header"] = dataclasses.replace(shared["running_header"], follow=None)
    shared["running_footer"] = dataclasses.replace(shared["running_footer"], follow="section")
    return shared


def build_with(
    intro: int, lead_in: int, run_on: int, template_dir: Path | None = None
) -> PagedDocument:
    """The document with its three lead-in lengths as parameters, for tuning."""
    document = PagedDocument(
        _paged.facts(), template_dir=template_dir, medium=PAGED_MEDIUM, **regions()
    )
    return (
        document.add_section(FullWidth(title="Portfolio", content=_paragraphs(intro, "Intro")))
        .add_section(FullWidth(title="Holdings", content=_holdings_table()))
        .add_section(FullWidth(title="Curve", content=_paragraphs(lead_in, "Curve")))
        .add_section(
            FullWidth(
                content=ChartBlock(
                    EmailImage.attached(_CHART_PNG, alt="Curve exposure by bucket", width=600),
                    subtitle=CHART_SUBTITLE,
                    source=CHART_SOURCE,
                    disclosure=CHART_DISCLOSURE,
                )
            )
        )
        .add_section(FullWidth(title="Positioning", content=_paragraphs(run_on, "Positioning")))
        .add_section(
            FullWidth(
                title=ENGINEERED_TITLE,
                content=TextBlock(f"<p>{ENGINEERED_FIRST_LINE}, and the reasons follow.</p>"),
            )
        )
    )


def build(template_dir: Path | None = None) -> Document:
    """Build the long-table document. Deterministic: same bytes every call."""
    return build_with(INTRO_PARAGRAPHS, LEAD_IN_PARAGRAPHS, RUN_ON_PARAGRAPHS, template_dir)
