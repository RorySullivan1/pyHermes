"""
Shared content for the paged fixtures, so a page change is the only variable.

``a4_portrait`` and ``slide_16_9`` render the *same* sections onto different
pages. Reusing the copy rather than writing two documents is what makes the
pair a true A/B: byte-for-byte the same content, one ``PageFormat`` apart, so
every difference between the two goldens is the page and nothing else — the
technique ``compact_size`` and ``spacious_size`` use for density.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from svc.builder import CardGroup, DataTable, FullWidth, TextBlock, TwoColumn
from svc.builder.enums import CardOrientation, TwoColumnRatio
from svc.builder.images import EmailImage
from svc.builder.medium import Medium
from svc.builder.models import KpiItem, TableRow
from svc.document import (
    BackMatter,
    Cover,
    Page,
    PagedDocument,
    RunningFooter,
    RunningHeader,
)

from ._png import solid_png

_GAIN = "#4A7C59"
_LOSS = "#B85450"

#: Light on purpose: the cover's ground is #1E2B38, and a mark in that same
#: colour renders correctly and shows nothing — a screenshot cannot judge an
#: image it cannot see, which is half of what this fixture is for.
_MARK_PNG = solid_png(72, 72, (245, 242, 236))

#: The cover's backdrop, attached so the document is self-contained.
_COVER_PNG = solid_png(120, 80, (22, 33, 45))

#: Fixed so the render never moves. A fixture that reads the clock cannot be
#: snapshotted.
_YEAR = "2026"


def facts() -> dict[str, Any]:
    """Every ``DocumentMetadata`` field, each at a distinctive value."""
    return {
        "language": "en-GB",
        "header_disclaimer": "For illustrative purposes. Not investment advice.",
        "firm_name": "Hermes Research",
        "campaign_name": "Quarterly Review",
        "department": "Rates Strategy",
        "date_range": "Quarter ending 30 September",
        "issue_label": "Issue 001",
        "current_year": _YEAR,
        "theme": "classic",
        "size_theme": "standard",
        "font_theme": "classic",
    }


def build_on(medium: Medium, template_dir: Path | None = None) -> PagedDocument:
    """
    The shared document, laid onto ``medium``'s page.

    Every region field carries a **non-default** value, per standing rule 9:
    a field left at its default is one the golden cannot pin, because the
    render would not move if the default changed underneath it.
    """
    document = PagedDocument(
        facts(),
        template_dir=template_dir,
        medium=medium,
        cover=Cover(
            # Distinct from firm_name / campaign_name on purpose, so the
            # golden pins that the cover says its own thing while the facts
            # still reach the running boxes and the text projection (#91).
            title="Quarterly Review",
            subtitle="What the curve priced, and what it did not",
            logo_url=EmailImage.attached(_MARK_PNG, alt="Hermes Research mark", width=72),
            logo_alt="Hermes Research — quarterly review",
            logo_width=96,
            # Attached rather than hosted, and that is a finding rather than
            # a preference: the PDF exporter makes no network requests, so a
            # document whose cover art lives on a CDN cannot be printed at
            # all. A printable document carries its own images (#164).
            background_image_url=EmailImage.attached(_COVER_PNG, alt="Cover backdrop", width=794),
            align="left",
            background_color="#1E2B38",
            text_color="#F5F2EC",
        ),
        running_header=RunningHeader(
            label="Hermes Research — Quarterly Review",
            box="top-right",
            show_page_number=True,
        ),
        running_footer=RunningFooter(
            label="Confidential",
            box="bottom-left",
            # The footer's default; the header above carries the folio here,
            # so this one is the off case and the pair covers both.
            show_page_number=False,
        ),
        back_matter=BackMatter(heading="Important Disclosures", align="left"),
    )
    return (
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
        .add_section(
            FullWidth(
                title="Narrative",
                content=TextBlock(
                    "<p>The curve steepened through the quarter as the front end "
                    "repriced. Duration added to returns for the first time in "
                    "four quarters.</p>"
                ),
            )
        )
        .add_section(
            FullWidth(
                title="Factor Returns",
                content=DataTable(
                    headers=["Factor", "1M", "YTD"],
                    rows=[
                        TableRow(cells=["Value", "+1.8%", "+7.4%"], colors=["", _GAIN, _GAIN]),
                        TableRow(cells=["Momentum", "-0.4%", "+11.2%"], colors=["", _LOSS, _GAIN]),
                        TableRow(cells=["Quality", "+0.9%", "+5.1%"], colors=["", _GAIN, _GAIN]),
                    ],
                    source="Hermes Research",
                    as_of="30 September 2026",
                    subtitle="Long-short, gross of costs",
                ),
            )
        )
        .add_section(
            TwoColumn(
                ratio=TwoColumnRatio.EQUAL,
                title="Positioning",
                left=TextBlock("<p>The left half of a 50-50 split.</p>"),
                right=TextBlock("<p>The right half of a 50-50 split.</p>"),
            )
        )
        # An explicit sheet boundary, with both breaks at non-default values.
        # In the email medium this same tree flattens and the wrapper is not
        # emitted at all, which is what a test rather than a golden pins.
        .add_section(
            Page(
                [
                    FullWidth(
                        title="Methodology",
                        content=TextBlock(
                            "<p>Factor returns are computed long-short and gross "
                            "of transaction costs.</p>"
                        ),
                    )
                ],
                break_before=True,
                break_after=True,
                title="Appendix",
            )
        )
    )
