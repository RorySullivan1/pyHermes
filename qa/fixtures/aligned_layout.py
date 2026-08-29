"""
Every alignment axis at once (#124), so a cross-axis regression is visible.

Four situations, because no fewer carry the epic: a **centred section whose
title follows** (the declaration lands on two sibling cells, and a centred
section with a left heading reads as a bug); a **component overriding its
container**, which shows the cascade *as* a cascade; a **right-aligned band
holding a CardGroup and a DataTable**, sitting unmoved — the epic's boundary
as an image, right-aligned so "kept its own alignment" is distinguishable
from "inherited the section's"; and an **aligned split**, where the
declaration lands per column cell.

Theme, size and font stay default: a preset moving alongside an alignment
axis would leave a golden diff nobody can attribute. It also carries the
gallery's only explicit ``Container.background_color`` (#128).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from svc.builder import (
    CardGroup,
    DataTable,
    Email,
    EmailBuilder,
    FullWidth,
    TextBlock,
    ThreeColumn,
    TwoColumn,
)
from svc.builder.models import Card, Column, TableRow

#: Fixed, like every string in the gallery: a golden cannot pin a value that
#: moves. See the module docstring in :mod:`qa.fixtures`.
_YEAR = "2026"


def _metadata() -> dict[str, Any]:
    return {
        "email_subject": "Aligned Layout — where a section's copy sits",
        "preheader_text": "One email exercising every alignment axis at once.",
        "firm_name": "Hermes Research",
        "campaign_name": "aligned-layout",
        "department": "Rates Strategy",
        "date_range": "Week ending 24 August",
        "issue_label": "Issue 009",
        "header_disclaimer": "For illustrative purposes. Not investment advice.",
        "current_year": _YEAR,
        "unsubscribe_url": "https://example.com/unsubscribe",
        "view_in_browser_url": "https://example.com/archive/009",
    }


def build(template_dir: Path | None = None) -> Email:
    """Build the aligned-layout email. Deterministic: same bytes every call."""
    return (
        EmailBuilder(template_dir=template_dir)
        .metadata(_metadata())
        # 1. The default. Present so the golden holds one section that states
        #    nothing, which is what makes the other four legible as deviations
        #    rather than as the house style.
        .section(
            FullWidth(
                title="Stated Nothing",
                content=TextBlock(
                    "This section sets no alignment, so it renders exactly as every "
                    "email did before the epic — which is the claim three of its four "
                    "commits make about the goldens."
                ),
            )
        )
        # 2. A centred section, title following.
        .section(
            FullWidth(
                title="Centred, Heading And All",
                align="center",
                content=TextBlock(
                    "The heading above and this paragraph take one declaration on two "
                    "sibling cells. A centred section whose heading stayed left is the "
                    "half-applied result that reads as a bug.",
                    subtitle="The standfirst belongs to the block, not to the section",
                ),
            )
        )
        # 3. A component disagreeing with its container.
        .section(
            FullWidth(
                title="Centred, With One Block Opting Out",
                align="center",
                content=TextBlock(
                    "This block sets its own alignment and wins by ordinary CSS "
                    "cascade — its declaration sits on a descendant of the cell "
                    "carrying the section's, and inheritance is the weakest source. "
                    "No Python resolves it, and no signature grew a parameter.",
                    align="right",
                ),
            )
        )
        # 4. The boundary: structural components in a right-aligned band.
        .section(
            FullWidth(
                title="Right-Aligned, Holding Structure",
                align="right",
                highlight=True,
                content=CardGroup(
                    [
                        Card("S&P 500", "5,234", "#4A7C59", "+1.42%"),
                        Card("UST 10Y", "4.28%", "#B85450", "+6 bps"),
                        Card("VIX", "14.32", "#4A7C59", "-2.18 pts"),
                    ],
                    orientation="horizontal",
                ),
            )
        )
        .section(
            FullWidth(
                title="Right-Aligned, Holding A Table",
                align="right",
                content=DataTable(
                    headers=[Column("Factor", kind="text"), "1M", "YTD"],
                    rows=[
                        TableRow(["Value", "+1.8%", "+7.4%"]),
                        TableRow(["Momentum", "-0.4%", "+11.2%"]),
                    ],
                    caption="Factor performance, gross of costs",
                ),
            )
        )
        # 5. A split, where the declaration lands per column cell.
        .section(
            TwoColumn(
                ratio="50-50",
                title="Centred Split",
                align="center",
                # Not an alignment axis, and here on purpose. Widening the
                # field-completeness rule to containers (#128) found that
                # `background_color` — the *original* entry in the closed
                # colour list — had never been set by any fixture, so no
                # golden pinned the caller's own band colour. This is the
                # cheapest place to close that: a brand-new fixture, so no
                # existing golden moves to accommodate it.
                background_color="#F4F1EC",
                left=TextBlock(
                    "The left half of a centred split, written wide enough that the "
                    "section's centring has room to be visible in a screenshot."
                ),
                right=TextBlock(
                    "The right half of the same split, written to the same width for "
                    "the same reason. Both cells carry the declaration."
                ),
            )
        )
        .section(
            ThreeColumn(
                ratio="33-33-33",
                title="Three Columns, One Disagreeing",
                align="center",
                left=TextBlock("Centred by the section, like its neighbour to the right."),
                center=TextBlock(
                    "This middle column states left and keeps it, inside a centred split.",
                    align="left",
                ),
                right=TextBlock("Centred by the section, like its neighbour to the left."),
            )
        )
        .build()
    )
