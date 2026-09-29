"""
Quarterly Review — the same builder, laid onto sheets instead of into an inbox.

The paged counterpart to ``market-snapshot``: identical components, containers
and design axes, a different **medium**. What the page adds is the managed
elements an email has no use for —

- a ``Cover`` that opens the document, on a named CSS page so no folio lands
  on it,
- a ``RunningFooter`` repeating in the bottom margin of every sheet, carrying
  the page counter,
- a ``Page`` marking a real sheet boundary before the appendix — which
  *flattens* to nothing in the email medium, so one tree serves both, and
- a ``BackMatter`` sheet closing on the disclosures.

Run it directly to (re)generate ``quarterly-review.html`` next to this file,
and ``quarterly-review.pdf`` as well when the ``[pdf]`` extra is installed:

    python examples/quarterly-review/quarterly-review.py

``build()`` is a pure, deterministic factory in the same shape as the email
examples and the fixtures in ``qa/fixtures/`` — same bytes every call.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder import CardGroup, DataTable, FullWidth, TextBlock
from pyhermes.builder.enums import CardOrientation
from pyhermes.builder.models import KpiItem, TableRow
from pyhermes.document import BackMatter, Cover, Page, PagedDocument, RunningFooter, RunningHeader

_GAIN = "#4A7C59"
_LOSS = "#B85450"


def build() -> PagedDocument:
    """Build the quarterly review. Deterministic: same bytes every call."""
    document = PagedDocument(
        {
            "firm_name": "Hermes Research",
            "campaign_name": "Quarterly Review",
            "department": "Rates Strategy",
            "date_range": "Quarter ending 30 September",
            "issue_label": "Issue 001",
            "current_year": "2026",
            "header_disclaimer": (
                "<p>Prepared for professional clients. Past performance is not a guide to "
                "future returns, and the figures above are gross of fees.</p>"
            ),
        },
        cover=Cover(
            title="Quarterly Review",
            subtitle="What the curve priced, and what it did not",
            background_color="#1E2B38",
            text_color="#F5F2EC",
        ),
        running_header=RunningHeader(label="Hermes Research — Quarterly Review", box="top-right"),
        running_footer=RunningFooter(label="Confidential", box="bottom-left"),
        back_matter=BackMatter(heading="Important Disclosures"),
    )

    document.add_section(
        FullWidth(
            title="Market Snapshot",
            highlight=True,
            content=CardGroup(
                [
                    KpiItem("S&P 500", "5,234", _GAIN, "+1.42%"),
                    KpiItem("UST 10Y", "4.28%", _LOSS, "+6 bps"),
                    KpiItem("Gold", "2,411", _GAIN, "+0.85%"),
                ],
                orientation=CardOrientation.HORIZONTAL,
            ),
        )
    )
    document.add_section(
        FullWidth(
            title="Narrative",
            content=TextBlock(
                "<p>The curve steepened through the quarter as the front end repriced. "
                "Duration added to returns for the first time in four quarters.</p>"
            ),
        )
    )
    document.add_section(
        FullWidth(
            title="Factor Returns",
            content=DataTable(
                headers=["Factor", "1M", "YTD"],
                rows=[
                    TableRow(cells=["Value", "+1.8%", "+7.4%"], colors=["", _GAIN, _GAIN]),
                    TableRow(cells=["Momentum", "-0.4%", "+11.2%"], colors=["", _LOSS, _GAIN]),
                ],
                source="Hermes Research",
                as_of="30 September 2026",
            ),
        )
    )
    # A sheet of its own. In the email medium this wrapper is not emitted at
    # all -- the sections inside simply run on.
    document.add_section(
        Page(
            [
                FullWidth(
                    title="Appendix — Methodology",
                    content=TextBlock(
                        "<p>Factor returns are computed long-short and gross of "
                        "transaction costs.</p>"
                    ),
                )
            ]
        )
    )
    return document


def main() -> None:
    """Render beside this file, and print what was written."""
    here = Path(__file__).parent
    html = build().save(here / "quarterly-review.html")
    print(f"{html}  ({html.stat().st_size / 1024:.1f} KB)")

    try:
        from pyhermes.pdf import page_count, save_pdf
    except ImportError:  # pragma: no cover - the extra is optional by design
        print('pdf skipped: install the extra with `pip install -e ".[pdf]"`')
        return
    from pyhermes.pdf import PdfError

    try:
        pdf = save_pdf(build(), here / "quarterly-review.pdf")
    except PdfError as exc:
        print(f"pdf skipped: {exc}")
        return
    print(f"{pdf}  ({pdf.stat().st_size / 1024:.1f} KB, {page_count(build())} page(s))")


if __name__ == "__main__":
    main()
